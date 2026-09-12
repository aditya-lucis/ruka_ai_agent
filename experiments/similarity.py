import numpy as np

def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    """Kemiripan arah dua vektor; skala diabaikan.
    Args:
        a, b: vektor 1-D dengan panjang sama.
    Returns:
        Skalar di [-1, 1].
    Raises:
        ValueError: bila panjang beda atau salah satu vektor nol.
    """
    a = np.asarray(a, dtype=np.float64).ravel()
    b = np.asarray(b, dtype=np.float64).ravel()

    if a.shape != b.shape:
        raise ValueError(f"shape mismatch: {a.shape} vs {b.shape}")
    denom = np.linalg.norm(a) * np.linalg.norm(b)

    if denom == 0.0:
        raise ValueError("vektor nol tidak punya arah")
    return float(np.dot(a, b) / denom)

def batch_cosine(queries: np.ndarray, docs: np.ndarray) -> np.ndarray:
    """Skor cosine seluruh pasangan query-dokumen, tanpa loop.
    Args:
        queries: (q, d) — q vektor query dimensi d.
        docs: (N, d) — N vektor dokumen dimensi d.
    Returns:
        (q, N) matriks skor; skor[i, j] = cos(query_i, doc_j).
    """

    qn = queries / np.linalg.norm(queries, axis=1, keepdims=True)
    dn = docs / np.linalg.norm(docs, axis=1, keepdims=True)
    return qn @ dn.T # (q, d) @ (d, N)