"""InfoNCE contrastive loss for Ruka Perception — multimodal module.

Implements Listing 8.1 from RUKA-IV Part VIII.
Symmetric InfoNCE (CLIP-style) + manual gradient with numerical gradient check.
"""

from __future__ import annotations

import numpy as np

from .attention import stable_softmax


# ---------------------------------------------------------------------------
# Listing 8.1 — InfoNCE + gradien manual (Part VIII)
# ---------------------------------------------------------------------------

def infonce_loss(
    sim: np.ndarray,
    temperature: float = 0.07,
) -> tuple[float, np.ndarray]:
    """Loss InfoNCE simetris ala CLIP + gradien terhadap sim.

    sim : (N, N) — diagonal = pasangan positif; lainnya negatif.
    Return: (loss skalar, dL/dsim (N, N)).

    Turunan manual (untuk pembelajaran — implementasi nyata pakai autograd):
    L_r = -(1/N) sum_i log p_ii, p = softmax(baris i dari sim/T).
    dL_r/dsim_ij = (p_ij - 1[i==j]) / (N*T).

    Dua bug nyata dari draf pertama (faktor 1/N hilang; transpose keliru
    pada suku kolom) tertangkap numerical gradient check — ditandai komentar.
    """
    if sim.ndim != 2 or sim.shape[0] != sim.shape[1]:
        raise ValueError("sim harus matriks persegi (N, N)")
    if temperature <= 0:
        raise ValueError("temperature harus > 0")
    n = sim.shape[0]
    logits = sim / temperature
    p = stable_softmax(logits, axis=1)               # (N, N)
    idx = np.arange(n)
    loss_rows = -np.log(np.clip(p[idx, idx], 1e-12, 1.0))
    grad = p.copy()
    grad[idx, idx] -= 1.0
    # Faktor 1/N wajib: L_r = -(1/N) sum log p_ii, z = sim/T,
    # sehingga dL/dsim_ij = (p_ij - delta_ij) / (N * T).
    # (Bug nyata yang ditangkap numerical gradient check test suite.)
    grad = grad / (temperature * n)                  # dL/dsim (baris)

    # Simetris: loss total = rata (baris + kolom) / 2 — seperti CLIP
    p_t = stable_softmax(logits, axis=0)
    loss_cols = -np.log(np.clip(p_t[idx, idx], 1e-12, 1.0))
    grad_t = p_t.copy()
    grad_t[idx, idx] -= 1.0
    # dL_c/dsim juga elementwise (TANPA transpose): softmax kolom
    # menghasilkan (p_t - I)/N pada posisi (i, j) yang sama.
    # (Transpose di sini = bug nyata kedua yang ditangkap gradcheck.)
    grad_t = grad_t / (temperature * n)              # dL/dsim (kolom)

    loss = float((loss_rows.mean() + loss_cols.mean()) / 2.0)
    return loss, (grad + grad_t) / 2.0


def collapse_diagnostic(sim: np.ndarray) -> dict:
    """Diagnosis kolaps ruang embedding.

    Tiga tanda kolaps: rata-rata similarity positif (diagonal),
    rata-rata negatif (off-diagonal), dan gap keduanya.
    gap ≈ 0 → kolaps / ruang curang (semua vektor sama).
    """
    if sim.ndim != 2 or sim.shape[0] != sim.shape[1]:
        raise ValueError("sim harus (N, N)")
    n = sim.shape[0]
    idx = np.arange(n)
    pos_sim = float(sim[idx, idx].mean())
    # Mask off-diagonal
    mask = np.ones_like(sim, dtype=bool)
    mask[idx, idx] = False
    neg_sim = float(sim[mask].mean()) if n > 1 else 0.0
    return {
        "pos_sim": pos_sim,
        "neg_sim": neg_sim,
        "gap": pos_sim - neg_sim,
        "collapsed": (pos_sim - neg_sim) < 0.05,
    }


def numerical_gradient_check(
    sim: np.ndarray,
    temperature: float = 0.07,
    eps: float = 1e-4,
    rtol: float = 1e-3,
) -> dict:
    """Verifikasi gradien analitik vs numerik (finite difference).

    Menguji 5 posisi acak dari matrix sim.
    Return: {'passed': bool, 'max_rel_err': float}
    """
    _, grad_analytical = infonce_loss(sim, temperature)
    np.random.seed(42)
    positions = [
        (int(i), int(j))
        for i, j in zip(
            np.random.randint(0, sim.shape[0], 5),
            np.random.randint(0, sim.shape[1], 5),
        )
    ]
    max_err = 0.0
    for i, j in positions:
        sim_plus = sim.copy(); sim_plus[i, j] += eps
        sim_minus = sim.copy(); sim_minus[i, j] -= eps
        loss_plus, _ = infonce_loss(sim_plus, temperature)
        loss_minus, _ = infonce_loss(sim_minus, temperature)
        grad_numerical = (loss_plus - loss_minus) / (2 * eps)
        grad_anal = grad_analytical[i, j]
        denom = max(abs(grad_numerical) + abs(grad_anal), 1e-8)
        rel_err = abs(grad_numerical - grad_anal) / denom
        max_err = max(max_err, rel_err)
    return {"passed": max_err <= rtol, "max_rel_err": float(max_err)}
