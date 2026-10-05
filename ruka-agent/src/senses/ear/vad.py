# -*- coding: utf-8 -*-
"""VAD Gatekeeper (FR-EA-02).

Mesin status VAD dengan histeresis:
- Masuk SPEECH: p >= 0.50 selama 2 jendela berturut-turut.
- Keluar ke SILENCE: p < 0.35 selama 25 jendela berturut-turut (hangover ~800 ms).
Jendela baku: 512 sampel @ 16 kHz (32 ms).
"""
from __future__ import annotations

import math
from typing import Sequence
from src.senses.ear.models import VADState


class VADGatekeeper:
    def __init__(
        self,
        sample_rate: int = 16000,
        window_size: int = 512,
        speech_prob_threshold: float = 0.50,
        silence_prob_threshold: float = 0.35,
        speech_consecutive_windows: int = 2,
        silence_consecutive_windows: int = 25,
    ) -> None:
        self.sample_rate = sample_rate
        self.window_size = window_size
        self.speech_prob_threshold = speech_prob_threshold
        self.silence_prob_threshold = silence_prob_threshold
        self.speech_consecutive_windows = speech_consecutive_windows
        self.silence_consecutive_windows = silence_consecutive_windows

        self._state: VADState = VADState.SILENCE
        self._consecutive_speech_count: int = 0
        self._consecutive_silence_count: int = 0

    @property
    def state(self) -> VADState:
        return self._state

    def reset(self) -> None:
        self._state = VADState.SILENCE
        self._consecutive_speech_count = 0
        self._consecutive_silence_count = 0

    def calculate_energy_prob(self, samples: Sequence[float]) -> float:
        """Estimasi probabilitas ucapan berbasis RMS dan ZCR jika model neural tidak tersedia."""
        if not samples:
            return 0.0
        n = len(samples)
        sum_sq = sum(s * s for s in samples)
        rms = math.sqrt(sum_sq / n)

        # Baseline noise floor estimate ~0.005, typical speech RMS > 0.02
        if rms < 0.005:
            return 0.0
        elif rms > 0.04:
            return 0.95
        else:
            # Linear scaling antara 0.005 dan 0.04
            return (rms - 0.005) / (0.04 - 0.005)

    def process_window(self, samples: Sequence[float], external_prob: float | None = None) -> VADState:
        """Memproses satu jendela audio 512 sampel (32 ms)."""
        prob = external_prob if external_prob is not None else self.calculate_energy_prob(samples)

        if prob >= self.speech_prob_threshold:
            self._consecutive_speech_count += 1
            self._consecutive_silence_count = 0
            if self._state == VADState.SILENCE:
                if self._consecutive_speech_count >= self.speech_consecutive_windows:
                    self._state = VADState.SPEECH
        elif prob < self.silence_prob_threshold:
            self._consecutive_silence_count += 1
            self._consecutive_speech_count = 0
            if self._state == VADState.SPEECH:
                if self._consecutive_silence_count >= self.silence_consecutive_windows:
                    self._state = VADState.SILENCE
        else:
            # Di daerah histeresis (0.35 <= prob < 0.50), pertahankan counter parsial
            pass

        return self._state
