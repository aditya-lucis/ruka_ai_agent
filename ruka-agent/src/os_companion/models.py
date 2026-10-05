# -*- coding: utf-8 -*-
"""AI Companion Operating System Models & Contracts (FR-OS).

Mendefinisikan kontrak tipe untuk sistem operasi pendamping desktop RUKA:
- 8 Titik kompas docking (N, NE, E, SE, S, SW, W, NW)
- 4 State Voice HUD (IDLE, LISTENING, THINKING, SPEAKING)
- 7 Fase Lunar Clock
- Notifikasi dan Dosing
- Resource Governor Quota
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
import time
from typing import Any, Callable, Optional


class CompassPoint(str, Enum):
    N = "N"
    NE = "NE"
    E = "E"
    SE = "SE"
    S = "S"
    SW = "SW"
    W = "W"
    NW = "NW"


class HUDState(str, Enum):
    IDLE = "idle"
    LISTENING = "listening"
    THINKING = "thinking"
    SPEAKING = "speaking"


class LunarPhase(str, Enum):
    FAJR = "fajr"                # 04:30 - 06:00: Tenang, bangun bertahap
    MORNING = "morning"          # 06:00 - 11:30: Bersemangat, produktif
    NOON = "noon"                # 11:30 - 14:00: Tenang, jeda siang
    AFTERNOON = "afternoon"      # 14:00 - 18:00: Fokus tinggi
    DUSK = "dusk"                # 18:00 - 20:00: Rangkuman hari (digest)
    NIGHT = "night"              # 20:00 - 22:00: Santai, vampir bangsawan
    MIDNIGHT = "midnight"        # 22:00 - 04:30: Jam malam (curfew), bisikan saja


class NotificationPriority(str, Enum):
    WHISPER = "whisper"          # Digabung ke digest 18:00
    NORMAL = "normal"            # Maks 1 per 10 menit
    URGENT = "urgent"            # Tembus jam malam


@dataclass(frozen=True)
class NotificationItem:
    notification_id: str
    title: str
    body: str
    priority: NotificationPriority = NotificationPriority.NORMAL
    created_at: float = field(default_factory=time.time)


@dataclass(frozen=True)
class GhostWindowConfig:
    transparent: bool = True
    frame: bool = False
    always_on_top: bool = True
    skip_taskbar: bool = True
    focusable: bool = False
    pointer_hysteresis_px: int = 2
    debounce_ms: float = 8.0


@dataclass(frozen=True)
class DockPosition:
    compass: CompassPoint
    x: int
    y: int
    is_snapped: bool = True


@dataclass
class OrganResourceQuota:
    organ_name: str
    max_ram_mb: float
    current_ram_mb: float = 0.0
    violation_count: int = 0
