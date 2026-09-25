from __future__ import annotations
import logging
from datetime import datetime, timedelta
from src.llm.structured import ask_structured
from src.memory.models import MemoryRecord, MemoryKind, ExtractedMemories

log = logging.getLogger("ruka.memory")

class MemoryManager:
    """Kebijakan memori — BUKAN penyimpanan (lihat PART XVI)."""
    def __init__(self, store, client, *, ttl_days: int = 90):
        self.store = store          # kontrak: save/fetch/expire
        self.client = client
        self.ttl_days = ttl_days

    # ---- WHAT to store: ekstraksi selektif, bukan dump ----
    def capture(self, user_id: str, conversation_tail: str) -> int:
        """Ekstrak memori layak-simpan dari ekor percakapan."""
        extracted = ask_structured(
            self.client,
            "Ekstrak memori jangka panjang yang layak disimpan "
            f"dari percakapan ini:\n{conversation_tail}",
            ExtractedMemories,
        )
        now = datetime.utcnow()
        saved = 0
        for m in extracted.memories:
            rec = MemoryRecord(
                id=f"{user_id}:{now.timestamp():.0f}:{saved}",
                kind=m.kind,
                content=m.content,
                user_id=user_id,
                created_at=now,
                expires_at=(now + timedelta(days=self.ttl_days)
                            if m.kind == MemoryKind.EPISODIC else None),
                importance=m.importance,
            )
            self.store.save(rec)
            saved += 1
        log.info("capture user=%s simpan=%d", user_id, saved)
        return saved

    # ---- WHEN to retrieve: pra-setiap request, selektif ----
    def context_for(self, user_id: str, query: str, *, limit: int = 5) -> str:
        """Ambil memori relevan sebagai blok system context."""
        records = self.store.search(user_id, query, limit=limit)
        self.store.expire_old(user_id)  # housekeeping murah
        if not records:
            return ""
        lines = [f"- [{r.kind.value}] {r.content}" for r in records]
        return "Memori relevan tentang user:\n" + "\n".join(lines)

    # ---- WHEN to summarize: history melebihi anggaran ----
    def should_summarize(self, history_chars: int,
                         budget_chars: int = 12_000) -> bool:
        return history_chars > budget_chars

    # ---- WHEN to forget: kadaluarsa + konflik ----
    def forget(self, record_id: str, reason: str) -> None:
        self.store.delete(record_id)
        log.info("forget id=%s alasan=%s", record_id, reason)
