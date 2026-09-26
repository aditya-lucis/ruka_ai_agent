"""RUKA VI: Tests for Companion FSM, Presence Engine, and SDK.
Strictly follows RUKA-VI Chapter XIV, XV, XXI, and XXV.
"""

from __future__ import annotations

import pytest

from ruka_companion.companion.state import (
    COMPANION_FSM,
    CompanionContext,
    CompanionEvents,
    CompanionMachine,
    CompanionStates,
)
from ruka_companion.presence.engine import (
    CapabilityStatus,
    OperatingMode,
    PresenceEngine,
    default_probes,
)
from ruka_companion.voice.speaker import AcousticGaussianProvider


class TestCompanion:
    """Uji formal FSM Companion 11-status (Part XIV)."""

    def test_initial_state_ready(self):
        machine = CompanionMachine()
        assert machine.state == CompanionStates.READY

    def test_guard_rejects_unconfirmed_permission(self):
        machine = CompanionMachine()
        machine.fire(CompanionEvents.ACTIVATE)
        assert machine.state == CompanionStates.ACTIVE
        machine.fire(CompanionEvents.PROCESS)
        assert machine.state == CompanionStates.PROCESSING
        machine.fire(CompanionEvents.NEED_PERMISSION)
        assert machine.state == CompanionStates.WAITING_PERMISSION

        # Konteks izin belum diberikan -> harus ditolak keras (I1)
        ctx = CompanionContext(permission_granted=False)
        with pytest.raises(PermissionError, match="I1"):
            machine.fire(CompanionEvents.PERMISSION_GRANTED, context=ctx)

        # Status tetap di WAITING_PERMISSION
        assert machine.state == CompanionStates.WAITING_PERMISSION

    def test_guard_accepts_confirmed_permission(self):
        machine = CompanionMachine()
        machine.fire(CompanionEvents.ACTIVATE)
        machine.fire(CompanionEvents.PROCESS)
        machine.fire(CompanionEvents.NEED_PERMISSION)
        assert machine.state == CompanionStates.WAITING_PERMISSION

        ctx = CompanionContext(permission_granted=True, actor_profile="BOS")
        nxt = machine.fire(CompanionEvents.PERMISSION_GRANTED, context=ctx)
        assert nxt == CompanionStates.PROCESSING
        assert machine.state == CompanionStates.PROCESSING

    def test_permission_denied_returns_to_ready(self):
        machine = CompanionMachine()
        machine.fire(CompanionEvents.ACTIVATE)
        machine.fire(CompanionEvents.PROCESS)
        machine.fire(CompanionEvents.NEED_PERMISSION)
        machine.fire(CompanionEvents.PERMISSION_DENIED)
        assert machine.state == CompanionStates.READY

    def test_illegal_transition_raises_value_error(self):
        machine = CompanionMachine()
        with pytest.raises(ValueError, match="transisi ilegal"):
            machine.fire(CompanionEvents.FINISH)

    def test_sleep_wake_cycle(self):
        machine = CompanionMachine()
        machine.fire(CompanionEvents.SLEEP)
        assert machine.state == CompanionStates.SLEEPING
        machine.fire(CompanionEvents.WAKE)
        assert machine.state == CompanionStates.WAKING
        machine.fire(CompanionEvents.RESUME)
        assert machine.state == CompanionStates.READY

    def test_error_recovery_cycle(self):
        machine = CompanionMachine()
        machine.fire(CompanionEvents.FAIL)
        assert machine.state == CompanionStates.ERROR
        machine.fire(CompanionEvents.RESUME)
        assert machine.state == CompanionStates.READY

    def test_degraded_recovery_cycle(self):
        machine = CompanionMachine()
        machine.fire(CompanionEvents.DEGRADE)
        assert machine.state == CompanionStates.DEGRADED
        machine.fire(CompanionEvents.RECOVER)
        assert machine.state == CompanionStates.RECOVERING
        machine.fire(CompanionEvents.RESUME)
        assert machine.state == CompanionStates.READY

    def test_speaking_interruption(self):
        machine = CompanionMachine()
        machine.fire(CompanionEvents.ACTIVATE)
        machine.fire(CompanionEvents.PROCESS)
        machine.fire(CompanionEvents.SPEAK)
        assert machine.state == CompanionStates.SPEAKING
        machine.fire(CompanionEvents.INTERRUPT)
        assert machine.state == CompanionStates.ACTIVE

    def test_offline_absorbs_further_interactions(self):
        machine = CompanionMachine()
        machine.fire(CompanionEvents.SHUTDOWN)
        assert machine.state == CompanionStates.OFFLINE

        # Status terminal menolak semua interaksi lanjutan (I2)
        with pytest.raises(ValueError, match="transisi ilegal"):
            machine.fire(CompanionEvents.ACTIVATE)
        with pytest.raises(ValueError, match="transisi ilegal"):
            machine.fire(CompanionEvents.RESUME)

    def test_static_analysis_invariants_and_reachability(self):
        # I3: semua 11 status terjangkau dari READY dan tidak ada dead state selain OFFLINE
        assert len(COMPANION_FSM.states) == 11
        assert COMPANION_FSM.unreachable_states() == set()
        assert COMPANION_FSM.dead_states() == set()
        assert COMPANION_FSM.check_invariants() == []


