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


from ruka_companion.sdk.manifest import (
    PluginManifest,
    PLUGIN_PERMISSIONS,
    RISKY_PERMISSIONS,
)
from ruka_companion.sdk.registry import (
    PluginRegistry,
    PluginState,
)
from ruka_companion.plugins.summarizer import Summarizer, summarize


class TestPluginManifest:
    def test_valid_manifest(self):
        m = PluginManifest(
            plugin_id="notes-summarizer",
            name="Notes Summarizer",
            version="1.0.0",
            description="Ekstraktif TF-MMR summarizer untuk memori Ruka.",
            ruka_compat="0.1.x",
            permissions=["memory.read", "event.subscribe"],
            entrypoint="ruka_companion.plugins.summarizer:summarize",
        )
        assert m.plugin_id == "notes-summarizer"
        assert m.as_dict()["version"] == "1.0.0"

    def test_invalid_slug_rejected(self):
        with pytest.raises(ValueError):
            PluginManifest(
                plugin_id="Invalid_Slug!",
                name="Bad",
                version="1.0.0",
                description="Deskripsi panjang memenuhi syarat batas minimal.",
                ruka_compat="0.1.0",
                entrypoint="x:y",
            )

    def test_invalid_semver_rejected(self):
        with pytest.raises(ValueError):
            PluginManifest(
                plugin_id="bad-semver",
                name="Bad",
                version="v1",
                description="Deskripsi panjang memenuhi syarat batas minimal.",
                ruka_compat="0.1.0",
                entrypoint="x:y",
            )

    def test_unknown_permission_default_deny(self):
        with pytest.raises(ValueError, match="izin tak dikenal"):
            PluginManifest(
                plugin_id="eager-tool",
                name="Eager",
                version="1.0.0",
                description="Deskripsi panjang memenuhi syarat batas minimal.",
                ruka_compat="0.1.0",
                permissions=["super_admin.root"],
                entrypoint="x:y",
            )

    def test_duplicate_permissions_rejected(self):
        with pytest.raises(ValueError, match="izin duplikat"):
            PluginManifest(
                plugin_id="dup-perm",
                name="Dup",
                version="1.0.0",
                description="Deskripsi panjang memenuhi syarat batas minimal.",
                ruka_compat="0.1.0",
                permissions=["memory.read", "memory.read"],
                entrypoint="x:y",
            )

    def test_risky_permission_requires_declaration(self):
        m = PluginManifest(
            plugin_id="terminal-tool",
            name="Terminal Tool",
            version="1.0.0",
            description="Plugin yang mengeksekusi perintah shell berbahaya.",
            ruka_compat="0.1.0",
            permissions=["terminal.execute"],
            entrypoint="x:y",
            must_declare_risk=False,
        )
        with pytest.raises(ValueError, match="menuntut must_declare_risk=True"):
            m.validate_risk()

    def test_declared_risk_without_notes_rejected(self):
        m = PluginManifest(
            plugin_id="terminal-tool",
            name="Terminal Tool",
            version="1.0.0",
            description="Plugin yang mengeksekusi perintah shell berbahaya.",
            ruka_compat="0.1.0",
            permissions=["terminal.execute"],
            entrypoint="x:y",
            must_declare_risk=True,
            risk_notes="",
        )
        with pytest.raises(ValueError, match="tanpa risk_notes"):
            m.validate_risk()


