# -*- coding: utf-8 -*-
"""Numerical gradient checking — the lie detector of backprop.
Central-difference approximation for parameter theta_j:
 dL/dtheta_j ~= [L(theta + eps) - L(theta - eps)] / (2*eps)
The check compares this against the analytic gradient from
``network.backward``. Any mismatch beyond tolerance means the hand
written chain rule is wrong — this test has caught every real
backprop bug in this package and it will catch yours.
Numerical care:
- eps = 1e-5 (float64) balances truncation vs rounding error;
- we perturb a *random sample* of coordinates by default (full check
  is O(P) forward passes — fine for thousands of params, not millions);
- relative error is reported, not absolute, so scale does not lie.
"""
from __future__ import annotations
import numpy as np

def numerical_gradient(loss_fn, param: np.ndarray,
                       eps: float = 1e-5,
                       sample: int | None = 32,
                       seed: int = 0) -> np.ndarray:
    """Estimate dL/dparam by central differences (in-place safe)."""
    if param.size == 0:
        return np.zeros_like(param)
    rng = np.random.default_rng(seed)
    if sample is None or sample >= param.size:
        flat_idx = np.arange(param.size)
    else:
        flat_idx = np.sort(rng.choice(param.size, size=sample, replace=False))
        
    num = np.zeros_like(param, dtype=np.float64)
    flat = param.reshape(-1)
    num_flat = num.reshape(-1)
    
    for j in flat_idx:
        orig = flat[j]
        
        flat[j] = orig + eps
        lp = loss_fn()
        
        flat[j] = orig - eps
        lm = loss_fn()
        
        flat[j] = orig  # restore exactly
        num_flat[j] = (lp - lm) / (2.0 * eps)
        
    return num

def relative_error(analytic: np.ndarray, numeric: np.ndarray,
                   eps: float = 1e-8) -> np.ndarray:
    """Elementwise |a - n| / max(|a|, |n|, eps) — dimensionless error."""
    a, n = np.abs(analytic), np.abs(numeric)
    return np.abs(a - n) / np.maximum(np.maximum(a, n), eps)

def check_gradients(network, loss_fn, dloss_fn, x: np.ndarray, y: np.ndarray,
                    sample_per_param: int = 32, tolerance: float = 1e-6,
                    seed: int = 0) -> dict:
    """Full check: forward+backward, then numeric comparison.
    ``loss_fn(network)`` and ``dloss_fn(network)`` are supplied by the
    caller so the same harness works for BCE, CCE, and MSE targets.
    Returns a report dict; ``passed`` is True when the max relative
    error over sampled coordinates stays under ``tolerance``.
    """
    logits = network.forward(x)
    dloss_fn(logits, y) # populate grads via backward
    analytic = [g.copy() for g in network.grads]
    
    report = {"per_layer": [], "passed": True, "max_rel_error": 0.0}
    
    def scalar_loss() -> float:
        return loss_fn(network.forward(x), y)
        
    for li, (param, grad) in enumerate(zip(network.params, analytic)):
        num = numerical_gradient(scalar_loss, param,
                                 sample=sample_per_param, seed=seed + li)
        
        mask = num != 0.0
        if not mask.any():
            continue
            
        rel = relative_error(grad.reshape(-1)[np.flatnonzero(mask)],
                             num.reshape(-1)[np.flatnonzero(mask)])
        max_rel = float(rel.max()) if rel.size else 0.0
        
        report["per_layer"].append({"layer": li, "max_rel_error": max_rel})
        report["max_rel_error"] = max(report["max_rel_error"], max_rel)
        if max_rel > tolerance:
            report["passed"] = False
            
    return report
