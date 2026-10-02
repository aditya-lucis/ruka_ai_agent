# -*- coding: utf-8 -*-
"""Mathematical Foundations — Utility Scoring and Constrained Optimization.

Menyediakan fungsi optimasi multi-objektif, scoring utility rencana/aksi,
dan pemilihan aksi ber-constraint sumber daya (budget & risiko).
"""
from __future__ import annotations

from typing import Sequence
import numpy as np


def utility_score(
    benefit: float,
    cost: float,
    risk: float,
    weights: tuple[float, float, float] = (1.0, 0.5, 0.5),
) -> float:
    """Menghitung skor utilitas multi-objektif:
    Utility = w_benefit * benefit - w_cost * cost - w_risk * risk.

    Args:
        benefit: Perkiraan manfaat atau reward yang diharapkan [0.0 - 1.0+].
        cost: Perkiraan beban (token, waktu, memori, delay).
        risk: Perkiraan tingkat bahaya / permission risk level.
        weights: Pembobotan relatif (w_benefit, w_cost, w_risk).
    """
    w_b, w_c, w_r = weights
    return float(w_b * benefit - w_c * cost - w_r * risk)


def softmax_select(
    scores: np.ndarray | Sequence[float],
    temperature: float = 1.0,
    rng: np.random.Generator | None = None,
) -> int:
    """Memilih indeks aksi menggunakan sampling probabilitas softmax.

    Bila temperature -> 0, bertindak greedy (argmax).
    """
    s = np.asarray(scores, dtype=np.float64)
    if s.size == 0:
        raise ValueError("scores tidak boleh kosong")
    if temperature <= 1e-4:
        return int(np.argmax(s))

    from src.math_foundations.probability import softmax
    probs = softmax(s, temperature=temperature)
    gen = rng if rng is not None else np.random.default_rng()
    return int(gen.choice(len(probs), p=probs))


def pareto_frontier_indices(costs: np.ndarray | Sequence[float], benefits: np.ndarray | Sequence[float]) -> list[int]:
    """Menentukan indeks titik non-dominated pada Pareto frontier (minimalkan cost, maksimalkan benefit)."""
    c = np.asarray(costs, dtype=np.float64)
    b = np.asarray(benefits, dtype=np.float64)
    if c.shape != b.shape or c.size == 0:
        return []

    n = c.size
    indices = list(range(n))
    # Urutkan berdasarkan cost menaik, benefit menurun
    sorted_order = sorted(indices, key=lambda i: (c[i], -b[i]))

    frontier: list[int] = []
    max_benefit_so_far = -float("inf")

    for idx in sorted_order:
        if b[idx] > max_benefit_so_far:
            frontier.append(idx)
            max_benefit_so_far = b[idx]

    return sorted(frontier)
