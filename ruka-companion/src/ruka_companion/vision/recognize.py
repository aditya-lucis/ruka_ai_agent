"""RUKA VI: Vision Face Recognition — Profile, Matcher with calibrated thresholds, and ModalitySignal mapping.
Strictly follows RUKA-VI Chapter XIII (Vision).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np

from ..math.linalg import cosine_similarity

COSINE_THRESHOLD_DOC = 0.363  # default dari dokumentasi resmi OpenCV Zoo (LFW 99.60%)


@dataclass
class FaceProfile:
    """Profil wajah: kumpulan embedding 128-d terdaftar."""

    profile_id: str
    embeddings: list[np.ndarray] = field(default_factory=list)

    def add(self, embedding: np.ndarray) -> None:
        v = np.asarray(embedding, dtype=np.float64).ravel()
        if v.size != 128:
            raise ValueError(f"embedding SFace 128-d, dapat {v.size}")
        self.embeddings.append(v)


@dataclass(frozen=True)
class FaceMatch:
    """Hasil pencocokan wajah terhadap profil terdaftar."""

    profile_id: str | None
    score: float
    verdict: str  # 'KNOWN' | 'LOW_CONFIDENCE' | 'UNKNOWN' | 'UNAVAILABLE'
    margin: float


class FaceIdentityMatcher:
    """Matching ber-ambang terkalibrasi — default dari DOKUMENTASI resmi
    (0.363 cosine), ditimpa hasil kalibrasi deployment bila ada.
    Ambang ganda: known (≥ t_known) dan reject (< t_reject) — zona tengah
    LOW_CONFIDENCE: RUKA TIDAK menyatakan tahu bila bukti abu-abu.
    """

    def __init__(
        self,
        t_known: float = COSINE_THRESHOLD_DOC,
        t_reject: float | None = None,
    ) -> None:
        if t_reject is None:
            t_reject = t_known - 0.04
        if not 0.0 < t_reject < t_known < 1.0:
            raise ValueError("syarat: 0 < t_reject < t_known < 1")
        self.t_known = t_known
        self.t_reject = t_reject
        self.profiles: dict[str, FaceProfile] = {}

    def enroll(self, profile_id: str, embeddings: list[np.ndarray]) -> None:
        p = self.profiles.setdefault(profile_id, FaceProfile(profile_id))
        for e in embeddings:
            p.add(e)

    def match(self, embedding: np.ndarray) -> FaceMatch:
        if not self.profiles:
            return FaceMatch(None, 0.0, "UNAVAILABLE", 0.0)
        v = np.asarray(embedding, dtype=np.float64).ravel()
        scores: list[tuple[str, float]] = []

        for pid in sorted(self.profiles):
            p = self.profiles[pid]
            # skor = cosine TERBAIK terhadap embedding profil (max atas sampel)
            best = max(
                cosine_similarity(v, np.asarray(e).ravel()) for e in p.embeddings
            )
            scores.append((pid, best))
        scores.sort(key=lambda kv: kv[1], reverse=True)
        top_id, top_cos = scores[0]
        second_cos = scores[1][1] if len(scores) > 1 else 0.0
        margin = top_cos - second_cos
        if top_cos >= self.t_known:
            verdict = "KNOWN"
        elif top_cos < self.t_reject:
            verdict = "UNKNOWN"
        else:
            verdict = "LOW_CONFIDENCE"
        return FaceMatch(top_id, round(top_cos, 6), verdict, round(margin, 6))

    def set_calibration(self, t_known: float, t_reject: float) -> None:
        """Terapkan hasil kalibrasi FAR/FRR deployment."""
        if not 0.0 < t_reject < t_known < 1.0:
            raise ValueError("kalibrasi tak valid")
        self.t_known = t_known
        self.t_reject = t_reject

    def capability(self) -> dict[str, Any]:
        return {
            "layer": "perception",
            "kind": "face-recognition",
            "available": bool(self.profiles),
            "n_profiles": len(self.profiles),
            "thresholds": {"known": self.t_known, "reject": self.t_reject},
            "reference_note": (
                "ambang awal = model-card opencv_zoo (LFW 99.60%); "
                "kalibrasi deployment wajib"
            ),
        }
