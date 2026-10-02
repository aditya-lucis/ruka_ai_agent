# -*- coding: utf-8 -*-
"""Mathematical Foundations — Statistical Learning and Drift Detection.

Menyediakan statistik berjalan (running statistics via Welford's algorithm),
moving averages, metrik klasifikasi/evaluasi, dan deteksi pergeseran distribusi (drift detection).
"""
from __future__ import annotations

import math
from typing import Sequence
import numpy as np


class RunningStats:
    """Kalkulator statistik daring (online) menggunakan algoritma Welford.
    Menghitung mean, variansi, standar deviasi, min, max secara numerik stabil
    tanpa menyimpan seluruh riwayat data dalam memori.
    """
    def __init__(self) -> None:
        self.count: int = 0
        self.mean: float = 0.0
        self._m2: float = 0.0
        self.min_val: float = float("inf")
        self.max_val: float = float("-inf")

    def update(self, x: float) -> None:
        """Memasukkan nilai sampel baru."""
        val = float(x)
        self.count += 1
        delta = val - self.mean
        self.mean += delta / self.count
        delta2 = val - self.mean
        self._m2 += delta * delta2

        if val < self.min_val:
            self.min_val = val
        if val > self.max_val:
            self.max_val = val

    @property
    def variance(self) -> float:
        """Variansi sampel tak bias (ddof=1). 0.0 jika sampel < 2."""
        if self.count < 2:
            return 0.0
        return self._m2 / (self.count - 1)

    @property
    def standard_deviation(self) -> float:
        """Standar deviasi sampel."""
        return math.sqrt(self.variance)


def exponential_moving_average(previous: float, current: float, alpha: float = 0.2) -> float:
    """Menghitung Exponential Moving Average (EMA):
    EMA = alpha * current + (1 - alpha) * previous.
    """
    a = max(0.0, min(1.0, float(alpha)))
    return float(a * current + (1.0 - a) * previous)


def wasserstein_distance_1d(u_values: np.ndarray | Sequence[float], v_values: np.ndarray | Sequence[float]) -> float:
    """Menghitung Wasserstein-1 Distance (Earth Mover's Distance) pada sampel 1D.
    Sangat berguna untuk mendeteksi drift pada distribusi skor atau jarak embedding.
    """
    u = np.sort(np.asarray(u_values, dtype=np.float64).flatten())
    v = np.sort(np.asarray(v_values, dtype=np.float64).flatten())

    if u.size == 0 or v.size == 0:
        return 0.0

    all_vals = np.concatenate([u, v])
    all_vals.sort()

    u_cdf = np.searchsorted(u, all_vals[:-1], side="right") / u.size
    v_cdf = np.searchsorted(v, all_vals[:-1], side="right") / v.size

    deltas = np.diff(all_vals)
    dist = np.sum(np.abs(u_cdf - v_cdf) * deltas)
    return float(dist)


def classification_metrics(y_true: Sequence[int | bool], y_pred: Sequence[int | bool]) -> dict[str, float]:
    """Menghitung metrik performa klasifikasi biner (Accuracy, Precision, Recall, F1)."""
    yt = [int(v) for v in y_true]
    yp = [int(v) for v in y_pred]

    if len(yt) != len(yp):
        raise ValueError("Panjang target dan prediksi tidak cocok")
    if not yt:
        return {"accuracy": 0.0, "precision": 0.0, "recall": 0.0, "f1": 0.0}

    tp = sum(1 for t, p in zip(yt, yp) if t == 1 and p == 1)
    tn = sum(1 for t, p in zip(yt, yp) if t == 0 and p == 0)
    fp = sum(1 for t, p in zip(yt, yp) if t == 0 and p == 1)
    fn = sum(1 for t, p in zip(yt, yp) if t == 1 and p == 0)

    total = len(yt)
    accuracy = (tp + tn) / total
    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1 = (2 * precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0

    return {
        "accuracy": round(accuracy, 4),
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1": round(f1, 4),
    }
