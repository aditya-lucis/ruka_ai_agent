# -*- coding: utf-8 -*-
"""Blood Hearing Models & Dataclasses (FR-EA).

Kontrak dataclass beku untuk modul telinga Ruka / Project Noctis.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class VADState(str, Enum):
    SILENCE = "silence"
    SPEECH = "speech"


class WakeState(str, Enum):
    ARMED = "armed"
    REFRACTORY = "refractory"


class SpeakerStatus(str, Enum):
    VERIFIED_YOUNG_LORD = "verified_young_lord"
    AMBIGUOUS = "ambiguous"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class AudioChunk:
    """Potongan audio mono float32 16 kHz."""
    samples: tuple[float, ...]
    sample_rate: int = 16000
    timestamp_ms: float = 0.0

    @property
    def duration_ms(self) -> float:
        if self.sample_rate <= 0:
            return 0.0
        return (len(self.samples) / self.sample_rate) * 1000.0


@dataclass(frozen=True)
class WakeVerdict:
    """Hasil deteksi wake word."""
    detected: bool
    keyword: str = ""
    confidence: float = 0.0
    latency_ms: float = 0.0
    timestamp_ms: float = 0.0


@dataclass(frozen=True)
class TranscriptionHypothesis:
    """Hipotesis ASR streaming (parsial atau final)."""
    text: str
    is_final: bool
    confidence: float = 0.0
    words: tuple[dict[str, Any], ...] = field(default_factory=tuple)
    latency_ms: float = 0.0


@dataclass(frozen=True)
class SpeakerVerdict:
    """Hasil verifikasi pembicara (Speaker ID)."""
    status: SpeakerStatus
    similarity: float
    speaker_id: str = "young_lord"
    duration_s: float = 0.0
    requires_second_window: bool = False
