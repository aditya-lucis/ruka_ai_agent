# -*- coding: utf-8 -*-
"""Loss functions paired with their analytical gradients.
Convention: ``forward(logits_or_scores, targets) -> float`` and
``backward(...) -> dL/d(logits_or_scores)``. Classification losses eat
*logits* (unnormalized scores) — applying sigmoid/softmax before the
loss is the classic numerical-stability bug this design forbids.
"""
from __future__ import annotations
import numpy as np

def mse(y_pred: np.ndarray, y_true: np.ndarray) -> float:
    """Mean squared error over all elements."""
    d = y_pred - y_true
    return float((d * d).mean())

def mse_backward(y_pred: np.ndarray, y_true: np.ndarray) -> np.ndarray:
    n = y_pred.size
    return 2.0 * (y_pred - y_true) / max(n, 1)

def bce_with_logits(logits: np.ndarray, y_true: np.ndarray) -> float:
    """Binary cross-entropy computed from raw logits (stable form).
    L = -[y log s + (1-y) log(1-s)], s = sigmoid(z)
      = y * softplus(-z) + (1-y) * softplus(z)
    Splitting by label sign keeps every term a bounded softplus —
    no exp overflow for |z| large, and the perfect-prediction limit
    converges to 0 exactly as it must.
    """
    z, y = logits.astype(np.float64), y_true.astype(np.float64)
    loss = y * np.logaddexp(0.0, -z) + (1.0 - y) * np.logaddexp(0.0, z)
    return float(loss.mean())

def bce_with_logits_backward(logits: np.ndarray,
                             y_true: np.ndarray) -> np.ndarray:
    z, y = logits.astype(np.float64), y_true.astype(np.float64)
    s = 1.0 / (1.0 + np.exp(-z)) # sigmoid(z)
    return (s - y) / max(z.size, 1)

def cce_with_logits(logits: np.ndarray,
                    class_ids: np.ndarray) -> float:
    """Categorical cross-entropy from logits (stable softmax + NLL)."""
    z = logits.astype(np.float64)
    shifted = z - z.max(axis=-1, keepdims=True)
    log_probs = shifted - np.log(np.exp(shifted).sum(axis=-1, keepdims=True))
    n = z.shape[0]
    return float(-log_probs[np.arange(n), class_ids].mean())

def cce_with_logits_backward(logits: np.ndarray,
                             class_ids: np.ndarray) -> np.ndarray:
    """dL/dz = softmax(z) - one_hot(y) — the whole miracle fits one line."""
    z = logits.astype(np.float64)
    shifted = z - z.max(axis=-1, keepdims=True)
    e = np.exp(shifted)
    softmax = e / e.sum(axis=-1, keepdims=True)
    out = softmax.copy()
    n = z.shape[0]
    out[np.arange(n), class_ids] -= 1.0
    return out / n

LOSSES = {
    "mse": (mse, mse_backward),
    "bce": (bce_with_logits, bce_with_logits_backward),
    "cce": (cce_with_logits, cce_with_logits_backward),
}
