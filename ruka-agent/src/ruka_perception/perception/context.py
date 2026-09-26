from .types import Modality, PerceptionResult

_BLOCK_ORDER = [
    Modality.TEXT,
    Modality.IMAGE,
    Modality.AUDIO,
    Modality.INTERACTION_EVENT,
    Modality.UNKNOWN
]

_BLOCK_LABEL = {
    Modality.TEXT: "text",
    Modality.IMAGE: "visual",
    Modality.AUDIO: "audio",
    Modality.INTERACTION_EVENT: "event",
    Modality.UNKNOWN: "unknown"
}

class MultimodalContext:
    """Konteks terurut hasil fusion ringan (penataan blok, BUKAN
    fusion neural)."""
    def __init__(self):
        self.blocks: list[dict] = []
        self.notes: list[str] = []

    def add(self, result: PerceptionResult, *, raw_available: bool = False):
        """Tambah satu hasil. raw_available menandai apakah bytes/
        referensi aslinya masih bisa disertakan oleh adapter (nilai
        default False: builder hanya menyimpan RINGKASAN, bukan bytes)."""
        label = _BLOCK_LABEL.get(result.modality, "other")
        block = {
            "type": label,
            "summary": result.summary or result.transcript or "",
            "confidence": result.confidence,
            "has_embedding": result.embedding is not None,
            "raw_available": raw_available,
            "notes": list(result.notes),
        }
        
        if result.transcript:
            block["transcript"] = result.transcript
            
        self.blocks.append(block)
        self.notes.extend(result.notes)
        return self

    def ordered_blocks(self) -> list[dict]:
        """Blocks diurutkan text-first, lalu image, audio, event."""
        order = {m: i for i, m in enumerate(_BLOCK_ORDER)}
        
        def _get_modality_from_type(t: str) -> Modality:
            for k, v in _BLOCK_LABEL.items():
                if v == t: return k
            return Modality.UNKNOWN
            
        return sorted(self.blocks,
                      key=lambda b: order.get(_get_modality_from_type(b["type"]), 99))

    def budget_tokens(self) -> int:
        """Estimasi kasar token konteks ringkasan (bukan bytes asli):
        ~4 karakter per token untuk teks ringkasan."""
        total = 0
        for b in self.ordered_blocks():
            total += max(1, len(b.get("summary", "")) // 4)
            if b.get("transcript"):
                total += max(1, len(b["transcript"]) // 4)
        return total

    def to_prompt_sections(self) -> list[str]:
        """Render konteks menjadi seksi teks untuk prompt kognitif.
        Bytes asli TIDAK dirender di sini — adapter infrastruktur yang
        menyusun part input API dengan uri/data."""
        sections = []
        for b in self.ordered_blocks():
            head = f"[{b['type'].upper()}]"
            body = b.get("transcript") or b.get("summary", "")
            conf = b.get("confidence")
            line = f"{head} {body}"
            if conf is not None:
                line += f" (confidence={conf:.2f})"
            sections.append(line)
        return sections
