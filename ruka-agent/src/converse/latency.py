# -*- coding: utf-8 -*-
"""Latency Meter & Budget Tracker (FR-MC-08).

Mengukur latensi percakapan total suara-ke-suara:
- Jatah anggaran: ASR final 250 ms, Otak TTFT 300 ms, TTS TTFB 100 ms, Jitter/Jaringan 100 ms
- Target total percakapan p95 di bawah 800 milidetik
"""
from __future__ import annotations

import numpy as np


class LatencyMeter:
    def __init__(self, target_p95_ms: float = 800.0) -> None:
        self.target_p95_ms = target_p95_ms
        self._latencies: list[float] = []

    def record_turn_latency(
        self,
        asr_ms: float = 200.0,
        brain_ttft_ms: float = 250.0,
        tts_ttfb_ms: float = 120.0,
        network_buffer_ms: float = 30.0,
    ) -> float:
        """Mencatat komponen latensi satu giliran dan mengembalikan totalnya."""
        total_ms = asr_ms + brain_ttft_ms + tts_ttfb_ms + network_buffer_ms
        self._latencies.append(total_ms)
        return total_ms

    @property
    def p50(self) -> float:
        if not self._latencies:
            return 0.0
        return float(np.percentile(self._latencies, 50))

    @property
    def p95(self) -> float:
        if not self._latencies:
            return 0.0
        return float(np.percentile(self._latencies, 95))

    @property
    def meets_sla(self) -> bool:
        """Memeriksa apakah p95 memenuhi target SLA <= 800 ms."""
        return self.p95 <= self.target_p95_ms
