# -*- coding: utf-8 -*-
"""Humanized Mouse Trajectory Generator (FR-HA-03).

Membangkitkan kurva Bezier kuadratik berjitter alami:
- Titik kontrol P1 dihitung ortogonal dari titik tengah P0 -> P2
- Profil kecepatan ease-in / ease-out (smoothstep)
- Micro-jitter tegak lurus (|delta| <= 2 px) untuk mencegah teleportasi kursor dan deteksi bot
- Menjamin titik akhir tepat mendarat di target (x2, y2)
"""
from __future__ import annotations

import math
import random


class HumanMouseTrajectory:
    def __init__(self, rng_seed: int | None = 42) -> None:
        self.rng = random.Random(rng_seed)

    def generate_path(
        self,
        start_pos: tuple[int, int],
        target_pos: tuple[int, int],
        steps: int = 25,
        max_jitter: float = 2.0,
    ) -> list[tuple[int, int]]:
        """Membangkitkan daftar koordinat pergerakan kursor mouse yang mulus dan manusiawi."""
        x0, y0 = start_pos
        x2, y2 = target_pos

        if start_pos == target_pos:
            return [target_pos]

        dx = x2 - x0
        dy = y2 - y0
        dist = math.hypot(dx, dy)

        # 1. Tentukan titik kontrol P1 (menyimpang dari garis lurus)
        mid_x = (x0 + x2) / 2.0
        mid_y = (y0 + y2) / 2.0

        # Vektor normal ortogonal
        nx = -dy / (dist + 1e-9)
        ny = dx / (dist + 1e-9)

        # Deviasi kurva proporsional jarak (10% - 25% dari panjang)
        deviation = (self.rng.uniform(0.1, 0.25) * dist) * (1 if self.rng.random() > 0.5 else -1)
        p1_x = mid_x + nx * deviation
        p1_y = mid_y + ny * deviation

        path: list[tuple[int, int]] = []

        num_steps = max(5, steps)
        for i in range(num_steps):
            u = i / float(num_steps - 1)

            # Easing velocity (smoothstep: 3u^2 - 2u^3)
            t = 3.0 * (u ** 2) - 2.0 * (u ** 3)

            # Kurva Bezier Kuadratik: B(t) = (1-t)^2 P0 + 2(1-t)t P1 + t^2 P2
            bx = ((1.0 - t) ** 2) * x0 + 2.0 * (1.0 - t) * t * p1_x + (t ** 2) * x2
            by = ((1.0 - t) ** 2) * y0 + 2.0 * (1.0 - t) * t * p1_y + (t ** 2) * y2

            # Tambahkan micro-jitter ortogonal kecuali pada titik awal dan titik akhir
            if 0 < i < num_steps - 1:
                jitter = self.rng.uniform(-max_jitter, max_jitter)
                bx += nx * jitter
                by += ny * jitter

            path.append((int(round(bx)), int(round(by))))

        # Pastikan titik akhir tepat mendarat di target
        path[-1] = (x2, y2)
        return path
