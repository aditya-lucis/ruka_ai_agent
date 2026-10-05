# -*- coding: utf-8 -*-
"""Sentinel Mode for Screen Lock & User Absence (FR-OS-14).

Menegakkan protokol perlindungan saat layar terkunci atau pengguna absen > 5 menit:
- Avatar tidur (12 fps)
- Kamera mati (blind mode aktif)
- Notifikasi tertahan
- Audit keamanan per jam
"""
from __future__ import annotations

import time
from typing import Callable, Optional


class SentinelModeManager:
    ABSENCE_THRESHOLD_S = 300.0  # 5 menit

    def __init__(
        self,
        on_enter_sentinel: Optional[Callable[[], None]] = None,
        on_exit_sentinel: Optional[Callable[[], None]] = None,
    ) -> None:
        self.on_enter_sentinel = on_enter_sentinel
        self.on_exit_sentinel = on_exit_sentinel

        self.is_screen_locked: bool = False
        self.is_sentinel_active: bool = False
        self.last_user_activity: float = time.time()
        self.last_audit_time: float = time.time()

    def set_screen_lock(self, locked: bool) -> bool:
        """Dipicu oleh event OS screen lock/unlock."""
        self.is_screen_locked = locked
        return self._evaluate_state()

    def report_activity(self) -> bool:
        """Melaporkan interaksi pengguna aktif (keyboard, mouse, suara)."""
        self.last_user_activity = time.time()
        if self.is_sentinel_active and not self.is_screen_locked:
            self.is_sentinel_active = False
            if self.on_exit_sentinel:
                self.on_exit_sentinel()
        return self.is_sentinel_active

    def check_idle(self, current_time: Optional[float] = None) -> bool:
        """Memeriksa apakah absen > 300 detik."""
        now = current_time if current_time is not None else time.time()
        if (now - self.last_user_activity) >= self.ABSENCE_THRESHOLD_S:
            if not self.is_sentinel_active:
                self.is_sentinel_active = True
                if self.on_enter_sentinel:
                    self.on_enter_sentinel()
        return self.is_sentinel_active

    def _evaluate_state(self) -> bool:
        should_be_active = self.is_screen_locked or ((time.time() - self.last_user_activity) >= self.ABSENCE_THRESHOLD_S)
        if should_be_active and not self.is_sentinel_active:
            self.is_sentinel_active = True
            if self.on_enter_sentinel:
                self.on_enter_sentinel()
        elif not should_be_active and self.is_sentinel_active:
            self.is_sentinel_active = False
            if self.on_exit_sentinel:
                self.on_exit_sentinel()
        return self.is_sentinel_active