class TestPluginRegistry:
    def test_lifecycle_and_order(self):
        reg = PluginRegistry()
        m_base = PluginManifest(
            plugin_id="base-plugin",
            name="Base",
            version="0.1.0",
            description="Plugin fondasi dasar yang dibutuhkan dependensi.",
            ruka_compat="0.1.0",
            permissions=["memory.read"],
            entrypoint="pkg.base:init",
        )
        m_dep = PluginManifest(
            plugin_id="child-plugin",
            name="Child",
            version="0.1.0",
            description="Plugin turunan yang bergantung pada base-plugin.",
            ruka_compat="0.1.0",
            permissions=["memory.write"],
            dependencies=["base-plugin"],
            entrypoint="pkg.child:init",
        )

        reg.discover(m_base)
        reg.discover(m_dep)

        reg.validate("base-plugin")
        reg.validate("child-plugin")

        # Topologically, base-plugin must come before child-plugin
        order = reg.install_order()
        assert order.index("base-plugin") < order.index("child-plugin")

    def test_cycle_dependency_rejected(self):
        reg = PluginRegistry()
        m1 = PluginManifest(
            plugin_id="p-one",
            name="One",
            version="0.1.0",
            description="Deskripsi panjang memenuhi syarat batas minimal.",
            ruka_compat="0.1.0",
            dependencies=["p-two"],
            entrypoint="p1:x",
        )
        m2 = PluginManifest(
            plugin_id="p-two",
            name="Two",
            version="0.1.0",
            description="Deskripsi panjang memenuhi syarat batas minimal.",
            ruka_compat="0.1.0",
            dependencies=["p-one"],
            entrypoint="p2:x",
        )
        reg.discover(m1)
        reg.discover(m2)

        rec = reg.validate("p-one")
        assert rec.state == PluginState.REJECTED
        assert "ber-SIKLUS" in rec.rejection_reason

    def test_risky_permission_install_without_owner_confirm_rejected(self):
        reg = PluginRegistry()
        m = PluginManifest(
            plugin_id="eager-shell",
            name="Eager",
            version="0.1.0",
            description="Deskripsi panjang memenuhi syarat batas minimal.",
            ruka_compat="0.1.0",
            permissions=["terminal.execute"],
            entrypoint="x:y",
            must_declare_risk=True,
            risk_notes="butuh shell",
        )
        reg.discover(m)
        reg.validate("eager-shell")
        reg.stage("eager-shell")

        rec = reg.install("eager-shell", owner_confirm=False)
        assert rec.state == PluginState.REJECTED
        assert "butuh konfirmasi pemilik" in rec.rejection_reason

    def test_install_enable_and_permission_enforcement(self):
        reg = PluginRegistry()
        m = PluginManifest(
            plugin_id="reader-tool",
            name="Reader",
            version="0.1.0",
            description="Deskripsi panjang memenuhi syarat batas minimal.",
            ruka_compat="0.1.0",
            permissions=["memory.read"],
            entrypoint="x:y",
        )
        reg.discover(m)
        reg.validate("reader-tool")
        reg.stage("reader-tool")
        reg.install("reader-tool")

        # In INSTALLED state, cannot use permission until ENABLED
        allowed, reason = reg.check_permission("reader-tool", "memory.read")
        assert allowed is False
        assert "harus ENABLED" in reason

        reg.enable("reader-tool")
        allowed, reason = reg.check_permission("reader-tool", "memory.read")
        assert allowed is True
        assert reason == "granted"

        # Permission not requested is denied
        allowed2, _ = reg.check_permission("reader-tool", "memory.write")
        assert allowed2 is False

        # When disabled, permission denied
        reg.disable("reader-tool")
        allowed3, _ = reg.check_permission("reader-tool", "memory.read")
        assert allowed3 is False

        # Removal clears permissions
        reg.remove("reader-tool")
        assert reg._get("reader-tool").state == PluginState.REMOVED
        assert len(reg._get("reader-tool").granted_permissions) == 0


class TestReferencePlugin:
    def test_tf_mmr_summarizer_deterministic(self):
        text = (
            "Ruka adalah asisten AI pribadi yang setia. "
            "Dia memiliki arsitektur zero-trust berdaulat. "
            "Sistem memorinya menggunakan version vector dan tombstone. "
            "Semua aksi penting membutuhkan konfirmasi pemilik. "
            "Telegram bot bertindak sebagai jembatan komunikasi jarak jauh. "
            "Kamera dan suara memberikan persepsi multimodal. "
            "Dengan prinsip default deny keamanan laptop selalu terjaga. "
            "Ruka siap mendampingi Tuanku setiap saat."
        )
        res1 = summarize(text, k=3)
        res2 = summarize(text, k=3)

        assert res1 == res2
        assert res1["n_sentences"] == 8
        assert len(res1["selected"]) == 3
        assert res1["method"] == "tf+mmr-extractive"
        assert len(res1["summary"]) > 0

    def test_empty_text_summarization(self):
        res = summarize("", k=3)
        assert res["summary"] == ""
        assert res["n_sentences"] == 0

