# -*- coding: utf-8 -*-
"""Second-Order Damped Spring Physics & 5-Segment Tail (FR-PR-04).

Fisika sekunder untuk telinga kucing vampir dan ekor lima segmen:
- Telinga: Pegas redam orde dua k=180, zeta=0.7
  d2x/dt2 + 2*zeta*omega*dx/dt + omega^2*(x - x_target) = 0
- Ekor: Rantai tunda 5 segmen (60-90 ms per tingkat) dengan efek cambuk 1.6x di ujung
"""
from __future__ import annotations

import collections
import math
from src.presence.models import EarPose, TailPose


class SecondOrderSpring:
    """Pegas redam orde dua analitis/Euler semi-implisit."""

    def __init__(self, k: float = 180.0, zeta: float = 0.7) -> None:
        self.k = k
        self.zeta = zeta
        self.omega = math.sqrt(k)  # ~13.416 rad/s
        self.pos: float = 0.0
        self.vel: float = 0.0

    def update(self, target_pos: float, dt: float) -> float:
        dt = max(0.001, min(0.05, dt))
        # Percepatan pegas: a = -k*(pos - target) - 2*zeta*omega*vel
        accel = -self.k * (self.pos - target_pos) - (2.0 * self.zeta * self.omega * self.vel)
        self.vel += accel * dt
        self.pos += self.vel * dt
        return self.pos

    def reset(self, val: float = 0.0) -> None:
        self.pos = val
        self.vel = 0.0


class EarPhysicsEngine:
    def __init__(self) -> None:
        self.left_spring = SecondOrderSpring(k=180.0, zeta=0.7)
        self.right_spring = SecondOrderSpring(k=180.0, zeta=0.7)
        self.flick_timer: float = 0.0

    def trigger_flick(self, duration_s: float = 0.15) -> None:
        """Memicu kedutan telinga sebelum rotasi kepala."""
        self.flick_timer = duration_s

    def update(self, target_left: float, target_right: float, dt: float) -> EarPose:
        flick = False
        if self.flick_timer > 0.0:
            self.flick_timer -= dt
            flick = True
            # Beri sentakan sudut saat flick aktif
            target_left += 15.0 * math.sin(self.flick_timer * 40.0)
            target_right -= 15.0 * math.sin(self.flick_timer * 40.0)

        left = self.left_spring.update(target_left, dt)
        right = self.right_spring.update(target_right, dt)
        return EarPose(left_angle_deg=round(left, 2), right_angle_deg=round(right, 2), flick_active=flick)


class TailPhysicsEngine:
    """Ekor 5-segmen dengan rantai tunda (delay chain 75ms) dan pengali cambuk 1.6x di ujung."""

    def __init__(self, delay_per_segment_ms: float = 75.0) -> None:
        self.delay_s = delay_per_segment_ms / 1000.0
        # Ring buffer riwayat sudut dasar ekor
        self.history: collections.deque[tuple[float, float]] = collections.deque(maxlen=300)
        self.whip_factors = tuple(1.0 + 0.6 * (i / 4.0) for i in range(5))  # (1.0, 1.15, 1.3, 1.45, 1.6)

    def update(self, base_angle_deg: float, current_time: float) -> TailPose:
        self.history.append((current_time, base_angle_deg))

        angles: list[float] = []
        for i in range(5):
            target_time = current_time - (i * self.delay_s)
            # Cari sudut terdekat pada target_time
            matched_angle = base_angle_deg
            for t_hist, ang in reversed(self.history):
                if t_hist <= target_time:
                    matched_angle = ang
                    break
            # Terapkan pengali cambuk
            amplified = matched_angle * self.whip_factors[i]
            angles.append(round(amplified, 2))

        return TailPose(
            segments_deg=(angles[0], angles[1], angles[2], angles[3], angles[4]),
            whip_intensity=self.whip_factors[4],
        )
