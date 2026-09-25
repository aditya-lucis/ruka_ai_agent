"""MemoryGovernor — satu-satunya pintu tulis memori."""
from __future__ import annotations
from datetime import datetime, timezone
from src.memory.models import MemoryKind, MemoryRecord, TTL_BY_KIND

class MemoryContractError(ValueError):
    """Record melanggar kontrak governance — GAGAL KERAS."""

class MemoryGovernor:
    def __init__(self, store) -> None:      # store: sqlite_store Vol I (evolved)
        self._store = store
        self._rejected: list[str] = []

    def write(self, record: MemoryRecord, now: datetime | None = None) -> int:
        now = now or datetime.now(timezone.utc)
        self._validate(record)
        ttl = TTL_BY_KIND[record.kind]
        if record.expires_at is None and ttl is not None:
            record = record.model_copy(update={"expires_at": now + ttl})
        return self._store.insert_memory(record)

    def _validate(self, r: MemoryRecord) -> None:
        if not r.content.strip():
            raise MemoryContractError("content kosong — memori tanpa isi ditolak")
        if r.kind != MemoryKind.WORKING and r.provenance is None:
            raise MemoryContractError(
                f"kind={r.kind.value} wajib provenance (source_type, source_id)"
            )
        if r.kind == MemoryKind.IDENTITY and r.importance < 0.9:
            raise MemoryContractError(
                "identity memory wajib importance >= 0.9 — identitas adalah "
                "prioritas recall tertinggi"
            )

    def recall(self, kinds: list[MemoryKind], limit: int = 8,
               now: datetime | None = None) -> list[MemoryRecord]:
        """Baca terurut importance; record kedaluwarsa disaring."""
        now = now or datetime.now(timezone.utc)
        rows = self._store.query_memories(kinds=[k.value for k in kinds],
                                          active_only=True)
        out = []
        for r in rows:
            if r.supersedes_id is not None:
                continue                      # sudah direvisi (PART 9)
            if r.is_expired(now):
                continue
            out.append(r)
        out.sort(key=lambda r: -r.importance)
        return out[:limit]

    @property
    def rejected(self) -> list[str]:
        return list(self._rejected)
