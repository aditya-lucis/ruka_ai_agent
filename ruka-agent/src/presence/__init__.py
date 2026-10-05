# -*- coding: utf-8 -*-
"""Living Presence Package (PROJECT NOCTIS FR-PR)."""

from src.presence.attention import AttentionEngine
from src.presence.blinking import BlinkingEngine
from src.presence.breathing import BreathingEngine
from src.presence.engine import LivingPresenceEngine
from src.presence.models import (
    AttentionTarget,
    BreathingState,
    DegradationLevel,
    EarPose,
    MoodState,
    PresenceFrame,
    TailPose,
    ValenceArousal,
)
from src.presence.mood_fsm import MoodStateMachine
from src.presence.observability import (
    PresenceRingBuffer,
    compute_frame_phash_64,
    hamming_distance,
    is_visual_regression,
)
from src.presence.spring_physics import EarPhysicsEngine, TailPhysicsEngine

__all__ = [
    "AttentionEngine",
    "BlinkingEngine",
    "BreathingEngine",
    "LivingPresenceEngine",
    "AttentionTarget",
    "BreathingState",
    "DegradationLevel",
    "EarPose",
    "MoodState",
    "PresenceFrame",
    "TailPose",
    "ValenceArousal",
    "MoodStateMachine",
    "PresenceRingBuffer",
    "compute_frame_phash_64",
    "hamming_distance",
    "is_visual_regression",
    "EarPhysicsEngine",
    "TailPhysicsEngine",
]
