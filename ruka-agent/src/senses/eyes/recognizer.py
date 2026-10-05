# -*- coding: utf-8 -*-
"""Face Recognizer & Enrollment (FR-EY-03, FR-EY-04, FR-EY-05).

Pengenalan wajah menggunakan embedding ArcFace 512 dimensi:
- Ambang kesamaan kosinus konservatif 0.35.
- Pendaftaran 5 pose (depan, kiri, kanan, atas, bawah) dengan gerbang ketajaman varians Laplacian >= 60.
- Hanya menyimpan vektor rata-rata ternormalisasi; nol foto mentah disimpan.
- Uji keaslian (anti-spoofing) tantangan kedip.
"""
from __future__ import annotations

import math
from typing import Sequence
from src.senses.eyes.models import FaceIdentity


class FaceRecognizer:
    def __init__(
        self,
        cosine_threshold: float = 0.35,
        target_user_id: str = "young_lord",
    ) -> None:
        self.cosine_threshold = cosine_threshold
        self.target_user_id = target_user_id
        self._enrolled_embedding: list[float] | None = None

    @property
    def is_enrolled(self) -> bool:
        return self._enrolled_embedding is not None

    def enroll_5_poses(
        self,
        pose_embeddings: Sequence[Sequence[float]],
        sharpness_scores: Sequence[float],
    ) -> bool:
        """Mendaftarkan wajah 5 pose dengan verifikasi ketajaman (Laplacian >= 60)."""
        if len(pose_embeddings) != 5:
            raise ValueError(f"Membutuhkan tepat 5 pose wajah, menerima {len(pose_embeddings)}")

        for i, score in enumerate(sharpness_scores):
            if score < 60.0:
                raise ValueError(f"Pose ke-{i+1} gagal gerbang ketajaman (skor {score:.1f} < 60.0)")

        # Hitung rata-rata vektor 5 pose
        dim = len(pose_embeddings[0])
        avg_vec = [0.0] * dim
        for pose in pose_embeddings:
            if len(pose) != dim:
                raise ValueError("Dimensi embedding tidak konsisten")
            for j in range(dim):
                avg_vec[j] += pose[j]

        # Normalisasi L2 vektor rata-rata
        norm = math.sqrt(sum(x * x for x in avg_vec))
        if norm <= 1e-9:
            raise ValueError("Vektor rata-rata wajah memiliki magnitude nol")

        self._enrolled_embedding = [float(x / norm) for x in avg_vec]
        return True

    def recognize(self, test_embedding: Sequence[float]) -> FaceIdentity:
        """Mengenali identitas dari embedding wajah 512-dimensi."""
        if self._enrolled_embedding is None:
            return FaceIdentity(
                user_id="unknown",
                similarity=0.0,
                is_young_lord=False,
                confidence=0.0,
            )

        norm = math.sqrt(sum(x * x for x in test_embedding))
        if norm <= 1e-9:
            return FaceIdentity(
                user_id="unknown",
                similarity=0.0,
                is_young_lord=False,
                confidence=0.0,
            )

        normed_test = [x / norm for x in test_embedding]
        similarity = sum(a * b for a, b in zip(self._enrolled_embedding, normed_test))

        is_owner = similarity >= self.cosine_threshold
        user_id = self.target_user_id if is_owner else "stranger"

        return FaceIdentity(
            user_id=user_id,
            similarity=float(similarity),
            is_young_lord=is_owner,
            confidence=float(max(0.0, min(1.0, similarity))),
            embedding_512=tuple(normed_test),
        )

    def verify_liveness_blink(self, eye_aspect_ratios: Sequence[float]) -> bool:
        """Uji hidup kedip (FR-EY-05): rasio mata tertutup < 0.20 di dalam jendela observasi."""
        if not eye_aspect_ratios:
            return False
        # Harus ada setidaknya satu titik di mana mata tertutup (EAR < 0.20)
        # dan setidaknya satu titik mata terbuka (EAR >= 0.25)
        has_closed = any(ear < 0.20 for ear in eye_aspect_ratios)
        has_open = any(ear >= 0.25 for ear in eye_aspect_ratios)
        return has_closed and has_open
