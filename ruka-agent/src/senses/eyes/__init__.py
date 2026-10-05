# -*- coding: utf-8 -*-
"""Crimson Eyes Organ Package (FR-EY)."""
from src.senses.eyes.detector import DualTrackDetector
from src.senses.eyes.gaze import GazeEstimator
from src.senses.eyes.models import (
    BoundingBox,
    FaceIdentity,
    GazeVector,
    VisionFrameVerdict,
    VisionMode,
)
from src.senses.eyes.pipeline import CrimsonEyes
from src.senses.eyes.privacy import PrivacyGuard
from src.senses.eyes.recognizer import FaceRecognizer

__all__ = [
    "BoundingBox",
    "CrimsonEyes",
    "DualTrackDetector",
    "FaceIdentity",
    "FaceRecognizer",
    "GazeEstimator",
    "GazeVector",
    "PrivacyGuard",
    "VisionFrameVerdict",
    "VisionMode",
]
