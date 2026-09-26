"""RUKA VI: Vision Face Detection & Embedding — YuNet and SFace wrappers.
Strictly follows RUKA-VI Chapter XIII (Vision).
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

from .camera import Frame


@dataclass
class FaceDetection:
    """Deteksi satu wajah: bounding box, score, dan 5 titik landmark."""

    box: tuple[float, float, float, float]  # (x, y, w, h)
    score: float
    landmarks: tuple[tuple[float, float], ...]  # 5 landmark (right eye, left eye, nose, right mouth, left mouth)


class YuNetDetector:
    """Detektor wajah YuNet ONNX — ringan, cepat, input adaptif."""

    def __init__(
        self,
        model_path: str | Path,
        score_threshold: float = 0.6,
        nms_threshold: float = 0.3,
        top_k: int = 5000,
    ) -> None:
        p = Path(model_path)
        if not p.is_file():
            raise FileNotFoundError(f"model YuNet tidak ada: {p}")
        import cv2  # noqa: PLC0415

        self._cv2 = cv2
        self.det = cv2.FaceDetectorYN.create(
            str(p), "", (320, 320), score_threshold, nms_threshold, top_k
        )

    def detect(self, image_bgr: np.ndarray) -> list[FaceDetection]:
        """Deteksi semua wajah dalam satu frame BGR. Kosong = tidak ada wajah."""
        if image_bgr.ndim != 3 or image_bgr.shape[2] != 3:
            raise ValueError("butuh gambar BGR (h, w, 3)")
        h, w = image_bgr.shape[:2]
        self.det.setInputSize((w, h))
        _retval, faces = self.det.detect(image_bgr)
        out: list[FaceDetection] = []
        if faces is None:
            return out
        for f in np.atleast_2d(faces):
            box = (float(f[0]), float(f[1]), float(f[2]), float(f[3]))
            lm = tuple((float(f[4 + 2 * i]), float(f[5 + 2 * i])) for i in range(5))
            out.append(FaceDetection(box=box, score=float(f[14]), landmarks=lm))
        return out

    def detect_frame(self, frame: Frame) -> list[FaceDetection]:
        return self.detect(frame.pixels)


class SFaceEmbedder:
    """Wrapper SFace — embedding 128-d per wajah ter-align."""

    def __init__(self, model_path: str | Path) -> None:
        p = Path(model_path)
        if not p.is_file():
            raise FileNotFoundError(f"model SFace tidak ada: {p}")
        import cv2  # noqa: PLC0415

        self._cv2 = cv2
        self.rec = cv2.FaceRecognizerSF.create(str(p), "")
        self._metric_cosine = getattr(cv2, "FaceRecognizerSF_FR_COSINE", 0)
        self._metric_l2 = getattr(cv2, "FaceRecognizerSF_FR_NORM_L2", 1)

    def align_crop(self, image_bgr: np.ndarray, detection: FaceDetection) -> np.ndarray:
        """Crop wajah ter-align 112×112 — pra-syarat embedding SFace."""
        face_row = np.array(
            [
                detection.box[0],
                detection.box[1],
                detection.box[2],
                detection.box[3],
                *[c for pt in detection.landmarks for c in pt],
                detection.score,
            ],
            dtype=np.float32,
        )
        return self.rec.alignCrop(image_bgr, face_row)

    def embed(self, aligned_bgr: np.ndarray) -> np.ndarray:
        """(112,112,3) → embedding (128,) float32 mentah."""
        feat = self.rec.feature(aligned_bgr)  # (1, 128) float32
        return feat.ravel()

    def embed_face(
        self, image_bgr: np.ndarray, detection: FaceDetection
    ) -> np.ndarray:
        aligned = self.align_crop(image_bgr, detection)
        return self.embed(aligned)

    @staticmethod
    def match_cosine(a: np.ndarray, b: np.ndarray) -> float:
        """cos_sim(a, b) — untuk embedding SFace."""
        a = np.asarray(a, dtype=np.float64).ravel()
        b = np.asarray(b, dtype=np.float64).ravel()
        na = np.linalg.norm(a)
        nb = np.linalg.norm(b)
        if na == 0.0 or nb == 0.0:
            raise ValueError("embedding nol — rusak")
        return float(np.dot(a, b) / (na * nb))

    def measure_latency(
        self, image_bgr: np.ndarray, detection: FaceDetection, repeats: int = 5
    ) -> dict[str, float]:
        """Ukur latensi align+embed (ms) — dipakai eksperimen EXPECTED vs MEASURED."""
        times: list[float] = []
        for _ in range(repeats):
            t0 = time.perf_counter()
            self.embed_face(image_bgr, detection)
            times.append((time.perf_counter() - t0) * 1000.0)
        arr = np.asarray(times)
        return {
            "align_embed_ms_mean": float(arr.mean()),
            "align_embed_ms_p50": float(np.percentile(arr, 50)),
            "align_embed_ms_p95": float(np.percentile(arr, 95)),
            "repeats": int(repeats),
        }


def cosine_to_similarity(cos: float) -> float:
    """Peta cosine [-1,1] → similarity [0,1]: (cos + 1)/2."""
    return (cos + 1.0) / 2.0
