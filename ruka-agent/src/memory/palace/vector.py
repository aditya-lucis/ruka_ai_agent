# -*- coding: utf-8 -*-
"""512-Dimensional Vector Embedding & Similarity Engine for Memory Palace (FR-ME-01).

Menyediakan pembuatan embedding 512-dimensi lokal deterministik,
serialisasi biner float32 BLOB untuk SQLite, dan kalkulasi cosine similarity.
"""
from __future__ import annotations

import hashlib
import struct
from typing import Sequence
import numpy as np

EMBEDDING_DIM = 512


def text_to_embedding(text: str, dim: int = EMBEDDING_DIM) -> np.ndarray:
    """Menghasilkan representasi vektor 512-dimensi ternormalisasi L2.
    
    Menggunakan teknik multi-hash random projection yang deterministik,
    cepat (sub-millisecond), dan bebas dependensi jaringan untuk memori lokal.
    """
    if not text:
        vec = np.zeros(dim, dtype=np.float32)
        vec[0] = 1.0
        return vec

    tokens = text.lower().split()
    if not tokens:
        tokens = [text.lower()]

    vec = np.zeros(dim, dtype=np.float64)

    # Akumulasi fitur n-gram dan token hashing
    for token in tokens:
        h = int(hashlib.sha256(token.encode("utf-8")).hexdigest(), 16)
        # Petakan token ke beberapa dimensi
        for i in range(4):
            idx = (h >> (i * 16)) % dim
            sign = 1.0 if ((h >> (i * 16 + 15)) & 1) == 0 else -1.0
            vec[idx] += sign

    # Normalisasi L2
    norm = np.linalg.norm(vec)
    if norm > 1e-9:
        vec = vec / norm
    else:
        vec[0] = 1.0

    return vec.astype(np.float32)


def embedding_to_blob(vec: np.ndarray) -> bytes:
    """Mengubah vektor numpy float32 menjadi binary BLOB untuk SQLite."""
    if not isinstance(vec, np.ndarray) or vec.dtype != np.float32:
        vec = np.asarray(vec, dtype=np.float32)
    return vec.tobytes()


def blob_to_embedding(blob: bytes, dim: int = EMBEDDING_DIM) -> np.ndarray:
    """Mengubah binary BLOB dari SQLite kembali menjadi numpy ndarray 512-dimensi."""
    if not blob:
        return np.zeros(dim, dtype=np.float32)
    arr = np.frombuffer(blob, dtype=np.float32)
    if arr.shape[0] != dim:
        padded = np.zeros(dim, dtype=np.float32)
        n = min(dim, arr.shape[0])
        padded[:n] = arr[:n]
        return padded
    return arr


def cosine_similarity(v1: np.ndarray, v2: np.ndarray) -> float:
    """Menghitung kemiripan kosinus antara dua vektor."""
    dot = float(np.dot(v1, v2))
    norm1 = float(np.linalg.norm(v1))
    norm2 = float(np.linalg.norm(v2))
    if norm1 < 1e-9 or norm2 < 1e-9:
        return 0.0
    return max(0.0, min(1.0, dot / (norm1 * norm2)))
