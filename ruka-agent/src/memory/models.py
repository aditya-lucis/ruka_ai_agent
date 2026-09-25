"""Memory record v0.3 — kind + governance metadata.
Evolusi dari v0.2 (Vol I). Kolom lama dipertahankan; kolom baru
punya default sehingga migrasi ALTER TABLE aman dan reversibel.
"""
from __future__ import annotations
import sqlite3
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Literal
from pydantic import BaseModel, Field

class MemoryKind(str, Enum):
    WORKING = "working"
    CONVERSATION = "conversation"
    SUMMARY = "summary"
    EPISODIC = "episodic"
    SEMANTIC = "semantic"
    PREFERENCE = "preference"
    IDENTITY = "identity"
    PROJECT = "project"
    KNOWLEDGE = "knowledge"

class Provenance(BaseModel):
    """Dari mana record ini berasal — wajib non-null untuk kind
    selain WORKING (scratchpad giliran)."""
    source_type: str                      # conversation | document | tool | system
    source_id: str                        # turn id / chunk id / call id
    source_hash: str = ""                # integritas konten sumber
    captured_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class MemoryRecord(BaseModel):
    """Satu unit memori jangka panjang v0.3 (kompatibel penuh v0.2)."""
    id: str | None = None
    user_id: str = "default"
    kind: MemoryKind
    content: str
    importance: float = Field(default=0.3, ge=0.0, le=1.0)
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    provenance: Provenance | None = None
    expires_at: datetime | None = None
    supersedes_id: int | str | None = None      # PART 9: riwayat revisi
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    def is_expired(self, now: datetime | None = None) -> bool:
        if self.expires_at is None:
            return False
        return (now or datetime.now(timezone.utc)) >= self.expires_at

TTL_BY_KIND: dict[MemoryKind, timedelta | None] = {
    MemoryKind.WORKING: timedelta(minutes=30),
    MemoryKind.CONVERSATION: None,             # append-only, di-fold berkala
    MemoryKind.SUMMARY: timedelta(days=180),
    MemoryKind.EPISODIC: None,
    MemoryKind.SEMANTIC: None,
    MemoryKind.PREFERENCE: timedelta(days=365),
    MemoryKind.IDENTITY: None,
    MemoryKind.PROJECT: timedelta(days=90),
    MemoryKind.KNOWLEDGE: None,                # dikelola pipeline RAG
}

MIGRATION_V03 = """
ALTER TABLE memories ADD COLUMN kind TEXT NOT NULL DEFAULT 'episodic';
ALTER TABLE memories ADD COLUMN importance REAL NOT NULL DEFAULT 0.3;
ALTER TABLE memories ADD COLUMN confidence REAL NOT NULL DEFAULT 0.5;
ALTER TABLE memories ADD COLUMN source_type TEXT;
ALTER TABLE memories ADD COLUMN source_id TEXT;
ALTER TABLE memories ADD COLUMN source_hash TEXT DEFAULT '';
ALTER TABLE memories ADD COLUMN provenance_at TEXT;
ALTER TABLE memories ADD COLUMN expires_at TEXT;
ALTER TABLE memories ADD COLUMN supersedes_id INTEGER;
CREATE INDEX IF NOT EXISTS idx_memories_kind ON memories(kind);
CREATE INDEX IF NOT EXISTS idx_memories_expiry ON memories(expires_at);
"""

def migrate(conn: sqlite3.Connection) -> None:
    """Aman dipanggil berulang (idempotent): kolom yang sudah ada
    dilewati dengan diam; kolom baru ditambahkan dengan default."""
    existing = {row[1] for row in conn.execute("PRAGMA table_info(memories)")}
    for stmt in MIGRATION_V03.strip().split(";\n"):
        stmt = stmt.strip()
        if not stmt:
            continue
        head = stmt.split()[0].upper()
        if head == "ALTER":
            col = stmt.split("ADD COLUMN")[1].split()[0]
            if col in existing:
                continue
        conn.execute(stmt)
    conn.commit()

# --- Kompatibilitas Model Vol I ---
class SessionSummary(BaseModel):
    """Ringkasan percakapan — pengganti history mentah."""
    summary: str = Field(max_length=1500)
    open_questions: list[str] = Field(default_factory=list)
    preferences_learned: list[str] = Field(default_factory=list)

class ExtractedMemory(BaseModel):
    kind: Literal["episodic", "semantic", "preference"]
    content: str = Field(min_length=8, max_length=500)
    importance: float = Field(ge=0.0, le=1.0)

class ExtractedMemories(BaseModel):
    """Output ekstraksi — kosong adalah jawaban sah dan sering benar."""
    memories: list[ExtractedMemory] = Field(max_length=4)
    rejected: list[str] = Field(default_factory=list,
                                description="ringkasan yang sengaja "
                                "tidak disimpan + alasannya")
