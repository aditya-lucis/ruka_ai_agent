"""Attention mechanisms for Ruka Perception — multimodal module.

Implements Listings 2.1, 3.1, 4.1 (Part II-IV) and 7.1, 7.2 (Part VII) from RUKA-IV.

Listing 2.1 — shape validation on attention gate
Listing 3.1 — numerically stable softmax + temperature
Listing 4.1 — attention entropy (normalized)
Listing 7.1 — scaled dot-product attention
Listing 7.2 — cross-modal attention (text queries image)
"""

from __future__ import annotations

import numpy as np


# ---------------------------------------------------------------------------
# Listing 3.1 — Softmax stabil + temperature (Part III)
# ---------------------------------------------------------------------------

def stable_softmax(x: np.ndarray, axis: int = -1, temperature: float = 1.0) -> np.ndarray:
    """Numerically-stable softmax dengan temperature scaling.

    Stability trick: kurangi max per baris sebelum exp — overflow dicegah,
    hasil identik secara matematis.
    Temperature T > 1 meratakan distribusi (lebih seragam);
    T < 1 mempertajam distribusi (lebih one-hot).
    """
    if temperature <= 0:
        raise ValueError(f"temperature harus > 0, dapat {temperature}")
    z = x / temperature
    z = z - np.max(z, axis=axis, keepdims=True)  # stabilitas numerik
    e = np.exp(z)
    return e / np.sum(e, axis=axis, keepdims=True)


# ---------------------------------------------------------------------------
# Listing 4.1 — Entropi attention ternormalisasi (Part IV)
# ---------------------------------------------------------------------------

def attention_entropy(weights: np.ndarray) -> np.ndarray:
    """Entropi per baris attention weight matrix.

    H(baris_i) = -Σ_j w_ij log(w_ij), dinormalkan ke [0,1] dengan log(n_k).
    Nilai tinggi = distribusi merata (tidak fokus).
    Nilai rendah = perhatian terkonsentrasi pada satu token.
    Berguna untuk diagnosis: mask kausal menghasilkan entropi rendah di baris awal.
    """
    if weights.ndim != 2:
        raise ValueError(f"weights harus (n_q, n_k) 2-D, dapat {weights.shape}")
    n_k = weights.shape[1]
    eps = 1e-12
    raw = -np.sum(weights * np.log(np.clip(weights, eps, 1.0)), axis=-1)
    max_entropy = np.log(n_k) if n_k > 1 else 1.0
    return raw / max_entropy


# ---------------------------------------------------------------------------
# Listing 2.1 / 7.1 — Scaled dot-product attention (Part II + Part VII)
# ---------------------------------------------------------------------------

def scaled_dot_product_attention(
    q: np.ndarray,
    k: np.ndarray,
    v: np.ndarray,
    mask: np.ndarray | None = None,
    temperature: float = 1.0,
) -> tuple[np.ndarray, np.ndarray]:
    """Attention inti. Return (output (n_q, d_v), bobot (n_q, n_k)).

    mask (n_q, n_k): 1 = boleh dilihat, 0 = diblok. Posisi 0 diberi
    skor -inf SEBELUM softmax sehingga bobotnya tepat nol.

    Validasi bentuk (Listing 2.1): dua kesalahan paling sering diangkat
    menjadi ValueError dengan angka nyata, bukan TypeError samar dari NumPy.
    """
    if q.ndim != 2 or k.ndim != 2 or v.ndim != 2:
        raise ValueError("Q, K, V harus 2-D")
    n_q, d_k = q.shape
    n_k, d_k2 = k.shape
    n_k2, d_v = v.shape
    if d_k != d_k2:
        raise ValueError(
            f"dimensi d_k Q ({d_k}) != K ({d_k2}) — QK^T tak terdefinisi"
        )
    if n_k != n_k2:
        raise ValueError(
            f"jumlah token K ({n_k}) != V ({n_k2}) — pasangan K,V lepas"
        )
    scores = q @ k.T / np.sqrt(d_k)             # (n_q, n_k)
    if mask is not None:
        if mask.shape != (n_q, n_k):
            raise ValueError(f"mask {mask.shape} != {(n_q, n_k)}")
        scores = np.where(mask > 0, scores, -np.inf)
    weights = stable_softmax(scores, axis=-1, temperature=temperature)
    output = weights @ v                         # (n_q, d_v)
    return output, weights


def causal_mask(n: int) -> np.ndarray:
    """Buat causal mask (n, n): segitiga bawah 1, atas 0.

    Token ke-t hanya boleh melihat posisi 0..t.
    Test invarian: segitiga atas weights == 0.0 setelah attention.
    """
    return np.tril(np.ones((n, n), dtype=np.float32))


# ---------------------------------------------------------------------------
# Listing 7.2 — Cross-modal attention: teks bertanya, gambar menjawab (Part VII)
# ---------------------------------------------------------------------------

def cross_modal_attention(
    text_repr: np.ndarray,
    image_repr: np.ndarray,
    temperature: float = 1.0,
) -> tuple[np.ndarray, np.ndarray]:
    """Text attends to Image: teks bertanya, patch gambar menjawab.

    text_repr  : (n_text, d) — token teks (embedding prompt)
    image_repr : (n_patch, d) — token patch gambar (patch embedding)
    Return: konteks (n_text, d), peta perhatian (n_text, n_patch).

    Di implementasi nyata d_v boleh != d; versi ini menyatukan d —
    bagian fusion membahas konsekuensi desain itu.
    """
    if text_repr.ndim != 2 or image_repr.ndim != 2:
        raise ValueError("representasi harus (token, dim)")
    if text_repr.shape[1] != image_repr.shape[1]:
        raise ValueError(
            f"dimensi tak cocok: teks {text_repr.shape[1]}, "
            f"gambar {image_repr.shape[1]} — butuh proyeksi dulu"
        )
    scores = text_repr @ image_repr.T / np.sqrt(text_repr.shape[1])
    scores = scores / temperature
    weights = stable_softmax(scores, axis=-1)
    context = weights @ image_repr
    return context, weights
