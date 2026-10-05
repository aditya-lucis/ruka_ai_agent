# -*- coding: utf-8 -*-
"""Poisson Process Eye Blinking Engine (FR-PR-03).

Mengatur dinamika kedipan mata biologis menggunakan proses Poisson:
- Laju dasar: 0.28 kedipan per detik (rata-rata selang ~3.5 detik)
- Durasi tutup-buka: 300 ms (tutup 100 ms, buka 200 ms)
- Peluang kedip ganda (double-blink): 10% dengan jeda 120 ms
- Variasi laju per suasana hati (0.11 hingga 0.70 kedipan/detik)
"""
from __future__ import annotations

import math
import random
from src.presence.models import MoodState

MOOD_BLINK_RATES: dict[MoodState, float] = {
    MoodState.SLEEPY: 0.11,
    MoodState.FOCUSED: 0.15,
    MoodState.CALM: 0.28,
    MoodState.VAMPIRE_NOBLE: 0.25,
    MoodState.PROTECTIVE: 0.20,
    MoodState.HAPPY: 0.35,
    MoodState.EXCITED: 0.50,
    MoodState.ANXIOUS: 0.70,
}


class BlinkingEngine:
    def __init__(self, rng_seed: int | None = None) -> None:
        self.rng = random.Random(rng_seed)
        self.next_blink_time: float = 0.0
        self.current_blink_start: float = -1.0
        self.is_double_blink: bool = False
        self.second_blink_start: float = -1.0
        self.blink_duration: float = 0.30  # 300 ms

    def _sample_interval(self, rate: float) -> float:
        """Mengambil interval waktu berikutnya dari distribusi eksponensial (Proses Poisson)."""
        rate = max(0.05, rate)
        u = self.rng.random()
        return -math.log(1.0 - max(1e-6, min(1.0 - 1e-6, u))) / rate

    def update(self, current_time: float, mood: MoodState) -> tuple[float, float]:
        """Mengembalikan nilai kedip mata kiri dan kanan (0.0 = terbuka, 1.0 = tertutup)."""
        rate = MOOD_BLINK_RATES.get(mood, 0.28)

        # Inisialisasi waktu kedip pertama jika belum diset
        if self.next_blink_time <= 0.0:
            self.next_blink_time = current_time + self._sample_interval(rate)

        # Cek apakah waktu untuk memulai kedipan tiba
        if current_time >= self.next_blink_time and self.current_blink_start < 0:
            self.current_blink_start = current_time
            # 10% peluang kedip ganda (double-blink)
            if self.rng.random() < 0.10:
                self.is_double_blink = True
                self.second_blink_start = current_time + self.blink_duration + 0.12  # jeda 120 ms
            else:
                self.is_double_blink = False
                self.second_blink_start = -1.0

        blink_value = 0.0

        # Evaluasi kedipan pertama
        if self.current_blink_start > 0:
            dt = current_time - self.current_blink_start
            if 0 <= dt <= self.blink_duration:
                # 100 ms pertama menutup, 200 ms berikutnya membuka
                if dt < 0.10:
                    blink_value = dt / 0.10
                else:
                    blink_value = 1.0 - ((dt - 0.10) / 0.20)
            elif dt > self.blink_duration:
                if not self.is_double_blink:
                    self.current_blink_start = -1.0
                    self.next_blink_time = current_time + self._sample_interval(rate)

        # Evaluasi kedipan kedua jika double-blink aktif
        if self.is_double_blink and self.second_blink_start > 0:
            dt2 = current_time - self.second_blink_start
            if 0 <= dt2 <= self.blink_duration:
                if dt2 < 0.10:
                    blink_value = dt2 / 0.10
                else:
                    blink_value = 1.0 - ((dt2 - 0.10) / 0.20)
            elif dt2 > self.blink_duration:
                self.is_double_blink = False
                self.current_blink_start = -1.0
                self.second_blink_start = -1.0
                self.next_blink_time = current_time + self._sample_interval(rate)

        clamped = max(0.0, min(1.0, blink_value))
        return clamped, clamped
