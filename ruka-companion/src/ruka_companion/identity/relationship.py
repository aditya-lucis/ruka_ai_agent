"""RUKA VI: Relationship Engine — Persistent interaction history and healthy ratio tracking.
Strictly follows RUKA-VI Chapter IX.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class RelationshipType(str, Enum):
    OWNER = "OWNER"
    INTRODUCED = "INTRODUCED"  # diperkenalkan (delegasi)
    SERVICE = "SERVICE"  # bot/sistem lain
    UNKNOWN = "UNKNOWN"


@dataclass
class Relationship:
    """Satu relasi persisten — kunci: profile_id."""

    profile_id: str
    rel_type: RelationshipType
    first_seen_ms: int = field(default_factory=lambda: int(time.time() * 1000))
    last_seen_ms: int = field(default_factory=lambda: int(time.time() * 1000))
    interaction_count: int = 0
    positive_count: int = 0
    introduction_source: str | None = None  # profile_id pemberi introduksi
    provenance: dict[str, Any] = field(default_factory=dict)
    notes: list[str] = field(default_factory=list)

    def record_interaction(
        self, positive: bool = True, now_ms: int | None = None
    ) -> None:
        self.interaction_count += 1
        if positive:
            self.positive_count += 1
        self.last_seen_ms = now_ms if now_ms is not None else int(time.time() * 1000)

    @property
    def healthy_ratio(self) -> float:
        """Rasio interaksi positif — input trust.history."""
        if self.interaction_count == 0:
            return 0.5  # netral sebelum ada sejarah
        return self.positive_count / self.interaction_count


class RelationshipEngine:
    """Registri relasi + pertumbuhan sehat dari sejarah interaksi."""

    def __init__(self) -> None:
        self._rels: dict[str, Relationship] = {}

    def upsert(self, rel: Relationship) -> Relationship:
        if rel.profile_id in self._rels:
            old = self._rels[rel.profile_id]
            old.rel_type = rel.rel_type
            old.interaction_count = max(old.interaction_count, rel.interaction_count)
            old.positive_count = max(old.positive_count, rel.positive_count)
            old.last_seen_ms = max(old.last_seen_ms, rel.last_seen_ms)
            if rel.introduction_source and not old.introduction_source:
                old.introduction_source = rel.introduction_source
            old.provenance.update(rel.provenance)
            return old
        self._rels[rel.profile_id] = rel
        return rel

    def get(self, profile_id: str) -> Relationship | None:
        return self._rels.get(profile_id)

    def record_interaction(
        self, profile_id: str, positive: bool = True, now_ms: int | None = None
    ) -> None:
        rel = self._rels.get(profile_id)
        if rel is None:
            raise KeyError(f"relasi untuk {profile_id} tidak ditemukan")
        rel.record_interaction(positive=positive, now_ms=now_ms)
