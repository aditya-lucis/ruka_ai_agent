# -*- coding: utf-8 -*-
"""Speaker ID & Verification (FR-EA-08, FR-EA-09, FR-EA-10).

Identifikasi pembicara menggunakan embedding dan kesamaan kosinus:
- skor >= 0.70: VERIFIED_YOUNG_LORD (hak penuh)
- skor 0.50 s/d 0.70: AMBIGUOUS (meminta jendela audio kedua)
- skor < 0.50: UNKNOWN (orang asing / tidak dikenal)
Gerbang enrollment: durasi >= 25s, SNR >= 15 dB, tanpa clipping.
"""
from __future__ import annotations

import math
from typing import Sequence
from src.senses.ear.models import SpeakerStatus, SpeakerVerdict


class SpeakerIdentifier:
    def __init__(
        self,
        high_threshold: float = 0.70,
        low_threshold: float = 0.50,
        target_speaker_id: str = "young_lord",
    ) -> None:
        self.high_threshold = high_threshold
        self.low_threshold = low_threshold
        self.target_speaker_id = target_speaker_id
        self._enrolled_embedding: list[float] | None = None

    @property
    def is_enrolled(self) -> bool:
        return self._enrolled_embedding is not None

    def enroll(
        self,
        embedding: Sequence[float],
        duration_s: float = 30.0,
        snr_db: float = 20.0,
        has_clipping: bool = False,
    ) -> bool:
        """Mendaftarkan profil suara Young Lord dengan gerbang kualitas."""
        if duration_s < 25.0:
            raise ValueError(f"Durasi enrollment {duration_s:.1f}s tidak memenuhi syarat minimal 25.0s")
        if snr_db < 15.0:
            raise ValueError(f"SNR {snr_db:.1f} dB di bawah standar kebersihan minimal 15.0 dB")
        if has_clipping:
            raise ValueError("Audio enrollment mengandung clipping sinyal")

        # Normalisasi L2 embedding
        norm = math.sqrt(sum(x * x for x in embedding))
        if norm <= 1e-9:
            raise ValueError("Vektor embedding memiliki magnitude nol")
        self._enrolled_embedding = [float(x / norm) for x in embedding]
        return True

    def verify(
        self,
        test_embedding: Sequence[float],
        duration_s: float = 1.0,
    ) -> SpeakerVerdict:
        """Memverifikasi kemiripan embedding suara uji dengan profil tersimpan."""
        if self._enrolled_embedding is None:
            # Belum ada enrollment, fallback ke UNKNOWN
            return SpeakerVerdict(
                status=SpeakerStatus.UNKNOWN,
                similarity=0.0,
                speaker_id="unknown",
                duration_s=duration_s,
                requires_second_window=False,
            )

        norm = math.sqrt(sum(x * x for x in test_embedding))
        if norm <= 1e-9:
            return SpeakerVerdict(
                status=SpeakerStatus.UNKNOWN,
                similarity=0.0,
                speaker_id="unknown",
                duration_s=duration_s,
                requires_second_window=False,
            )

        normed_test = [x / norm for x in test_embedding]

        # Cosine similarity dot product
        similarity = sum(a * b for a, b in zip(self._enrolled_embedding, normed_test))

        if similarity >= self.high_threshold:
            status = SpeakerStatus.VERIFIED_YOUNG_LORD
            speaker_id = self.target_speaker_id
            req_second = False
        elif similarity >= self.low_threshold:
            status = SpeakerStatus.AMBIGUOUS
            speaker_id = "ambiguous"
            req_second = True
        else:
            status = SpeakerStatus.UNKNOWN
            speaker_id = "unknown"
            req_second = False

        return SpeakerVerdict(
            status=status,
            similarity=float(similarity),
            speaker_id=speaker_id,
            duration_s=duration_s,
            requires_second_window=req_second,
        )
