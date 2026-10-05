# -*- coding: utf-8 -*-
"""Barge-In / Interruption Detector (FR-EA-11).

Mendeteksi interupsi ucapan pengguna saat Ruka sedang berbicara:
- Ambang durasi ucapan minimal 600 ms.
- Ambang energi RMS minimal 0.02 pada residu echo canceller.
- Memicu perintah hening (voice.stop_speaking) di bawah 300 milidetik.
"""
from __future__ import annotations

import math
import time
from typing import Sequence


class InterruptionDetector:
    def __init__(
        self,
        min_speech_duration_ms: float = 600.0,
        min_rms_energy: float = 0.02,
        max_action_latency_ms: float = 300.0,
    ) -> None:
        self.min_speech_duration_ms = min_speech_duration_ms
        self.min_rms_energy = min_rms_energy
        self.max_action_latency_ms = max_action_latency_ms

        self._active_speech_ms: float = 0.0
        self._is_ruka_speaking: bool = False

    def set_ruka_speaking(self, speaking: bool) -> None:
        self._is_ruka_speaking = speaking
        if not speaking:
            self._active_speech_ms = 0.0

    def process_chunk(
        self,
        samples: Sequence[float],
        duration_ms: float = 32.0,
    ) -> tuple[bool, float]:
        """Memproses chunk audio saat Ruka berbicara.

        Returns:
            tuple (is_interrupted, latency_ms)
        """
        start_t = time.perf_counter()

        if not self._is_ruka_speaking or not samples:
            self._active_speech_ms = 0.0
            return False, 0.0

        n = len(samples)
        sum_sq = sum(s * s for s in samples)
        rms = math.sqrt(sum_sq / n)

        if rms >= self.min_rms_energy:
            self._active_speech_ms += duration_ms
        else:
            self._active_speech_ms = max(0.0, self._active_speech_ms - duration_ms * 0.5)

        interrupted = self._active_speech_ms >= self.min_speech_duration_ms
        latency_ms = (time.perf_counter() - start_t) * 1000.0

        if interrupted:
            # Reset counter setelah menembakkan interupsi
            self._active_speech_ms = 0.0

        return interrupted, latency_ms
