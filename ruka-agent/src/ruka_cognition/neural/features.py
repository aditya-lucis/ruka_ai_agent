# -*- coding: utf-8 -*-
"""Deterministic text features: hashed character trigrams.
Why not "just embed with the LLM provider"? Because baseline and
training reproducibility must not depend on network state. This is the
classic feature-hashing trick (Weinberger et al., 2009) applied to
character 3-grams — robust to typos, no vocabulary to maintain, and
identical on every machine.
"""
from __future__ import annotations
import hashlib
import numpy as np

_ALPHABET_BONUS = "abcdefghijklmnopqrstuvwxyz0123456789 _-./"

def hashed_trigram_features(texts: list[str], dimension: int = 512,
                            normalize_l2: bool = True) -> np.ndarray:
    """Map texts to dense (n, dimension) float64 feature matrix."""
    if dimension < 8:
        raise ValueError("dimension must be >= 8")
    out = np.zeros((len(texts), dimension), dtype=np.float64)
    for i, text in enumerate(texts):
        t = " ".join(text.lower().split())
        if not t:
            continue
        padded = f"^^{t}$$"
        counts: dict[int, float] = {}
        for k in range(len(padded) - 2):
            gram = padded[k:k + 3]
            h = int.from_bytes(hashlib.md5(gram.encode("utf-8")).digest()[:8],
                               "big")
            slot = h % dimension
            sign = 1.0 if (h >> 63) & 1 == 0 else -1.0
            counts[slot] = counts.get(slot, 0.0) + sign
            
        for slot, value in counts.items():
            out[i, slot] = value
            
    if normalize_l2:
        norms = np.linalg.norm(out, axis=1, keepdims=True)
        out = out / np.maximum(norms, 1e-12)
    return out

def lexical_overlap(a: str, b: str) -> float:
    """Jaccard overlap of lowercase token sets (sparse-retrieval signal)."""
    ta = set(a.lower().split())
    tb = set(b.lower().split())
    if not ta or not tb:
        return 0.0
    return len(ta & tb) / len(ta | tb)
