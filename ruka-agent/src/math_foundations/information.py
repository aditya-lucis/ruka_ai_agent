# -*- coding: utf-8 -*-
"""Mathematical Foundations — Information Theory and Importance Scoring.

Menyediakan utilitas teori informasi:
Kullback-Leibler (KL) divergence, kalkulasi surprise memori,
skor importance memori, dan estimasi mutual information.
"""
from __future__ import annotations

import math
from typing import Sequence
import numpy as np


def kl_divergence(
    p: np.ndarray | Sequence[float],
    q: np.ndarray | Sequence[float],
    eps: float = 1e-12,
) -> float:
    """Menghitung Kullback-Leibler Divergence: D_KL(P || Q) = sum(p_i * log(p_i / q_i)).

    P dan Q akan dinormalisasi jika jumlahnya != 1.0.
    """
    arr_p = np.asarray(p, dtype=np.float64).flatten()
    arr_q = np.asarray(q, dtype=np.float64).flatten()

    if arr_p.shape != arr_q.shape:
        raise ValueError(f"Dimensi P dan Q tidak cocok: {arr_p.shape} vs {arr_q.shape}")
    if arr_p.size == 0:
        return 0.0

    sum_p = np.sum(arr_p)
    sum_q = np.sum(arr_q)
    if sum_p <= eps or sum_q <= eps:
        return 0.0

    norm_p = np.clip(arr_p / sum_p, eps, 1.0)
    norm_q = np.clip(arr_q / sum_q, eps, 1.0)

    # Hanya hitung di mana p_i > 0
    mask = norm_p > eps
    div = np.sum(norm_p[mask] * np.log2(norm_p[mask] / norm_q[mask]))
    return max(0.0, float(div))


def memory_surprise(predicted_prob: float, eps: float = 1e-12) -> float:
    """Menghitung nilai 'surprise' (self-information) dari suatu kejadian:
    I(x) = -log2(P(x)).

    Semakin tidak terduga sebuah input atau peristiwa, semakin tinggi nilai surprise-nya.
    Rentang dinormalisasi secara logistik atau dibatasi agar tidak meluap tak terhingga.
    """
    p = max(eps, min(1.0, float(predicted_prob)))
    raw_surprise = -math.log2(p)
    # Normalkan ke skala 0.0 - 1.0 dengan sigmoid lembut berbasis skala informasi 10 bit
    return float(1.0 - math.exp(-raw_surprise / 3.0))


def importance_score(
    relevance: float,
    recency: float,
    surprise: float,
    weights: tuple[float, float, float] = (0.5, 0.3, 0.2),
) -> float:
    """Menghitung skor importance memori berdasarkan perpaduan:
    Importance = alpha * relevance + beta * recency + gamma * surprise.
    """
    alpha, beta, gamma = weights
    score = (
        alpha * max(0.0, min(1.0, relevance))
        + beta * max(0.0, min(1.0, recency))
        + gamma * max(0.0, min(1.0, surprise))
    )
    return float(max(0.0, min(1.0, score)))


def mutual_information_discrete(contingency_table: np.ndarray, eps: float = 1e-12) -> float:
    """Menghitung Mutual Information I(X; Y) dari tabel kontingensi bersama (2D)."""
    table = np.asarray(contingency_table, dtype=np.float64)
    if table.ndim != 2 or table.size == 0:
        return 0.0

    total = np.sum(table)
    if total <= eps:
        return 0.0

    p_xy = table / total
    p_x = np.sum(p_xy, axis=1, keepdims=True)
    p_y = np.sum(p_xy, axis=0, keepdims=True)

    denom = np.dot(p_x, p_y)
    mask = (p_xy > eps) & (denom > eps)

    mi = np.sum(p_xy[mask] * np.log2(p_xy[mask] / denom[mask]))
    return max(0.0, float(mi))
