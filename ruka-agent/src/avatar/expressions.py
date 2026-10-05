# -*- coding: utf-8 -*-
"""Micro-Expressions & Asymmetric Blush Layer (FR-AV-08).

Mengatur ekspresi mikro dan lapisan rona wajah:
- Reaksi ekspresi mikro cepat: 150 s.d. 300 ms
- Lapisan rona malu (Blush Layer):
  * Waktu naik (rise): 1.2 detik
  * Waktu meluruh (decay): 8.0 detik
- Kontrol taring vampir bangsawan (fangs)
"""
from __future__ import annotations

import time
from typing import Dict


class ExpressionLayerManager:
    BLUSH_RISE_S = 1.2   # 1.2 detik naik
    BLUSH_DECAY_S = 8.0  # 8.0 detik luruh

    def __init__(self) -> None:
        self.blush_intensity: float = 0.0
        self.target_blush: float = 0.0
        self.fangs_intensity: float = 0.0
        self.flat_ears_intensity: float = 0.0
        self.ear_twitch_intensity: float = 0.0

    def trigger_blush(self, intensity: float = 1.0) -> None:
        """Memicu rona pipi saat malu, dipuji Young Lord, atau terkejut sopan."""
        self.target_blush = max(0.0, min(1.0, intensity))

    def set_fangs(self, intensity: float) -> None:
        """Mengatur ketampakan taring vampir [0.0, 1.0]."""
        self.fangs_intensity = max(0.0, min(1.0, intensity))

    def update(self, dt: float) -> Dict[str, float]:
        """Memperbarui nilai blendshape kustom RUKA dengan kurva naik-luruh asimetris."""
        dt = max(0.001, dt)

        # Update blush asimetris
        if self.blush_intensity < self.target_blush:
            # Naik cepat (1.2 detik)
            self.blush_intensity += dt / self.BLUSH_RISE_S
            if self.blush_intensity >= self.target_blush:
                self.blush_intensity = self.target_blush
                # Mulai meluruh setelah mencapai target
                self.target_blush = 0.0
        elif self.blush_intensity > self.target_blush:
            # Luruh perlahan (8.0 detik)
            self.blush_intensity -= dt / self.BLUSH_DECAY_S
            if self.blush_intensity < 0.0:
                self.blush_intensity = 0.0

        return {
            "blush": round(self.blush_intensity, 3),
            "fangs": round(self.fangs_intensity, 3),
            "flat_ears": round(self.flat_ears_intensity, 3),
            "ear_twitch": round(self.ear_twitch_intensity, 3),
        }
