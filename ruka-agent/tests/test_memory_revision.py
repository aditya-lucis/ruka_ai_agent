from datetime import datetime, timedelta, timezone
import pytest
from src.memory.models import MemoryKind, MemoryRecord, Provenance
from src.memory.revision import (MemoryRevisionStrategy,
                                 consolidation_sweep, looks_like_override)

T0 = datetime(2026, 9, 7, 10, 0, tzinfo=timezone.utc)

class FakeStore:
    def __init__(self, records):
        self.records = records
        self.superseded: list[tuple[int, int, str]] = []

    def query_memories(self, kinds, active_only=True):
        return [r for r in self.records if r.kind.value in kinds
                and r.supersedes_id is None]

    def mark_superseded(self, loser_id, winner_id, reason):
        self.superseded.append((loser_id, winner_id, reason))

def _pref(content, src="conversation", days_old=0.0, conf=0.8):
    rec = MemoryRecord(kind=MemoryKind.PREFERENCE, content=content,
                       confidence=conf,
                       provenance=Provenance(source_type=src, source_id="t"))
    rec.created_at = T0 - timedelta(days=days_old)
    return rec

def test_scenario_x_then_y_y_wins_and_old_archived():
    """Skenario spesifikasi: X (90 hari lalu) lalu Y (baru)."""
    old = _pref("Bos suka pendekatan monolith untuk service baru", days_old=90)
    old.id = 1
    new = _pref("Sekarang Bos lebih suka microservice dengan modular monolith")
    new.id = 2
    store = FakeStore([old])
    strat = MemoryRevisionStrategy(store)
    verdict = strat.revise_preference(new, now=T0)
    assert verdict is not None and verdict.winner is new
    strat.apply(verdict)
    assert store.superseded == [(1, 2, verdict.reason)]

def test_old_strong_evidence_can_defeat_new_weak():
    old = _pref("Bos suka pendekatan monolith", days_old=30, conf=0.95)
    old.id = 1
    new = _pref("Sekarang Bos suka microservice", src="system", conf=0.2)
    new.id = 2
    verdict = MemoryRevisionStrategy(FakeStore([old])).revise_preference(new, now=T0)
    assert verdict.winner is old       # bukti menang usia

def test_override_signal_detected():
    assert looks_like_override("Sekarang saya lebih suka YAML") is True
    assert looks_like_override("Hari ini cuaca cerah") is False

def test_no_conflict_returns_none():
    other = _pref("Bos suka tema gelap pada editor", days_old=10)
    other.id = 1
    new = _pref("Sekarang Bos lebih suka microservice")
    new.id = 2
    assert MemoryRevisionStrategy(FakeStore([other])).revise_preference(new, now=T0) is None
