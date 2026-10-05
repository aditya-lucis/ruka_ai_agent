# -*- coding: utf-8 -*-
"""Prosody Controller for 8 Marquis Moods (FR-VO-04).

Memetakan suasana hati Marquis ke parameter prosodi:
- pitch semitone dijepit maksimal [-2.5, 2.5]
- rate multiplier dijepit [0.75, 1.35]
- energy multiplier dijepit [0.50, 1.50]
"""
from __future__ import annotations

from src.senses.voice.models import MarquisMood, ProsodySettings

MOOD_PROSODY_MAP: dict[MarquisMood, ProsodySettings] = {
    MarquisMood.SASSY: ProsodySettings(
        pitch_semitones=1.5,
        rate_multiplier=1.15,
        energy_multiplier=1.20,
        valence=0.3,
        arousal=0.6,
    ),
    MarquisMood.LOYAL: ProsodySettings(
        pitch_semitones=-0.5,
        rate_multiplier=1.00,
        energy_multiplier=1.00,
        valence=0.7,
        arousal=0.1,
    ),
    MarquisMood.ANALYTICAL: ProsodySettings(
        pitch_semitones=0.0,
        rate_multiplier=0.95,
        energy_multiplier=0.95,
        valence=0.1,
        arousal=-0.1,
    ),
    MarquisMood.DRAMATIC: ProsodySettings(
        pitch_semitones=2.0,
        rate_multiplier=1.10,
        energy_multiplier=1.30,
        valence=-0.2,
        arousal=0.8,
    ),
    MarquisMood.WHISPERED: ProsodySettings(
        pitch_semitones=-1.0,
        rate_multiplier=0.85,
        energy_multiplier=0.60,
        valence=0.2,
        arousal=-0.6,
    ),
    MarquisMood.MOCKING: ProsodySettings(
        pitch_semitones=1.0,
        rate_multiplier=1.10,
        energy_multiplier=1.10,
        valence=0.4,
        arousal=0.5,
    ),
    MarquisMood.PROTECTIVE: ProsodySettings(
        pitch_semitones=-1.5,
        rate_multiplier=1.05,
        energy_multiplier=1.25,
        valence=0.5,
        arousal=0.4,
    ),
    MarquisMood.NEUTRAL: ProsodySettings(
        pitch_semitones=0.0,
        rate_multiplier=1.00,
        energy_multiplier=1.00,
        valence=0.0,
        arousal=0.0,
    ),
}


class ProsodyController:
    """Pengontrol prosodi yang menjamin jepitan batas semitone dan laju suara."""

    MAX_PITCH_SEMITONES: float = 2.5
    MIN_PITCH_SEMITONES: float = -2.5

    def get_settings(
        self,
        mood: MarquisMood | str,
        custom_pitch_offset: float = 0.0,
        custom_rate_multiplier: float = 1.0,
    ) -> ProsodySettings:
        """Mengambil konfigurasi prosodi dengan jepitan mutlak."""
        if isinstance(mood, str):
            try:
                m_enum = MarquisMood(mood.lower())
            except ValueError:
                m_enum = MarquisMood.NEUTRAL
        else:
            m_enum = mood

        base = MOOD_PROSODY_MAP.get(m_enum, MOOD_PROSODY_MAP[MarquisMood.NEUTRAL])

        # Hitung dan jepit pitch
        raw_pitch = base.pitch_semitones + custom_pitch_offset
        clamped_pitch = max(self.MIN_PITCH_SEMITONES, min(self.MAX_PITCH_SEMITONES, raw_pitch))

        # Hitung dan jepit rate
        raw_rate = base.rate_multiplier * custom_rate_multiplier
        clamped_rate = max(0.75, min(1.35, raw_rate))

        return ProsodySettings(
            pitch_semitones=float(clamped_pitch),
            rate_multiplier=float(clamped_rate),
            energy_multiplier=base.energy_multiplier,
            valence=base.valence,
            arousal=base.arousal,
        )
