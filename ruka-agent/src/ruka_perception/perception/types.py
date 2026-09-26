from enum import Enum
from dataclasses import dataclass, field

class Modality(Enum):
    TEXT = "text"
    IMAGE = "image"
    AUDIO = "audio"
    VIDEO = "video"
    INTERACTION_EVENT = "interaction_event"
    UNKNOWN = "unknown"

class Provenance(Enum):
    """Asal bytes — menentukan seberapa banyak validasi yang wajib
    sebelum bytes itu dipercaya."""
    USER_UPLOAD = "user_upload"      # paling tidak dipercaya
    TOOL_RESULT = "tool_result"      # output tool, tetap divalidasi
    OWN_OUTPUT = "own_output"        # hasil generate Ruka sendiri
    SYSTEM_ASSET = "system_asset"    # asset internal (avatar, dsb.)

@dataclass
class PerceptionInput:
    """Satu unit input dari dunia. Bytes TIDAK pernah dibawa-bawa
    tanpa alasan: untuk text hanya `text`, untuk binary hanya `data`.
    Atribut:
        modality: modality yang diklaim pengirim (akan diverifikasi).
        mime_type: klaim MIME dari pengirim (akan dicocokkan magic bytes).
        text: isi bila modality TEXT.
        data: bytes bila modality IMAGE/AUDIO (bisa None bila hanya
              referensi file yang sudah ter-upload).
        external_ref: URI file ter-upload (Files API) bila bytes tidak
                      disertakan — mis. "https://generativelanguage.googleapis.com/..."
        metadata: dict kecil, tidak boleh berisi secret.
        received_at: epoch detik (float) untuk pengukuran latensi.
        trace_id: id korelasi lintas tahap.
    """
    modality: Modality
    mime_type: str | None = None
    text: str | None = None
    data: bytes | None = None
    external_ref: str | None = None
    metadata: dict = field(default_factory=dict)
    provenance: Provenance = Provenance.USER_UPLOAD
    received_at: float = 0.0
    trace_id: str = ""

@dataclass
class RouterDecision:
    modality: Modality
    handler: str
    reason: str
    accepted: bool = True

@dataclass
class PerceptionResult:
    modality: Modality
    summary: str = ""
    transcript: str = ""
    confidence: float | None = None
    notes: list[str] = field(default_factory=list)
    embedding: list[float] | None = None
    trace_id: str = ""
