# -*- coding: utf-8 -*-
"""Crimson Eyes Models & Dataclasses (FR-EY).

Kontrak dataclass beku untuk organ penglihatan lokal Ruka / Project Noctis.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Sequence


class VisionMode(str, Enum):
    NORMAL = "normal"      # 30 fps
    SLEEPY = "sleepy"      # 15 fps
    BLIND = "blind"        # 0 fps, zero-leak privacy shield


@dataclass(frozen=True)
class BoundingBox:
    x: float
    y: float
    width: float
    height: float
    confidence: float = 1.0


@dataclass(frozen=True)
class FaceIdentity:
    """Identitas wajah hasil ArcFace embedding 512-dimensi."""
    user_id: str
    similarity: float
    is_young_lord: bool
    confidence: float = 1.0
    embedding_512: tuple[float, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class GazeVector:
    """Arah pandang dan status kontak mata (FR-EY-07)."""
    yaw_deg: float
    pitch_deg: float
    is_eye_contact: bool
    contact_duration_ms: float = 0.0


@dataclass(frozen=True)
class VisionFrameVerdict:
    """Hasil inferensi satu frame visual."""
    mode: VisionMode
    motion_score: float
    face_detected: bool
    bbox: BoundingBox | None = None
    identity: FaceIdentity | None = None
    gaze: GazeVector | None = None
    privacy_shield_active: bool = False
    latency_ms: float = 0.0
