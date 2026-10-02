# -*- coding: utf-8 -*-
"""Mathematical Foundations — Probability, Entropy, and Calibration.

Menyediakan kalkulasi probabilistik murni:
pembaruan Bayesian, entropi Shannon, kalibrasi kepastian (ECE, Brier Score),
dan scaling softmax ber-temperatur.
"""
from __future__ import annotations

import math
from typing import Sequence
import numpy as np


def shannon_entropy(probs: np.ndarray | Sequence[float], eps: float = 1e-12, base: float = 2.0) -> float:
    """Menghitung Entropi Shannon dari suatu distribusi probabilitas diskrit:
    H(X) = - sum(p_i * log_base(p_i)).

    Args:
        probs: Array probabilitas. Akan dinormalisasi jika jumlahnya != 1.0.
        eps: Nilai stabilisasi numerik.
        base: Basis logaritma (default 2.0 untuk satuan bit/shannon).
    """
    p = np.asarray(probs, dtype=np.float64).flatten()
    if p.size == 0:
        return 0.0
    p = np.clip(p, 0.0, None)
    total = np.sum(p)
    if total <= eps:
        return 0.0
    p = p / total

    # Ambil probabilitas non-nol
    valid_p = p[p > eps]
    if valid_p.size <= 1:
        return 0.0

    if base == 2.0:
        log_p = np.log2(valid_p)
    elif base == math.e:
        log_p = np.log(valid_p)
    else:
        log_p = np.log(valid_p) / np.log(base)

    entropy = -float(np.sum(valid_p * log_p))
    return max(0.0, entropy)


def bayesian_update(
    prior: float,
    likelihood: float,
    false_alarm_prob: float = 0.05,
    eps: float = 1e-12,
) -> float:
    """Memperbarui probabilitas posterior P(H|E) berdasarkan bukti baru E:

    P(H|E) = (P(E|H) * P(H)) / (P(E|H) * P(H) + P(E|~H) * (1 - P(H)))

    Args:
        prior: P(H) - probabilitas awal hipotesis [0.0, 1.0].
        likelihood: P(E|H) - probabilitas bukti jika hipotesis benar [0.0, 1.0].
        false_alarm_prob: P(E|~H) - probabilitas bukti jika hipotesis salah.
        eps: Epsilon kestabilan numerik.

    Returns:
        Posterior probability P(H|E) dalam rentang [0.0, 1.0].
    """
    p_h = max(0.0, min(1.0, float(prior)))
    p_e_given_h = max(0.0, min(1.0, float(likelihood)))
    p_e_given_not_h = max(0.0, min(1.0, float(false_alarm_prob)))

    numerator = p_e_given_h * p_h
    denominator = numerator + p_e_given_not_h * (1.0 - p_h)

    if denominator <= eps:
        return p_h

    posterior = numerator / denominator
    return max(0.0, min(1.0, float(posterior)))


def brier_score(
    probabilities: np.ndarray | Sequence[float],
    outcomes: np.ndarray | Sequence[int | bool | float],
) -> float:
    """Menghitung Brier Score (Mean Squared Error antara probabilitas prediksi dan hasil biner aktual):
    BS = (1/N) * sum((p_i - y_i)^2). Rentang: 0 (sempurna) hingga 1 (terburuk).
    """
    p = np.asarray(probabilities, dtype=np.float64).flatten()
    y = np.asarray(outcomes, dtype=np.float64).flatten()
    if p.shape != y.shape:
        raise ValueError(f"Ukuran tidak cocok: {p.shape} vs {y.shape}")
    if p.size == 0:
        return 0.0
    return float(np.mean((p - y) ** 2))


def expected_calibration_error(
    confidences: np.ndarray | Sequence[float],
    accuracies: np.ndarray | Sequence[int | bool | float],
    n_bins: int = 10,
) -> float:
    """Menghitung Expected Calibration Error (ECE):
    ECE = sum_{b=1}^B ( |B_b| / N ) * |acc(B_b) - conf(B_b)|.
    """
    confs = np.asarray(confidences, dtype=np.float64).flatten()
    accs = np.asarray(accuracies, dtype=np.float64).flatten()

    if confs.shape != accs.shape:
        raise ValueError(f"Ukuran confidences dan accuracies tidak cocok: {confs.shape} vs {accs.shape}")
    n = confs.size
    if n == 0:
        return 0.0

    bins = np.linspace(0.0, 1.0, n_bins + 1)
    ece = 0.0

    for i in range(n_bins):
        bin_lower = bins[i]
        bin_upper = bins[i + 1]

        # Inklusif untuk bin terakhir
        if i == n_bins - 1:
            in_bin = (confs >= bin_lower) & (confs <= bin_upper)
        else:
            in_bin = (confs >= bin_lower) & (confs < bin_upper)

        count = np.sum(in_bin)
        if count > 0:
            bin_acc = np.mean(accs[in_bin])
            bin_conf = np.mean(confs[in_bin])
            ece += (count / n) * abs(bin_acc - bin_conf)

    return float(ece)


def temperature_scale(logits: np.ndarray | Sequence[float], temperature: float = 1.0) -> np.ndarray:
    """Menskala logits dengan temperatur sebelum diaplikasikan ke softmax."""
    t = max(1e-6, float(temperature))
    arr = np.asarray(logits, dtype=np.float64)
    return arr / t


def softmax(logits: np.ndarray | Sequence[float], temperature: float = 1.0) -> np.ndarray:
    """Menghitung probabilitas softmax dengan temperatur terkontrol dan stabilitas numerik."""
    scaled = temperature_scale(logits, temperature=temperature)
    if scaled.size == 0:
        return np.empty((0,), dtype=np.float64)

    # Shift max untuk kestabilan numerik
    max_val = np.max(scaled, axis=-1, keepdims=True)
    exp_vals = np.exp(scaled - max_val)
    sum_exp = np.sum(exp_vals, axis=-1, keepdims=True)
    return exp_vals / sum_exp
