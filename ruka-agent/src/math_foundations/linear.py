# -*- coding: utf-8 -*-
"""Mathematical Foundations — Pure Linear Algebra Utilities.

Menyediakan operasi aljabar linier murni berbasis NumPy:
normalisasi vektor, cosine similarity, batch similarity, proyeksi,
dan ortogonalisasi tanpa ketergantungan model bahasa.
"""
from __future__ import annotations

import numpy as np


def l2_normalize(v: np.ndarray, eps: float = 1e-12) -> np.ndarray:
    """Melakukan normalisasi L2 pada vektor (1D) atau matriks baris (2D).

    Args:
        v: Vektor 1D atau matriks 2D dengan tipe numerik.
        eps: Nilai epsilon untuk stabilitas numerik menghindari pembagian dengan nol.

    Returns:
        np.ndarray dengan panjang unit (norm L2 = 1.0).
    """
    arr = np.asarray(v, dtype=np.float32)
    if arr.ndim == 1:
        norm = np.linalg.norm(arr)
        if norm <= eps:
            return np.zeros_like(arr)
        return arr / norm
    elif arr.ndim == 2:
        norms = np.linalg.norm(arr, axis=1, keepdims=True)
        norms = np.where(norms <= eps, 1.0, norms)
        normalized = arr / norms
        # Set baris yang asalnya nol tetap nol
        zero_rows = (np.linalg.norm(arr, axis=1, keepdims=True) <= eps).squeeze(-1)
        normalized[zero_rows] = 0.0
        return normalized
    else:
        raise ValueError(f"Dimensi array tidak didukung: {arr.ndim}. Wajib 1D atau 2D.")


def cosine_similarity(a: np.ndarray, b: np.ndarray, eps: float = 1e-12) -> float:
    """Menghitung kemiripan kosinus antara dua vektor 1D dalam rentang [-1.0, 1.0]."""
    va = np.asarray(a, dtype=np.float32).flatten()
    vb = np.asarray(b, dtype=np.float32).flatten()
    if va.shape != vb.shape:
        raise ValueError(f"Ukuran dimensi vektor tidak sama: {va.shape} vs {vb.shape}")
    
    norm_a = float(np.linalg.norm(va))
    norm_b = float(np.linalg.norm(vb))
    if norm_a <= eps or norm_b <= eps:
        return 0.0

    dot = float(np.dot(va, vb))
    val = dot / (norm_a * norm_b)
    return float(np.clip(val, -1.0, 1.0))


def batch_cosine(query: np.ndarray, matrix: np.ndarray, eps: float = 1e-12) -> np.ndarray:
    """Menghitung kemiripan kosinus antara 1 vektor query (D,) dan sekumpulan vektor (N, D).

    Returns:
        np.ndarray berdimensi (N,) berisi nilai skor kemiripan dalam rentang [-1.0, 1.0].
    """
    q = np.asarray(query, dtype=np.float32).flatten()
    m = np.asarray(matrix, dtype=np.float32)

    if m.ndim != 2:
        raise ValueError(f"Matriks referensi harus berdimensi 2 (N, D), didapat ndim={m.ndim}")
    if m.shape[0] == 0:
        return np.empty((0,), dtype=np.float32)
    if m.shape[1] != q.shape[0]:
        raise ValueError(f"Dimensi fitur tidak cocok: query ({q.shape[0]}) vs matrix ({m.shape[1]})")

    qn = l2_normalize(q, eps=eps)
    mn = l2_normalize(m, eps=eps)

    # Bila query ber-norm 0, hasil semua 0
    if np.linalg.norm(qn) <= eps:
        return np.zeros(m.shape[0], dtype=np.float32)

    scores = np.dot(mn, qn)
    return np.clip(scores, -1.0, 1.0)


def euclidean_distance(a: np.ndarray, b: np.ndarray) -> float:
    """Menghitung jarak Euclidean antara dua vektor."""
    va = np.asarray(a, dtype=np.float32).flatten()
    vb = np.asarray(b, dtype=np.float32).flatten()
    if va.shape != vb.shape:
        raise ValueError(f"Ukuran dimensi vektor tidak sama: {va.shape} vs {vb.shape}")
    return float(np.linalg.norm(va - vb))


def batch_euclidean(query: np.ndarray, matrix: np.ndarray) -> np.ndarray:
    """Menghitung jarak Euclidean antara query (D,) dan matriks (N, D)."""
    q = np.asarray(query, dtype=np.float32).flatten()
    m = np.asarray(matrix, dtype=np.float32)
    if m.ndim != 2:
        raise ValueError(f"Matriks harus berdimensi 2 (N, D), didapat ndim={m.ndim}")
    if m.shape[0] == 0:
        return np.empty((0,), dtype=np.float32)
    if m.shape[1] != q.shape[0]:
        raise ValueError(f"Dimensi fitur tidak cocok: query ({q.shape[0]}) vs matrix ({m.shape[1]})")
    diff = m - q
    return np.linalg.norm(diff, axis=1)


def vector_projection(a: np.ndarray, b: np.ndarray, eps: float = 1e-12) -> np.ndarray:
    """Memproyeksikan vektor a ke arah vektor b: proj_b(a) = ((a . b) / ||b||^2) * b."""
    va = np.asarray(a, dtype=np.float32).flatten()
    vb = np.asarray(b, dtype=np.float32).flatten()
    if va.shape != vb.shape:
        raise ValueError(f"Ukuran dimensi vektor tidak sama: {va.shape} vs {vb.shape}")
    norm_sq = float(np.dot(vb, vb))
    if norm_sq <= eps:
        return np.zeros_like(va)
    scalar = float(np.dot(va, vb)) / norm_sq
    return scalar * vb


def orthonormalize(vectors: np.ndarray, eps: float = 1e-12) -> np.ndarray:
    """Proses Gram-Schmidt untuk menghasilkan basis ortonormal dari sekumpulan vektor (K, D)."""
    v_arr = np.asarray(vectors, dtype=np.float32)
    if v_arr.ndim != 2:
        raise ValueError("vectors harus berupa matriks 2D (K, D)")
    if v_arr.shape[0] == 0:
        return np.empty((0, v_arr.shape[1]), dtype=np.float32)

    basis: list[np.ndarray] = []
    for v in v_arr:
        w = v.copy()
        for u in basis:
            proj = (np.dot(w, u) / np.dot(u, u)) * u
            w = w - proj
        norm_w = np.linalg.norm(w)
        if norm_w > eps:
            basis.append(w / norm_w)

    if not basis:
        return np.empty((0, v_arr.shape[1]), dtype=np.float32)
    return np.array(basis, dtype=np.float32)
