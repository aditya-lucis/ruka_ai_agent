# -*- coding: utf-8 -*-
"""Voice HUD 4-State & 48-Column Waveform (FR-OS-03).

Menyediakan tampilan status suara desktop:
- 4 State: IDLE, LISTENING, THINKING, SPEAKING
- Subtitle maksimal 2 baris sinkron dengan frasa ucapan
- Waveform jujur 48 kolom yang dibangkitkan dari amplitudo viseme audio
"""
from __future__ import annotations

import collections
import math
from typing import Sequence, Tuple
from src.os_companion.models import HUDState


class VoiceHUD:
    TOTAL_BARS = 48

    def __init__(self) -> None:
        self.state: HUDState = HUDState.IDLE
        self.subtitle_lines: list[str] = []
        self._history_amplitudes: collections.deque[float] = collections.deque(
            [0.0] * self.TOTAL_BARS, maxlen=self.TOTAL_BARS
        )

    def set_state(self, state: HUDState) -> None:
        self.state = state
        if state == HUDState.IDLE:
            self.subtitle_lines.clear()

    def set_subtitle(self, text: str) -> list[str]:
        """Memecah teks menjadi maksimal 2 baris subtitle ringkas."""
        if not text:
            self.subtitle_lines = []
            return []

        words = text.strip().split()
        if len(words) <= 8:
            lines = [" ".join(words)]
        else:
            mid = len(words) // 2
            line1 = " ".join(words[:mid])
            line2 = " ".join(words[mid:min(len(words), mid * 2)])
            lines = [line1, line2]

        self.subtitle_lines = lines[:2]
        return self.subtitle_lines

    def push_viseme_amplitude(self, amplitude: float) -> Tuple[float, ...]:
        """Memasukkan amplitudo audio/viseme terkini [0.0, 1.0] dan menghasilkan 48 kolom."""
        amp = max(0.0, min(1.0, amplitude))
        self._history_amplitudes.append(amp)
        return tuple(self._history_amplitudes)

    def get_current_waveform(self) -> Tuple[float, ...]:
        """Mengembalikan 48 kolom tinggi waveform jujur."""
        if self.state == HUDState.IDLE:
            # Garis datar mendekati nol
            return tuple(0.02 for _ in range(self.TOTAL_BARS))
        elif self.state == HUDState.LISTENING:
            # Denyut lembut bernapas
            return tuple(self._history_amplitudes)
        elif self.state == HUDState.THINKING:
            # Efek gelombang berjalan (running wave)
            t = len(self._history_amplitudes)
            return tuple(0.15 + 0.10 * math.sin((i + t) * 0.4) for i in range(self.TOTAL_BARS))
        else:  # SPEAKING
            return tuple(self._history_amplitudes)
