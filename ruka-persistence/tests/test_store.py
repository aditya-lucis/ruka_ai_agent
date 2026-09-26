import pytest
from pathlib import Path
from ruka_persistence.memory.store import MemoryStore

def test_memory_store_init(tmp_path):
    db_path = tmp_path / "ruka.db"
    store = MemoryStore(db_path)
    
    conn = store.get_connection()
    # Check WAL
    mode = conn.execute("PRAGMA journal_mode").fetchone()[0]
    assert mode.lower() in ("wal", "memory")  # if in-memory, wal might fallback
    
    # Check migrations applied
    tables = [r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
    assert "schema_migrations" in tables
    
    # Check version 1 applied
    versions = [r[0] for r in conn.execute("SELECT version FROM schema_migrations").fetchall()]
    assert 1 in versions
