# -*- coding: utf-8 -*-
"""Electron Ghost Window & Polite Pointer Gate (FR-OS-01).

Mengelola konfigurasi jendela hantu desktop dan gerbang pointer sopan:
- 5 properti hantu: transparan, tanpa dekorasi/frame, selalu di atas, tanpa bilah tugas, tidak mencuri fokus
- Gerbang pointer dengan histeresis 2 piksel dan debounce 8 ms
- Menghitung apakah klik mouse harus tembus (click-through) atau berinteraksi dengan RUKA
"""
from __future__ import annotations

import math
import time
from typing import Tuple
from src.os_companion.models import GhostWindowConfig


class PointerGate:
    def __init__(
        self,
        hysteresis_px: int = 2,
        debounce_ms: float = 8.0,
    ) -> None:
        self.hysteresis_px = hysteresis_px
        self.debounce_s = debounce_ms / 1000.0

        self.last_pos: Tuple[int, int] = (-999, -999)
        self.last_event_time: float = 0.0
        self.is_interactive: bool = False

    def process_mouse_move(
        self,
        x: int,
        y: int,
        avatar_bounds: Tuple[int, int, int, int],  # (left, top, width, height)
        timestamp: float | None = None,
    ) -> bool:
        """Memproses pergerakan kursor dengan histeresis 2px dan debounce 8ms.

        Returns:
            True jika pointer aktif berinteraksi dengan avatar (capture pointer),
            False jika pointer tembus pandang (click-through ke aplikasi belakang).
        """
        now = timestamp if timestamp is not None else time.perf_counter()

        # 1. Debounce 8 ms
        if (now - self.last_event_time) < self.debounce_s:
            return self.is_interactive

        # 2. Histeresis 2 px
        dx = x - self.last_pos[0]
        dy = y - self.last_pos[1]
        dist = math.hypot(dx, dy)
        if dist < self.hysteresis_px:
            return self.is_interactive

        self.last_pos = (x, y)
        self.last_event_time = now

        # 3. Hit-test apakah kursor berada di dalam batas avatar
        ax, ay, aw, ah = avatar_bounds
        inside = (ax <= x <= ax + aw) and (ay <= y <= ay + ah)
        self.is_interactive = inside
        return self.is_interactive


class GhostWindowManager:
    def __init__(self, config: GhostWindowConfig | None = None) -> None:
        self.config = config or GhostWindowConfig()
        self.pointer_gate = PointerGate(
            hysteresis_px=self.config.pointer_hysteresis_px,
            debounce_ms=self.config.debounce_ms,
        )

    def get_window_options(self) -> dict[str, bool]:
        """Mengembalikan opsi BrowserWindow Electron yang memenuhi 5 properti hantu."""
        return {
            "transparent": self.config.transparent,
            "frame": self.config.frame,
            "alwaysOnTop": self.config.always_on_top,
            "skipTaskbar": self.config.skip_taskbar,
            "focusable": self.config.focusable,
        }