class TestPresence:
    """Uji PresenceEngine, mode efektif A/B/C, dan kejujuran ketersediaan (Part XV)."""

    def test_effective_mode_local_only(self):
        eng = PresenceEngine(runtime_state="READY", cloud_link="DISCONNECTED")
        assert eng.effective_mode() == OperatingMode.LOCAL_ONLY

    def test_effective_mode_hybrid(self):
        eng = PresenceEngine(runtime_state="READY", cloud_link="CONNECTED")
        assert eng.effective_mode() == OperatingMode.HYBRID

    def test_effective_mode_remote_laptop_offline(self):
        for s in ("OFFLINE", "SHUTDOWN", "CRASHED"):
            eng = PresenceEngine(runtime_state=s, cloud_link="CONNECTED")
            assert eng.effective_mode() == OperatingMode.REMOTE

    def test_effective_mode_offline_disconnected(self):
        eng = PresenceEngine(runtime_state="OFFLINE", cloud_link="DISCONNECTED")
        assert eng.effective_mode() == OperatingMode.LOCAL_ONLY

    def test_honest_answer_when_available(self):
        probes = {
            "test.cap": lambda: CapabilityStatus(
                "test.cap", True, "siap", "local"
            )
        }
        eng = PresenceEngine(probes=probes)
        ans = eng.answer_availability("test.cap")
        assert ans == "test.cap tersedia."

    def test_honest_answer_when_unavailable_contains_reason(self):
        probes = {
            "tools.terminal": lambda: CapabilityStatus(
                "tools.terminal", False, "laptop offline", "local"
            )
        }
        eng = PresenceEngine(probes=probes)
        ans = eng.answer_availability("tools.terminal")
        assert "TIDAK tersedia" in ans
        assert "laptop offline" in ans

    def test_honest_answer_when_unknown(self):
        eng = PresenceEngine()
        ans = eng.answer_availability("unknown.capability")
        assert ans == "unknown.capability tidak dikenal sistem."

    def test_default_probes_structure(self):
        matcher_mock = type(
            "MockMatcher", (), {"capability": lambda self: {"available": False, "reason": "kosong"}}
        )()
        speaker = AcousticGaussianProvider()
        probes = default_probes(
            matcher_face=matcher_mock,
            speaker_provider=speaker,
            cloud_link_state=lambda: "CONNECTED",
        )
        assert "voice.asr" in probes
        assert "voice.speaker" in probes
        assert "vision.face" in probes
        assert "cloud.link" in probes
        assert "tools.terminal" in probes

        eng = PresenceEngine(
            runtime_state="READY", cloud_link="CONNECTED", probes=probes
        )
        rep = eng.report()
        assert rep["mode"] == "HYBRID"
        assert rep["cloud_link"] == "CONNECTED"
        assert len(rep["capabilities"]) == 5
        assert rep["privacy"] == {"mic": "OFF", "camera": "OFF"}
