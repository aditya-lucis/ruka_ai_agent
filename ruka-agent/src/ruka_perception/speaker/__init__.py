"""Speaker verification and identification module for Ruka Perception.

Exposes SpeakerVerifier, cosine_similarity, far_frr_sweep, eer, roc_points, and identify.
"""

from .verification import (
    SpeakerVerifier,
    cosine_similarity,
    eer,
    far_frr_sweep,
    identify,
    roc_points,
)

__all__ = [
    "SpeakerVerifier",
    "cosine_similarity",
    "eer",
    "far_frr_sweep",
    "identify",
    "roc_points",
]
