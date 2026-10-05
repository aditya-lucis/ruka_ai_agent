# -*- coding: utf-8 -*-
"""Data models and types for NOCTIS Memory Palace (FR-ME-01 & Table 19)."""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
import time
from typing import Any
import uuid


class MemoryWing(str, Enum):
    """Lima sayap resmi Memory Palace PROJECT NOCTIS."""
    RELATIONSHIP = "relationship"  # Graf entitas: relasi Young Lord & orang sekitar
    PROJECT = "project"            # Konteks proyek, status repo, keputusan arsitektur (ADR)
    PREFERENCE = "preference"      # Preferensi pengguna (ambang 3 sinyal)
    DAILY = "daily"                # Catatan harian & sesi interaksi
    DREAM = "dream"                # Konsolidasi latar belakang saat idle/tidur


@dataclass
class RelationshipTriple:
    """Tripel subjek-predikat-objek dalam sayap hubungan (palace_relationship)."""
    subject: str
    predicate: str
    object: str
    confidence: float = 1.0
    provenance: str = ""
    id: str = field(default_factory=lambda: f"rel_{uuid.uuid4().hex[:8]}")
    created_at: float = field(default_factory=time.time)
    is_deleted: bool = False
    delete_reason: str | None = None

    def text_representation(self) -> str:
        return f"{self.subject} {self.predicate} {self.object}"


@dataclass
class ProjectMemory:
    """Status repositori & rekaman keputusan arsitektur (palace_project)."""
    repo: str
    kind: str                      # "status" | "decision"
    body: str
    rationale: str = ""
    status: str = "active"         # "active" | "superseded"
    superseded_by: str | None = None
    id: str = field(default_factory=lambda: f"proj_{uuid.uuid4().hex[:8]}")
    created_at: float = field(default_factory=time.time)
    is_deleted: bool = False
    delete_reason: str | None = None

    def text_representation(self) -> str:
        return f"[{self.repo}] [{self.kind}] {self.body}. Rationale: {self.rationale}"


@dataclass
class PreferenceMemory:
    """Preferensi gaya & aturan Young Lord (palace_preference)."""
    key: str
    value: str
    signal_count: int = 1
    confidence: float = 0.5
    id: str = field(default_factory=lambda: f"pref_{uuid.uuid4().hex[:8]}")
    created_at: float = field(default_factory=time.time)
    is_deleted: bool = False
    delete_reason: str | None = None

    @property
    def is_active(self) -> bool:
        """Sesuai spesifikasi SRS: pembelajar konservatif dengan ambang 3 sinyal."""
        return self.signal_count >= 3

    def text_representation(self) -> str:
        return f"Preferensi {self.key}: {self.value}"


@dataclass
class DailyMemory:
    """Catatan harian kejadian dan sesi (palace_daily)."""
    summary: str
    session_id: str = ""
    highlights: list[str] = field(default_factory=list)
    id: str = field(default_factory=lambda: f"day_{uuid.uuid4().hex[:8]}")
    timestamp: float = field(default_factory=time.time)
    is_deleted: bool = False
    delete_reason: str | None = None

    def text_representation(self) -> str:
        hl_str = ", ".join(self.highlights) if self.highlights else ""
        return f"Sesi {self.session_id}: {self.summary} {hl_str}".strip()


@dataclass
class DreamMemory:
    """Konsolidasi malam/idle dan abstraksi memori (palace_dream)."""
    topic: str
    reflection: str
    abstraction_level: int = 1
    id: str = field(default_factory=lambda: f"drm_{uuid.uuid4().hex[:8]}")
    created_at: float = field(default_factory=time.time)
    is_deleted: bool = False
    delete_reason: str | None = None

    def text_representation(self) -> str:
        return f"Refleksi [{self.topic}]: {self.reflection}"


@dataclass
class RecallResult:
    """Hasil temu-balik memori terfusi RRF berprovenance untuk Crimson Heart."""
    entry_id: str
    wing: MemoryWing
    content: str
    score: float
    provenance: dict[str, Any]
    match_sources: list[str] = field(default_factory=list)  # ["bm25", "vector", "graph"]
