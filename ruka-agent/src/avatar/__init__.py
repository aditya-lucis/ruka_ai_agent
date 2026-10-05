# -*- coding: utf-8 -*-
"""Living Avatar Package (PROJECT NOCTIS FR-AV)."""

from src.avatar.arbitrator import ChannelArbitrator
from src.avatar.engine import LivingAvatarEngine
from src.avatar.expressions import ExpressionLayerManager
from src.avatar.eye_animator import AvatarEyeAnimator
from src.avatar.idle_tree import IdleAnimationTree
from src.avatar.lip_sync import LipSyncEngine, TimedViseme
from src.avatar.models import (
    ALL_SUPPORTED_BLENDSHAPES,
    CUSTOM_RUKA_BLENDSHAPES,
    STANDARD_ARKIT_BLENDSHAPES,
    AvatarFrame,
    BonePose,
    IdleBranch,
    PupilPose,
    VisemePose,
)
from src.avatar.verlet_physics import CapsuleCollider, VerletParticle, VerletPhysicsEngine

__all__ = [
    "ChannelArbitrator",
    "LivingAvatarEngine",
    "ExpressionLayerManager",
    "AvatarEyeAnimator",
    "IdleAnimationTree",
    "LipSyncEngine",
    "TimedViseme",
    "ALL_SUPPORTED_BLENDSHAPES",
    "CUSTOM_RUKA_BLENDSHAPES",
    "STANDARD_ARKIT_BLENDSHAPES",
    "AvatarFrame",
    "BonePose",
    "IdleBranch",
    "PupilPose",
    "VisemePose",
    "CapsuleCollider",
    "VerletParticle",
    "VerletPhysicsEngine",
]
