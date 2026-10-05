# -*- coding: utf-8 -*-
"""AI Companion Operating System Package (PROJECT NOCTIS FR-OS)."""

from src.os_companion.command_palette import CommandPaletteRegistry, PaletteAction
from src.os_companion.docking import MagneticDockManager
from src.os_companion.dosing import NotificationDoser
from src.os_companion.ghost_window import GhostWindowManager, PointerGate
from src.os_companion.governor import ResourceGovernor
from src.os_companion.lunar_clock import LunarClock
from src.os_companion.models import (
    CompassPoint,
    DockPosition,
    GhostWindowConfig,
    HUDState,
    LunarPhase,
    NotificationItem,
    NotificationPriority,
    OrganResourceQuota,
)
from src.os_companion.sentinel import SentinelModeManager
from src.os_companion.voice_hud import VoiceHUD

__all__ = [
    "CommandPaletteRegistry",
    "PaletteAction",
    "MagneticDockManager",
    "NotificationDoser",
    "GhostWindowManager",
    "PointerGate",
    "ResourceGovernor",
    "LunarClock",
    "SentinelModeManager",
    "VoiceHUD",
    "CompassPoint",
    "DockPosition",
    "GhostWindowConfig",
    "HUDState",
    "LunarPhase",
    "NotificationItem",
    "NotificationPriority",
    "OrganResourceQuota",
]
