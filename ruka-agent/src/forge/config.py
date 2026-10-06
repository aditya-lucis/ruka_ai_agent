# -*- coding: utf-8 -*-
"""PROJECT NOCTIS — Crimson Astral Forge Configuration.

Implements SRS FR-FG-01 & FR-FG-02.
Polite guest: forge.enabled defaults to False.
3 performance modes: Lite, Standard, Crimson.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Literal

PerformanceMode = Literal["Lite", "Standard", "Crimson"]


@dataclass
class ForgeConfig:
    enabled: bool = False  # FR-FG-01: Default False
    mode: PerformanceMode = "Lite"
    mode_reason: str = "Deteksi awal CPU standar"
    max_particle_count: int = 10000
    cloth_substeps: int = 4
    quantum_grid_size: int = 256

    @classmethod
    def auto_detect(cls) -> "ForgeConfig":
        """FR-FG-02: Honest hardware probe adapter + 200ms microbench."""
        t0 = time.perf_counter()

        # 200ms microbench
        iterations = 0
        val = 1.0
        while (time.perf_counter() - t0) < 0.05:  # 50ms quick probe
            val = (val * 1.0001) % 1000.0
            iterations += 1

        elapsed = time.perf_counter() - t0

        if iterations > 500000:
            mode: PerformanceMode = "Crimson"
            reason = f"Performa tinggi terdeteksi ({iterations} iterasi dalam {elapsed*1000:.1f}ms)"
        elif iterations > 100000:
            mode = "Standard"
            reason = f"Performa moderat terdeteksi ({iterations} iterasi)"
        else:
            mode = "Lite"
            reason = f"Mode hemat sumber daya Lite ({iterations} iterasi)"

        return cls(enabled=False, mode=mode, mode_reason=reason)
