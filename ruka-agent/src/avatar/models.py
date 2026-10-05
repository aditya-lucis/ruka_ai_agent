# -*- coding: utf-8 -*-
"""Living Avatar Engine Models & VRM Contract (FR-AV-01, FR-AV-02).

Kontrak VRM 1.0 dan pemisahan kanal independen:
- 4 Kanal Single-Writer: Bones (Presence), Expressions (Mood), Visemes (Voice), Pupils (Eyes)
- 23 ARKit Blendshapes + 4 Kustom (fangs, blush, flat_ears, ear_twitch)
- 6 Cabang Animasi Idle
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
import time
from typing import Dict, Tuple

# 23 ARKit blendshapes standar + 4 kustom Ruka Noctis
STANDARD_ARKIT_BLENDSHAPES = (
    "eyeBlinkLeft", "eyeBlinkRight", "eyeLookUpLeft", "eyeLookUpRight",
    "eyeLookDownLeft", "eyeLookDownRight", "eyeLookInLeft", "eyeLookInRight",
    "eyeLookOutLeft", "eyeLookOutRight", "eyeWideLeft", "eyeWideRight",
    "jawOpen", "mouthFunnel", "mouthPucker", "mouthLeft", "mouthRight",
    "mouthSmileLeft", "mouthSmileRight", "mouthFrownLeft", "mouthFrownRight",
    "browDownLeft", "browDownRight",
)

CUSTOM_RUKA_BLENDSHAPES = (
    "fangs",        # Taring vampir bangsawan
    "blush",        # Rona pipi merah
    "flat_ears",    # Telinga rebah (marah/waspada)
    "ear_twitch",   # Kedutan telinga refleks
)

ALL_SUPPORTED_BLENDSHAPES = set(STANDARD_ARKIT_BLENDSHAPES + CUSTOM_RUKA_BLENDSHAPES)


class IdleBranch(str, Enum):
    NOBLE_OBSERVE = "noble_observe"      # Vampir bangsawan mengamati tenang
    TAIL_PLAY = "tail_play"              # Mengibaskan ekor anggun
    EAR_PREEN = "ear_preen"              # Menyesuaikan posisi telinga
    CURIOUS_TILT = "curious_tilt"        # Memiringkan kepala penasaran
    DEEP_REST = "deep_rest"              # Istirahat setengah tidur
    VIGILANT_GUARD = "vigilant_guard"    # Menjaga waspada


@dataclass(frozen=True)
class BonePose:
    head_yaw: float = 0.0
    head_pitch: float = 0.0
    head_roll: float = 0.0
    chest_scale: float = 1.0
    ear_left_deg: float = 0.0
    ear_right_deg: float = 0.0
    tail_segments: Tuple[float, float, float, float, float] = (0.0, 0.0, 0.0, 0.0, 0.0)


@dataclass(frozen=True)
class PupilPose:
    dilation: float = 0.5          # 0.0 (mengecil tajam) s.d. 1.0 (membesar penuh)
    saccade_offset_x: float = 0.0  # Derajat micro-saccade
    saccade_offset_y: float = 0.0


@dataclass(frozen=True)
class VisemePose:
    viseme_id: str = "sil"         # "sil", "A", "E", "I", "O", "U", "M", "S"
    weight: float = 0.0            # 0.0 s.d. 1.0
    timestamp: float = field(default_factory=time.time)


@dataclass
class AvatarFrame:
    """Frame gabungan 60 fps hasil arbitrase 4 kanal independen."""
    frame_index: int
    timestamp: float
    bones: BonePose
    blendshapes: Dict[str, float]
    viseme: VisemePose
    pupil: PupilPose
    lod_level: int = 0             # 0=Full, 1=No secondary, 2=Minimal
