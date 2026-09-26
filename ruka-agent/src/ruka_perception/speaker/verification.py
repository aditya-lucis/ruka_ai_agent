"""Speaker verification, enrollment, and FAR/FRR/EER evaluation for Ruka Perception.

Implements Listings 11.2 and 11.3b from RUKA-IV.
Provides 1:1 speaker verification with risk-based thresholds,
centroid enrollment with unit-norm enforcement, monotonic FAR/FRR sweeps,
and sub-grid EER linear interpolation.
"""

from __future__ import annotations

import numpy as np


def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    """Kalkulasi kemiripan kosinus antara dua vektor embedding.

    Nilai berada pada rentang [-1.0, 1.0]. Mengembalikan 0.0 jika salah satu norma nol.
    """
    dot = float(np.dot(a, b))
    norm_a = float(np.linalg.norm(a))
    norm_b = float(np.linalg.norm(b))
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return float(dot / (norm_a * norm_b))


class SpeakerVerifier:
    """Verifikasi 1-lawan-1 terhadap satu klaim identitas.

    enroll  : vektor rata-rata enrollment (centroid beberapa sampel)
    claim   : vektor percobaan
    decision: score >= threshold -> accept, else reject
    Threshold BUKAN konstanta universal: ia titik tawar FAR/FRR yang
    dipilih sesuai risiko (FAR tinggi = penyusup masuk; FRR tinggi = pemilik sah ditolak).
    """

    def __init__(self, threshold: float = 0.72) -> None:
        if not (0.0 < threshold < 1.0):
            raise ValueError("threshold di (0, 1)")
        self.threshold = threshold

    @staticmethod
    def enroll(samples: np.ndarray) -> np.ndarray:
        """Centroid enrollment: rata-rata + re-normalisasi supaya
        unit norm (konvensi speaker embedding).
        """
        if samples.ndim != 2 or len(samples) < 1:
            raise ValueError("enrollment butuh (n, d)")
        c = samples.mean(axis=0)
        n = np.linalg.norm(c)
        return c / n if n > 0 else c

    def score(self, claim: np.ndarray, enrolled: np.ndarray) -> float:
        """Skor similarity klaim vs enrollment (cosine)."""
        return cosine_similarity(claim, enrolled)

    def decide(self, score: float) -> bool:
        """Keputusan biner. Kembalikan True = accept."""
        return bool(score >= self.threshold)


def far_frr_sweep(
    scores_genuine: list[float] | np.ndarray,
    scores_impostor: list[float] | np.ndarray,
    thresholds: np.ndarray | None = None,
) -> list[dict]:
    """Menghitung kurva FAR dan FRR sepanjang grid threshold.

    Invarian:
      - FAR monoton turun terhadap threshold
      - FRR monoton naik terhadap threshold
    """
    gen = np.asarray(scores_genuine, dtype=np.float64)
    imp = np.asarray(scores_impostor, dtype=np.float64)
    if gen.size == 0 or imp.size == 0:
        raise ValueError("skor genuine dan impostor tidak boleh kosong")

    if thresholds is None:
        thresholds = np.linspace(0.0, 1.0, 101)

    sweep: list[dict] = []
    for t in thresholds:
        # False Acceptance: Impostor dengan skor >= t
        far = float(np.mean(imp >= t))
        # False Rejection: Genuine dengan skor < t
        frr = float(np.mean(gen < t))
        sweep.append({
            "threshold": float(t),
            "far": far,
            "frr": frr,
        })
    return sweep


def eer(sweep: list[dict]) -> dict:
    """Equal Error Rate: threshold tempat FAR == FRR.

    Ditemukan lewat tanda selisih: karena FAR turun dan FRR naik
    terhadap threshold, kurva bersilang tepat sekali.
    """
    if not sweep:
        raise ValueError("sweep tidak boleh kosong")
    prev = None
    for row in sweep:
        d = row["far"] - row["frr"]
        if prev is not None and (d == 0 or (prev[1] > 0) != (d > 0)):
            # interpolasi linear antar dua titik bersilang
            t0, d0 = prev
            t1, d1 = row["threshold"], d
            if d1 == d0:
                return {"eer": row["frr"], "threshold": row["threshold"]}
            tt = t0 + (t1 - t0) * (0 - d0) / (d1 - d0)
            # estimasi FRR pada tt (FRR linear antar titik)
            frr0 = next(r for r in sweep if r["threshold"] == t0)["frr"]
            frr1 = row["frr"]
            eer_v = frr0 + (frr1 - frr0) * (tt - t0) / (t1 - t0)
            return {"eer": float(eer_v), "threshold": float(tt)}
        prev = (row["threshold"], d)
    return {
        "eer": float(sweep[-1]["frr"]),
        "threshold": float(sweep[-1]["threshold"]),
    }


def roc_points(sweep: list[dict]) -> list[tuple[float, float]]:
    """ROC: (FAR, 1 - FRR) = (FAR, TAR)."""
    return [(r["far"], 1.0 - r["frr"]) for r in sweep]


def identify(
    claim: np.ndarray, gallery: dict[str, np.ndarray]
) -> tuple[str, float]:
    """Identifikasi 1-dari-N: kandidat skor tertinggi.

    Sengaja dipisah dari verification — masalah berbeda, kesalahan berbeda
    (open-set vs closed-set), dan metriknya berbeda (Top-1 accuracy vs FAR/FRR).
    """
    if not gallery:
        raise ValueError("galeri kosong")
    scores = {name: cosine_similarity(claim, vec) for name, vec in gallery.items()}
    best = max(scores, key=scores.get)
    return best, scores[best]
