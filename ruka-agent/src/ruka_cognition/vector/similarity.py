# -*- coding: utf-8 -*-
"""Similarity and distance kernels — the math Ruka's Blood Sight runs on.
All functions accept 1-D sequences or 2-D batches (axis semantics like
NumPy ufuncs on the last axis) and return float or array. Cosine is
computed in the numerically stable form ``dot/(||a|| ||b|| + eps)``.
"""
from __future__ import annotations
import numpy as np
import numpy.typing as npt
ArrayLike = npt.ArrayLike
_EPS = 1e-12

def _as_matrix(x: ArrayLike) -> np.ndarray:
    a = np.asarray(x, dtype=np.float64)
    if a.ndim == 1:
        a = a.reshape(1, -1)
    if a.ndim != 2:
        raise ValueError(f"expected 1-D or 2-D input, got shape {a.shape}")
    return a

def l2_norm(x: ArrayLike) -> np.ndarray:
    """||x||_2 along the last axis."""
    a = _as_matrix(x)
    return np.sqrt((a * a).sum(axis=-1))

def normalize(x: ArrayLike) -> np.ndarray:
    """Project vectors onto the unit sphere (L2).
    Zero vectors map to zero (they have no direction); callers that
    need to reject them should check norms beforehand.
    """
    a = _as_matrix(x).copy()
    n = np.sqrt((a * a).sum(axis=-1, keepdims=True))
    return a / np.maximum(n, _EPS)

def dot(x: ArrayLike, y: ArrayLike) -> np.ndarray:
    """Inner product; on normalized vectors this *is* cosine."""
    a, b = _as_matrix(x), _as_matrix(y)
    if a.shape[-1] != b.shape[-1]:
        raise ValueError(f"dimension mismatch: {a.shape[-1]} vs {b.shape[-1]}")
    return (a * b).sum(axis=-1)

def cosine(x: ArrayLike, y: ArrayLike) -> np.ndarray:
    """Cosine similarity in [-1, 1]; 0 for zero vectors."""
    a, b = _as_matrix(x), _as_matrix(y)
    if a.shape[-1] != b.shape[-1]:
        raise ValueError(f"dimension mismatch: {a.shape[-1]} vs {b.shape[-1]}")
    num = (a * b).sum(axis=-1)
    den = np.sqrt((a * a).sum(axis=-1)) * np.sqrt((b * b).sum(axis=-1))
    return num / np.maximum(den, _EPS)

def euclidean(x: ArrayLike, y: ArrayLike) -> np.ndarray:
    """Euclidean distance ||x - y||_2."""
    a, b = _as_matrix(x), _as_matrix(y)
    if a.shape[-1] != b.shape[-1]:
        raise ValueError(f"dimension mismatch: {a.shape[-1]} vs {b.shape[-1]}")
    return np.sqrt(((a - b) ** 2).sum(axis=-1))

def cosine_to_distance(similarity: ArrayLike) -> np.ndarray:
    """Convert cosine similarity to a valid metric distance.
    Cosine similarity itself violates the triangle inequality; the
    mapping d = sqrt(2(1 - s)) (chord distance on the unit sphere)
    restores it. Rangkaian ranking must sort by a real distance when
    the metric property matters (ANN libraries assume it).
    """
    s = np.clip(np.asarray(similarity, dtype=np.float64), -1.0, 1.0)
    return np.sqrt(np.maximum(2.0 * (1.0 - s), 0.0))
