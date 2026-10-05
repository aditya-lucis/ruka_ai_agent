# -*- coding: utf-8 -*-
"""Avatar Eye Animation: Saccades, Micro-Saccades & Pupil Lag (FR-AV-04).

Mengatur dinamika mikroskopis mata RUKA:
- Saccade cepat (durasi 20 s.d. 80 ms)
- Micro-saccade 1 derajat tiap 1 s.d. 2 detik (mencegah tatapan zombie)
- Dinamika pupil dengan tundaan orde satu (1st-order filter tau=300ms) dari arousal emosional
"""
from __future__ import annotations

import math
import random
from typing import Optional
from src.avatar.models import PupilPose


class AvatarEyeAnimator:
    def __init__(self, rng_seed: Optional[int] = None) -> None:
        self.rng = random.Random(rng_seed)
        self.current_dilation: float = 0.5
        self.target_dilation: float = 0.5
        self.tau_dilation_s: float = 0.30  # 300 ms waktu konstan (FR-AV-04)

        self.last_micro_saccade_time: float = 0.0
        self.next_micro_saccade_interval: float = 1.5  # 1.0 - 2.0 detik
        self.saccade_offset_x: float = 0.0
        self.saccade_offset_y: float = 0.0

    def set_target_dilation_from_arousal(self, arousal: float) -> None:
        """Arousal [-1.0, 1.0] memetakan pupil ke [0.2, 0.9]."""
        norm = (arousal + 1.0) / 2.0  # [0.0, 1.0]
        self.target_dilation = max(0.2, min(0.9, 0.2 + norm * 0.7))

    def update(self, current_time: float, dt: float) -> PupilPose:
        dt = max(0.001, min(0.05, dt))

        # 1. Filter orde satu untuk pupil: dD/dt = (target - D) / tau
        alpha = dt / self.tau_dilation_s
        self.current_dilation += alpha * (self.target_dilation - self.current_dilation)
        self.current_dilation = max(0.1, min(1.0, self.current_dilation))

        # 2. Micro-saccade 1 derajat tiap 1-2 detik
        if (current_time - self.last_micro_saccade_time) >= self.next_micro_saccade_interval:
            self.last_micro_saccade_time = current_time
            self.next_micro_saccade_interval = self.rng.uniform(1.0, 2.0)
            # Gerakan acak 1 derajat (-1.0 s.d. 1.0)
            angle = self.rng.uniform(0, 2.0 * math.pi)
            self.saccade_offset_x = math.cos(angle) * 1.0
            self.saccade_offset_y = math.sin(angle) * 1.0
        else:
            # Redam perlahan micro-saccade
            self.saccade_offset_x *= 0.90
            self.saccade_offset_y *= 0.90

        return PupilPose(
            dilation=round(self.current_dilation, 3),
            saccade_offset_x=round(self.saccade_offset_x, 3),
            saccade_offset_y=round(self.saccade_offset_y, 3),
        )
