"""ruka_companion.math.metrics — Biometric operating metrics: ROC / FAR / FRR / EER.
Volume VI, Gate V6-2. Perangkat TERUKUR: semua fungsi menerima skor nyata
(genuine + impostor) dan mengembalikan angka yang bisa direproduksi.
Definisi (biner, "positive" = diterima sebagai genuine):
    FAR(θ) = P(accept | impostor)   = #impostor ≥ θ / #impostor
    FRR(θ) = P(reject | genuine)    = #genuine  < θ / #genuine
    EER    = θ* di mana FAR(θ*) ≈ FRR(θ*)
Semakin BESAR skor, semakin "genuine" (konvensi similarity).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable, Sequence

import numpy as np

__all__ = [
    "OperatingPoint",
    "far_frr",
    "eer",
    "roc_curve",
    "auc",
    "youden_j",
    "cost_optimal_threshold",
    "threshold_report",
]


@dataclass(frozen=True)
class OperatingPoint:
    """Satu titik kerja biometrik."""

    threshold: float
    far: float
    frr: float


def _scores(arr: Iterable[float], name: str) -> np.ndarray:
    a = np.asarray(list(arr), dtype=np.float64).ravel()
    if a.size == 0:
        raise ValueError(f"{name} kosong")
    return a


def far_frr(
    genuine: Sequence[float], impostor: Sequence[float], threshold: float
) -> tuple[float, float]:
    """(FAR, FRR) pada ambang θ — konvensi skor-besar = genuine."""
    g = _scores(genuine, "genuine")
    i = _scores(impostor, "impostor")
    far = float(np.mean(i >= threshold)) if i.size else 0.0
    frr = float(np.mean(g < threshold)) if g.size else 0.0
    return far, frr


def roc_curve(
    genuine: Sequence[float], impostor: Sequence[float], n_points: int = 101
) -> list[OperatingPoint]:
    """Kurva ROC: sapuan θ dari min semua skor sampai max semua skor.
    → daftar OperatingPoint terurut θ naik.
    """
    g = _scores(genuine, "genuine")
    i = _scores(impostor, "impostor")
    lo = float(min(g.min(), i.min()))
    hi = float(max(g.max(), i.max()))
    theta = np.linspace(lo, hi, n_points)
    out: list[OperatingPoint] = []
    for t in theta:
        far, frr = far_frr(g, i, float(t))
        out.append(OperatingPoint(float(t), far, frr))
    return out


def eer(*args: Any, **kwargs: Any) -> tuple[float, float]:
    """Equal Error Rate (EER).
    Bisa dipanggil dengan:
    1) eer(genuine, impostor) -> (t_star, eer_val)
    2) eer(thresholds, fars, frrs) -> (eer_val, t_star) (kompatibilitas test_math)
    """
    if len(args) == 3:
        thresholds, fars, frrs = args
        diffs = np.array(fars) - np.array(frrs)
        for i in range(len(diffs) - 1):
            if diffs[i] * diffs[i + 1] <= 0:
                d0, d1 = diffs[i], diffs[i + 1]
                alpha = 0.0 if d0 == d1 else d0 / (d0 - d1)
                t0, t1 = thresholds[i], thresholds[i + 1]
                t_star = t0 + alpha * (t1 - t0)
                f0, f1 = fars[i], fars[i + 1]
                eer_val = f0 + alpha * (f1 - f0)
                return float(eer_val), float(t_star)
        raise ValueError("Tidak ada persilangan EER yang ditemukan")

    if len(args) == 2:
        genuine, impostor = args
        pts = roc_curve(genuine, impostor)
        prev = pts[0]
        for cur in pts[1:]:
            d0 = prev.far - prev.frr
            d1 = cur.far - cur.frr
            if d0 == 0.0:
                return float(prev.threshold), float(prev.far)
            if d1 == 0.0:
                return float(cur.threshold), float(cur.far)
            if d0 * d1 < 0.0:
                alpha = d0 / (d0 - d1)
                t_star = prev.threshold + alpha * (cur.threshold - prev.threshold)
                eer_val = prev.far + alpha * (cur.far - prev.far)
                return float(t_star), float(eer_val)
            prev = cur
        best = min(pts, key=lambda p: abs(p.far - p.frr))
        return float(best.threshold), float((best.far + best.frr) / 2.0)

    raise ValueError("eer membutuhkan 2 (genuine, impostor) atau 3 (thresholds, fars, frrs) argumen")


def auc(genuine: Sequence[float], impostor: Sequence[float]) -> float:
    """AUC via U-statistik Mann–Whitney eksak."""
    g = _scores(genuine, "genuine")
    i = _scores(impostor, "impostor")
    n_win = 0.0
    for gv in g:
        n_win += float(np.sum(gv > i)) + 0.5 * float(np.sum(gv == i))
    return float(n_win / (g.size * i.size))


def youden_j(genuine: Sequence[float], impostor: Sequence[float]) -> tuple[float, float]:
    """Titik kerja yang memaksimalkan J = 1 - FAR - FRR. Mengembalikan (threshold, max_J)."""
    pts = roc_curve(genuine, impostor)
    best = max(pts, key=lambda p: 1.0 - p.far - p.frr)
    return best.threshold, 1.0 - best.far - best.frr


def cost_optimal_threshold(
    genuine: Sequence[float],
    impostor: Sequence[float],
    c_fa: float = 10.0,
    c_miss: float = 1.0,
    p_impostor: float = 0.5,
) -> float:
    """Ambang biaya-optimal meminimalkan C(θ) = C_FA·FAR·P(imp) + C_MISS·FRR·(1 - P(imp))."""
    pts = roc_curve(genuine, impostor)
    best = min(
        pts,
        key=lambda p: c_fa * p.far * p_impostor + c_miss * p.frr * (1.0 - p_impostor),
    )
    return best.threshold


def threshold_report(
    genuine: Sequence[float],
    impostor: Sequence[float],
    c_fa: float = 10.0,
    c_miss: float = 1.0,
    p_impostor: float = 0.5,
) -> dict[str, Any]:
    """Laporan kalibrasi ambang biometrik lengkap."""
    g = _scores(genuine, "genuine")
    i = _scores(impostor, "impostor")
    t_star, eer_val = eer(g, i)
    pts = roc_curve(g, i)
    j_th, j_val = youden_j(g, i)
    j_pt = next(p for p in pts if p.threshold == j_th)
    c_th = cost_optimal_threshold(g, i, c_fa=c_fa, c_miss=c_miss, p_impostor=p_impostor)
    c_pt = min(pts, key=lambda p: abs(p.threshold - c_th))
    return {
        "genuine_mean": float(g.mean()),
        "genuine_std": float(g.std(ddof=1)) if g.size > 1 else 0.0,
        "impostor_mean": float(i.mean()),
        "impostor_std": float(i.std(ddof=1)) if i.size > 1 else 0.0,
        "eer_threshold": float(t_star),
        "eer_value": float(eer_val),
        "youden_threshold": float(j_pt.threshold),
        "youden_j": float(1.0 - j_pt.far - j_pt.frr),
        "auc": float(auc(g, i)),
        "cost_optimal_threshold": float(c_pt.threshold),
        "cost_at_optimal": {
            "far": float(c_pt.far),
            "frr": float(c_pt.frr),
            "c_fa": float(c_fa),
            "c_miss": float(c_miss),
            "p_impostor": float(p_impostor),
            "expected_cost": float(
                c_fa * c_pt.far * p_impostor + c_miss * c_pt.frr * (1.0 - p_impostor)
            ),
        },
    }
