# -*- coding: utf-8 -*-
"""Eternal Voice Models & Dataclasses (FR-VO).

Kontrak dataclass beku untuk organ suara Ruka / Project Noctis.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Sequence


class MarquisMood(str, Enum):
    SASSY = "sassy"
    LOYAL = "loyal"
    ANALYTICAL = "analytical"
    DRAMATIC = "dramatic"
    WHISPERED = "whispered"
    MOCKING = "mocking"
    PROTECTIVE = "protective"
    NEUTRAL = "neutral"


@dataclass(frozen=True)
class ProsodySettings:
    """Konfigurasi prosodi audio yang telah dijepit (clamped)."""
    pitch_semitones: float  # Dijepit [-2.5, 2.5]
    rate_multiplier: float  # [0.75, 1.35]
    energy_multiplier: float  # [0.5, 1.5]
    valence: float = 0.0
    arousal: float = 0.0


@dataclass(frozen=True)
class VisemeEvent:
    """Event viseme 25 fps untuk sinkronisasi bibir avatar (FR-VO-12)."""
    viseme_id: str
    timestamp_ms: float
    weight: float = 1.0


@dataclass(frozen=True)
class TTSChunk:
    """Potongan audio stream sintesis TTS."""
    audio_data: bytes
    sample_rate: int = 24000
    duration_ms: float = 0.0
    is_first_chunk: bool = False
    is_final: bool = False
    ttfb_ms: float = 0.0
    visemes: tuple[VisemeEvent, ...] = field(default_factory=tuple)
