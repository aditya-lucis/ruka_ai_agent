"""RUKA VI: Vision subsystem package."""

from .camera import CameraSource, Frame, SensorState, SensorStateMachine
from .detect import FaceDetection, SFaceEmbedder, YuNetDetector, cosine_to_similarity
from .recognize import COSINE_THRESHOLD_DOC, FaceIdentityMatcher, FaceMatch, FaceProfile

__all__ = [
    "CameraSource",
    "Frame",
    "SensorState",
    "SensorStateMachine",
    "FaceDetection",
    "YuNetDetector",
    "SFaceEmbedder",
    "cosine_to_similarity",
    "COSINE_THRESHOLD_DOC",
    "FaceProfile",
    "FaceMatch",
    "FaceIdentityMatcher",
]
