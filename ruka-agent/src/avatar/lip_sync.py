# -*- coding: utf-8 -*-
"""Phoneme to Viseme Lip-Sync Engine (FR-AV-03).

Sinkronisasi bibir fonem ke viseme:
- Rata-rata offset di bawah 80 ms (dan tidak ada kata di atas 150 ms)
- Durasi minimal viseme vokal adalah 70 ms (0.07 detik)
- Pemetaan fonem alfabetis ke 8 kode viseme VRM standar (sil, A, E, I, O, U, M, S)
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import List
from src.avatar.models import VisemePose

PHONEME_TO_VISEME_MAP: dict[str, str] = {
    "a": "A", "ah": "A", "aa": "A",
    "e": "E", "eh": "E", "ey": "E",
    "i": "I", "ih": "I", "iy": "I",
    "o": "O", "ow": "O", "ao": "O",
    "u": "U", "uw": "U", "uh": "U",
    "m": "M", "b": "M", "p": "M",
    "s": "S", "z": "S", "sh": "S", "ch": "S", "j": "S",
    " ": "sil", ".": "sil", ",": "sil",
}


@dataclass(frozen=True)
class TimedViseme:
    viseme_id: str
    start_time_s: float
    duration_s: float
    weight: float = 1.0


class LipSyncEngine:
    MIN_VOWEL_DURATION_S = 0.070  # 70 ms minimal untuk vokal (FR-AV-03)

    def generate_timed_visemes(
        self,
        text: str,
        speech_rate_cps: float = 12.0,  # ~12 karakter per detik
        audio_start_time: float = 0.0,
    ) -> List[TimedViseme]:
        """Menghasilkan rangkaian viseme berwaktu dengan aturan batas minimal vokal 70ms."""
        visemes: list[TimedViseme] = []
        char_duration = 1.0 / max(4.0, speech_rate_cps)
        current_time = audio_start_time

        for char in text.lower():
            code = PHONEME_TO_VISEME_MAP.get(char, "sil")
            dur = char_duration
            if code in ("A", "E", "I", "O", "U"):
                dur = max(dur, self.MIN_VOWEL_DURATION_S)

            visemes.append(
                TimedViseme(
                    viseme_id=code,
                    start_time_s=current_time,
                    duration_s=dur,
                    weight=1.0 if code != "sil" else 0.0,
                )
            )
            current_time += dur

        return visemes

    def get_viseme_at_time(self, timeline: List[TimedViseme], current_time: float) -> VisemePose:
        """Mengambil pose viseme yang aktif pada current_time."""
        for tv in timeline:
            if tv.start_time_s <= current_time <= (tv.start_time_s + tv.duration_s):
                return VisemePose(viseme_id=tv.viseme_id, weight=tv.weight, timestamp=current_time)
        return VisemePose(viseme_id="sil", weight=0.0, timestamp=current_time)
