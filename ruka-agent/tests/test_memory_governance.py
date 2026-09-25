import sqlite3
from datetime import datetime, timedelta, timezone
import pytest
from src.memory.models import (MemoryKind, MemoryRecord, Provenance,
                               TTL_BY_KIND, migrate)
from src.memory.governance import MemoryContractError, MemoryGovernor

T0 = datetime(2026, 9, 7, 10, 0, tzinfo=timezone.utc)

class FakeStore:
    """Store in-memory — kontrak insert/query mengikuti sqlite_store."""
    def __init__(self) -> None:
        self.rows: list[MemoryRecord] = []

    def insert_memory(self, r: MemoryRecord) -> int:
        self.rows.append(r)
        return len(self.rows)

    def query_memories(self, kinds: list[str], active_only: bool = True):
        return [r for r in self.rows if r.kind.value in kinds]

def test_provenance_required_for_non_working():
    gov = MemoryGovernor(FakeStore())
    with pytest.raises(MemoryContractError, match="provenance"):
        gov.write(MemoryRecord(kind=MemoryKind.SEMANTIC, content="fakta"))

def test_ttl_applied_automatically():
    gov = MemoryGovernor(FakeStore())
    rec = MemoryRecord(kind=MemoryKind.WORKING, content="fokus: migrasi skema")
    gov.write(rec, now=T0)
    ttl = TTL_BY_KIND[MemoryKind.WORKING]
    assert gov._store.rows[0].expires_at == T0 + ttl

def test_identity_needs_high_importance():
    gov = MemoryGovernor(FakeStore())
    with pytest.raises(MemoryContractError, match="importance"):
        gov.write(MemoryRecord(kind=MemoryKind.IDENTITY, content="x",
                               importance=0.4,
                               provenance=Provenance(source_type="system",
                                                     source_id="boot")))

def test_expired_records_not_recalled():
    store = FakeStore()
    gov = MemoryGovernor(store)
    gov.write(MemoryRecord(kind=MemoryKind.WORKING, content="penting sebentar"), now=T0)
    later = T0 + timedelta(hours=2)          # jauh melewati TTL 30 menit
    assert gov.recall(kinds=[MemoryKind.WORKING], now=later) == []

def test_migration_idempotent_and_backcompatible():
    """Skema v0.2 (tanpa kolom baru) tetap terbaca setelah migrasi."""
    conn = sqlite3.connect(":memory:")
    conn.execute("CREATE TABLE memories (id INTEGER PRIMARY KEY, content TEXT)")
    conn.execute("INSERT INTO memories (content) VALUES ('warisan vol 1')")
    migrate(conn)
    migrate(conn)                              # idempotent
    row = conn.execute("SELECT content, kind FROM memories").fetchone()
    assert row == ("warisan vol 1", "episodic")   # default kind aman
