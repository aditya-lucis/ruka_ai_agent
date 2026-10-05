# -*- coding: utf-8 -*-
"""Living Presence Models & Data Structures (FR-PR).

Mendefinisikan kontrak tipe untuk loop kehadiran 60 Hz:
- MoodState 8-state (calm, happy, excited, focused, protective, anxious, vampire_noble, sleepy)
- Valence-Arousal koordinat [-1.0, 1.0]
- Pose telinga, ekor, napas, pandangan mata, dan frame kehadiran terpadu
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
import time
from typing import Tuple


class MoodState(str, Enum):
    CALM = "calm"
    HAPPY = "happy"
    EXCITED = "excited"
    FOCUSED = "focused"
    PROTECTIVE = "protective"
    ANXIOUS = "anxious"
    VAMPIRE_NOBLE = "vampire_noble"
    SLEEPY = "sleepy"


class DegradationLevel(str, Enum):
    FULL = "full"                      # 60 fps, semua fisika aktif
    NO_SECONDARY = "no_secondary"      # Matikan pegas telinga & ekor (p95 > 12ms)
    LOW_LOD = "low_lod"                # LOD rendah (p95 > 14ms)
    HALF_FPS = "half_fps"              # Turun ke 30 fps (p95 > 16.6ms)


@dataclass(frozen=True)
class ValenceArousal:
    valence: float = 0.0   # [-1.0, 1.0]: Negatif (kecewa/waspada) s.d. Positif (senang)
    arousal: float = 0.0   # [-1.0, 1.0]: Rendah (mengantuk) s.d. Tinggi (bersemangat)

    def clamp(self) -> ValenceArousal:
        return ValenceArousal(
            valence=max(-1.0, min(1.0, self.valence)),
            arousal=max(-1.0, min(1.0, self.arousal)),
        )


@dataclass(frozen=True)
class BreathingState:
    chest_scale: float = 1.0       # 1.0 s.d. 1.04
    phase_ratio: float = 0.0       # 0.0 s.d. 1.0 dalam satu siklus napas
    is_inhale: bool = True


@dataclass(frozen=True)
class EarPose:
    left_angle_deg: float = 0.0    # Sudut telinga kiri (-30 s.d. 45 derajat)
    right_angle_deg: float = 0.0   # Sudut telinga kanan
    flick_active: bool = False     # Efek kejang/kedut telinga sebelum rotasi kepala


@dataclass(frozen=True)
class TailPose:
    # 5 segmen ekor bertingkat dari pangkal ke ujung
    segments_deg: Tuple[float, float, float, float, float] = (0.0, 0.0, 0.0, 0.0, 0.0)
    whip_intensity: float = 1.0    # Pengali amplitudo ujung (maks 1.6x)


@dataclass(frozen=True)
class AttentionTarget:
    target_id: str
    x: float                       # Normalisasi [-1.0, 1.0]
    y: float                       # Normalisasi [-1.0, 1.0]
    salience: float = 1.0          # Nilai ketertarikan dasar
    priority: float = 1.0          # Prioritas (Young Lord = 2.0, cursor = 1.0)
    is_prey_lock: bool = False     # Kunci mangsa (pengali 1.6x)
    created_at: float = field(default_factory=time.time)


@dataclass(frozen=True)
class PresenceFrame:
    """Frame lengkap keluaran Living Presence Engine pada frekuensi 60 Hz."""
    frame_index: int
    timestamp: float
    mood: MoodState
    valence_arousal: ValenceArousal
    breathing: BreathingState
    blink_left: float              # 0.0 (terbuka) s.d. 1.0 (tertutup penuh)
    blink_right: float
    ear: EarPose
    tail: TailPose
    head_yaw_deg: float            # Rotasi kepala (-75 s.d. 75 derajat)
    head_pitch_deg: float          # Sudut dongak/tunduk (-30 s.d. 30 derajat)
    eye_look_x: float              # Arah pandang bola mata [-1.0, 1.0]
    eye_look_y: float
    degradation: DegradationLevel = DegradationLevel.FULL
    is_sleep_mode: bool = False
