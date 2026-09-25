from __future__ import annotations
import json
import sqlite3
from datetime import datetime
from src.memory.models import MemoryRecord, MemoryKind

SCHEMA = """
CREATE TABLE IF NOT EXISTS memory_records (
    id TEXT PRIMARY KEY,
    kind TEXT NOT NULL,
    content TEXT NOT NULL,
    user_id TEXT NOT NULL,
    created_at TEXT NOT NULL,
    expires_at TEXT,
    importance REAL NOT NULL DEFAULT 0.5
);
CREATE INDEX IF NOT EXISTS idx_memory_user
    ON memory_records(user_id, kind);
CREATE TABLE IF NOT EXISTS session_summaries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    summary TEXT NOT NULL,
    created_at TEXT NOT NULL
);
"""

class SqliteMemoryStore:
    """Fulfill kontrak store MemoryManager: save/search/expire/delete."""
    def __init__(self, path: str = "ruka.db"):
        self.conn = sqlite3.connect(path)
        self.conn.row_factory = sqlite3.Row
        self.conn.executescript(SCHEMA)

    def save(self, rec: MemoryRecord) -> None:
        self.conn.execute(
            "INSERT OR REPLACE INTO memory_records "
            "VALUES (?,?,?,?,?,?,?)",
            (rec.id, rec.kind.value, rec.content, rec.user_id,
             rec.created_at.isoformat(),
             rec.expires_at.isoformat() if rec.expires_at else None,
             rec.importance),
        )
        self.conn.commit()

    def search(self, user_id: str, query: str, *, limit: int = 5):
        """Pencarian kasar LIKE + ranking importance.
        Semantik penuh datang bersama vektor di PART XVII;
        versi ini cukup untuk episodic dan preference.
        """
        words = [w for w in query.lower().split() if len(w) > 3][:5]
        like = " OR ".join("content LIKE ?" for _ in words)
        params = [f"%{w}%" for w in words] if words else []
        sql = ("SELECT * FROM memory_records WHERE user_id=? "
               f"AND ({like or '1=1'}) "
               "ORDER BY importance DESC, created_at DESC LIMIT ?")
        rows = self.conn.execute(sql, [user_id, *params, limit])
        return [self._to_record(r) for r in rows]

    def expire_old(self, user_id: str) -> int:
        cur = self.conn.execute(
            "DELETE FROM memory_records WHERE user_id=? "
            "AND expires_at IS NOT NULL AND expires_at < ?",
            (user_id, datetime.utcnow().isoformat()),
        )
        self.conn.commit()
        return cur.rowcount

    def delete(self, record_id: str) -> None:
        self.conn.execute("DELETE FROM memory_records WHERE id=?",
                          (record_id,))
        self.conn.commit()

    @staticmethod
    def _to_record(r: sqlite3.Row) -> MemoryRecord:
        return MemoryRecord(
            id=r["id"], kind=MemoryKind(r["kind"]),
            content=r["content"], user_id=r["user_id"],
            created_at=datetime.fromisoformat(r["created_at"]),
            expires_at=(datetime.fromisoformat(r["expires_at"])
                        if r["expires_at"] else None),
            importance=r["importance"],
        )
