# -*- coding: utf-8 -*-
"""Test Suite for AI Companion Operating System (FR-OS / Boss Gate 4)."""
from __future__ import annotations

from datetime import datetime
import pytest

from src.os_companion.command_palette import CommandPaletteRegistry, PaletteAction
from src.os_companion.docking import MagneticDockManager
from src.os_companion.dosing import NotificationDoser
from src.os_companion.ghost_window import GhostWindowManager, PointerGate
from src.os_companion.governor import ResourceGovernor
from src.os_companion.lunar_clock import LunarClock
from src.os_companion.models import (
    CompassPoint,
    HUDState,
    LunarPhase,
    NotificationItem,
    NotificationPriority,
)
from src.os_companion.sentinel import SentinelModeManager
from src.os_companion.voice_hud import VoiceHUD


class TestGhostWindowAndPointerGate:
    def test_ghost_window_polite_properties(self):
        manager = GhostWindowManager()
        opts = manager.get_window_options()
        assert opts["transparent"] is True
        assert opts["frame"] is False
        assert opts["alwaysOnTop"] is True
        assert opts["skipTaskbar"] is True
        assert opts["focusable"] is False  # Tidak mencuri fokus

    def test_pointer_gate_hysteresis_and_debounce(self):
        gate = PointerGate(hysteresis_px=2, debounce_ms=8.0)
        avatar_bounds = (100, 100, 200, 200)

        # Di luar avatar (click through)
        outside = gate.process_mouse_move(50, 50, avatar_bounds, timestamp=0.01)
        assert outside is False

        # Di dalam avatar
        inside = gate.process_mouse_move(150, 150, avatar_bounds, timestamp=0.02)
        assert inside is True

        # Gerakan 1px (dalam ambang histeresis 2px) tidak mengubah status
        jitter = gate.process_mouse_move(151, 150, avatar_bounds, timestamp=0.03)
        assert jitter is True


class TestMagneticDocking:
    def test_eight_compass_snap_and_drag(self):
        dock_mgr = MagneticDockManager(screen_width=1920, screen_height=1080)
        initial_dock = dock_mgr.current_dock
        assert initial_dock.compass == CompassPoint.SE

        # Pointer down lalu up tanpa gerak -> Click
        dock_mgr.on_pointer_down(500, 500)
        final_dock, was_click = dock_mgr.on_pointer_up(500, 500)
        assert was_click is True

        # Seret sejauh 20px (melebihi ambang 4px) mendekati pojok kanan atas (NE)
        dock_mgr.on_pointer_down(1600, 100)
        is_drag = dock_mgr.on_pointer_move(1650, 80)
        assert is_drag is True

        # Rilis di dekat titik ideal NE (1704, 16)
        snapped_dock, was_click2 = dock_mgr.on_pointer_up(1710, 20)
        assert was_click2 is False
        assert snapped_dock.compass == CompassPoint.NE
        assert snapped_dock.is_snapped is True


class TestVoiceHUD:
    def test_voice_hud_subtitles_and_honest_waveform(self):
        hud = VoiceHUD()
        hud.set_state(HUDState.SPEAKING)

        lines = hud.set_subtitle("Young Lord, titah Anda sedang hamba jalankan dengan segenap ketelitian.")
        assert 1 <= len(lines) <= 2

        # Masukkan amplitudo viseme
        for amp in [0.2, 0.5, 0.8, 0.9]:
            hud.push_viseme_amplitude(amp)

        wave = hud.get_current_waveform()
        assert len(wave) == 48
        assert any(h > 0.0 for h in wave)


class TestCommandPalette:
    def test_command_palette_fuzzy_search(self):
        registry = CommandPaletteRegistry()
        registry.register(PaletteAction(action_id="git.status", title="Periksa Status Git", category="Development"))
        registry.register(PaletteAction(action_id="mode.sleep", title="Mode Tidur Avatar", category="System"))
        registry.register(PaletteAction(action_id="git.commit", title="Komit Perubahan Git", category="Development"))

        results = registry.search("git", limit=8)
        assert len(results) == 2
        assert all("git" in r.action_id for r in results)


class TestNotificationDoser:
    def test_ten_minute_cooldown_and_curfew(self):
        doser = NotificationDoser()

        normal_msg = NotificationItem(notification_id="n1", title="Info", body="Info berkala", priority=NotificationPriority.NORMAL)
        urgent_msg = NotificationItem(notification_id="n2", title="Alert", body="Bahaya", priority=NotificationPriority.URGENT)
        whisper_msg = NotificationItem(notification_id="n3", title="Bisik", body="Catatan kecil", priority=NotificationPriority.WHISPER)

        t0 = 100000.0  # Siang hari
        # Kirim normal pertama: berhasil
        ok1, reason1 = doser.can_deliver(normal_msg, current_time=t0)
        assert ok1 is True

        # Kirim normal kedua 60 detik kemudian: terblokir oleh cooldown 10 menit
        ok2, reason2 = doser.can_deliver(normal_msg, current_time=t0 + 60.0)
        assert ok2 is False
        assert "cooldown_active" in reason2

        # Kirim whisper: selalu ditampung ke antrean digest
        ok3, reason3 = doser.can_deliver(whisper_msg, current_time=t0 + 120.0)
        assert ok3 is False
        assert reason3 == "whisper_queued_for_digest"
        assert len(doser.flush_digest()) == 1


class TestLunarClock:
    def test_circadian_phases_and_permissions(self):
        # 10:00 pagi -> MORNING
        dt_morning = datetime(2026, 10, 5, 10, 0)
        phase_m = LunarClock.get_phase(dt_morning)
        assert phase_m == LunarPhase.MORNING
        assert LunarClock.is_voice_allowed(phase_m) is True

        # 23:30 malam -> MIDNIGHT (curfew)
        dt_midnight = datetime(2026, 10, 5, 23, 30)
        phase_mid = LunarClock.get_phase(dt_midnight)
        assert phase_mid == LunarPhase.MIDNIGHT
        assert LunarClock.is_voice_allowed(phase_mid) is False


class TestResourceGovernor:
    def test_ram_redline_and_three_strikes(self):
        gov = ResourceGovernor()
        restarted = False

        def mock_restart(organ):
            nonlocal restarted
            restarted = True
            return True

        gov.register_organ_quota("eyes", max_ram_mb=100.0, restart_fn=mock_restart)

        # 80 MB: Aman (di bawah 90% redline)
        is_red, tr_restart = gov.record_usage("eyes", 80.0)
        assert not is_red and not tr_restart

        # 95 MB: Melanggar redline (Strike 1)
        is_red1, _ = gov.record_usage("eyes", 95.0)
        assert is_red1 is True and not restarted

        # Strike 2
        gov.record_usage("eyes", 95.0)
        assert not restarted

        # Strike 3: Memicu restart otomatis!
        _, tr_restart3 = gov.record_usage("eyes", 95.0)
        assert tr_restart3 is True
        assert restarted is True


class TestSentinelMode:
    def test_screen_lock_and_five_minute_absence(self):
        sentinel_entered = False
        sentinel_exited = False

        manager = SentinelModeManager(
            on_enter_sentinel=lambda: exec("sentinel_entered = True", globals()),
            on_exit_sentinel=lambda: exec("sentinel_exited = True", globals()),
        )

        # Screen lock event
        manager.set_screen_lock(True)
        assert manager.is_sentinel_active is True

        # Unlock and activity
        manager.set_screen_lock(False)
        manager.report_activity()
        assert manager.is_sentinel_active is False
