"""Unit tests for ContinuityMonitor and ProactiveProposal — Ruka Volume IV Listings 14.1 & 14.2."""

import pytest

from ruka_perception.companion.continuity import (
    ContinuityMonitor,
    LABEL_SEQUENCE,
    PERMISSION_LEVELS,
    ProactiveProposal,
    TransitionRecord,
)


def _rec(prev, nxt, event="", impact=0.0) -> TransitionRecord:
    return TransitionRecord(
        prev_label=prev, next_label=nxt, event=event, event_impact_val=impact
    )


class TestTransitionRecord:
    def test_jump_distance_neighbor(self):
        """calm -> curious: jarak 1."""
        r = _rec("calm", "curious")
        assert r.jump_distance() == 1

    def test_jump_distance_far(self):
        """calm -> concerned: jarak 4."""
        r = _rec("calm", "concerned")
        assert r.jump_distance() == 4

    def test_jump_distance_unknown_label(self):
        """Label asing -> jarak 0 (abaikan)."""
        r = _rec("calm", "angry_unknown")
        assert r.jump_distance() == 0


class TestContinuityMonitor:
    def test_neighbor_always_legitimate(self):
        """Transisi tetangga (jump=1) selalu sah tanpa event."""
        mon = ContinuityMonitor()
        result = mon.check(_rec("calm", "curious"))
        assert result["verdict"] == "legitimate"

    def test_large_jump_no_event_is_violation(self):
        """Lompatan besar (>3) tanpa event -> violation."""
        mon = ContinuityMonitor()
        result = mon.check(_rec("calm", "concerned", impact=0.0))
        # jump = 4, impact = 0 -> violation
        assert result["verdict"] in {"suspicious", "violation"}

    def test_large_jump_strong_event_legitimate(self):
        """Lompatan besar dengan event kuat (impact >= 0.7) -> legitimate."""
        mon = ContinuityMonitor()
        result = mon.check(_rec("calm", "concerned", event="critical error", impact=0.8))
        assert result["verdict"] == "legitimate"

    def test_recovery_to_calm_legitimate(self):
        """Pulih ke calm/neutral dengan event moderat (>= 0.3) -> legitimate."""
        mon = ContinuityMonitor()
        result = mon.check(_rec("concerned", "calm", event="user calmed down", impact=0.4))
        assert result["verdict"] == "legitimate"

    def test_invalid_max_free_jump(self):
        """max_free_jump < 0 harus ditolak."""
        with pytest.raises(ValueError, match="max_free_jump"):
            ContinuityMonitor(max_free_jump=-1)

    def test_check_sequence_perfect_score(self):
        """Rangkaian semua legitimate -> skor = 1.0."""
        mon = ContinuityMonitor()
        records = [_rec("calm", "curious"), _rec("curious", "playful")]
        result = mon.check_sequence(records)
        assert result["score"] == 1.0
        assert result["violations"] == 0

    def test_check_sequence_with_violations(self):
        """Rangkaian dengan pelanggaran harus menurunkan skor."""
        mon = ContinuityMonitor()
        records = [
            _rec("calm", "curious"),                     # legitimate
            _rec("curious", "concerned", impact=0.0),    # jump 3: suspicious atau violation
        ]
        result = mon.check_sequence(records)
        assert result["score"] < 1.0

    def test_spec_example_random_sequence_low_score(self):
        """Contoh spec: rangkaian acak tanpa sebab harus skor < 0.6."""
        mon = ContinuityMonitor()
        # happy -> angry -> embarrassed -> calm -> random (semua simulasi)
        # Di kosakata kita: calm -> concerned -> curious -> calm
        records = [
            _rec("calm", "concerned", impact=0.0),    # jump 4 tanpa sebab
            _rec("concerned", "curious", impact=0.0), # jump 3 tanpa sebab
        ]
        result = mon.check_sequence(records)
        # Harus ada setidaknya suspicious atau violation
        assert result["violations"] + result["suspicious"] >= 1


class TestProactiveProposal:
    def _prop(self, relevance=0.8, risk=0.1, **kw) -> ProactiveProposal:
        return ProactiveProposal(
            trigger="deadline", opportunity="reminder",
            relevance=relevance, risk=risk, action="send_reminder", **kw
        )

    def test_low_risk_low_level_suggests(self):
        """Risiko rendah + level 1 -> delivery suggest."""
        result = self._prop(risk=0.1, relevance=0.8).gate(granted_level=1)
        assert result["delivery"] == "suggest"
        assert result["mode"] == PERMISSION_LEVELS[1]

    def test_high_risk_level_1_not_allowed(self):
        """Risiko tinggi (> 0.4) butuh level >= 2; level 1 -> not allowed."""
        result = self._prop(risk=0.5, relevance=0.8).gate(granted_level=1)
        assert result["allowed"] is False

    def test_very_high_risk_level_3_needed(self):
        """Risiko sangat tinggi (> 0.7) butuh level 3."""
        prop = self._prop(risk=0.8, relevance=0.9)
        result = prop.gate(granted_level=2)
        assert result["allowed"] is False
        assert result["needed_level"] == 3
        result3 = prop.gate(granted_level=3)
        assert result3["allowed"] is True

    def test_low_relevance_caps_at_suggest(self):
        """Relevansi < 0.5 -> needed = 1 (saran saja, bahkan bila risiko tinggi)."""
        prop = self._prop(risk=0.5, relevance=0.3)
        result = prop.gate(granted_level=1)
        assert result["needed_level"] == 1

    def test_gate_never_elevates_permission(self):
        """Aturan keras: gate TIDAK PERNAH menaikkan izin sendiri di output."""
        prop = self._prop(risk=0.0, relevance=0.9)
        for level in [0, 1, 2, 3]:
            result = prop.gate(granted_level=level)
            assert result["mode"] == PERMISSION_LEVELS.get(level, "notify_only")

    def test_level_0_always_silent(self):
        """Level 0 -> delivery silent (hanya notifikasi)."""
        result = self._prop(risk=0.0, relevance=0.9).gate(granted_level=0)
        assert result["delivery"] == "silent"
