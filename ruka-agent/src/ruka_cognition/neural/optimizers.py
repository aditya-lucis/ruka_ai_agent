# -*- coding: utf-8 -*-
"""Optimizers: SGD, SGD + Momentum, Adam.
All optimizers share one interface so the Trainer never branches on
optimizer type: ``step(params, grads)`` mutates params in place, and
``zero_grad`` semantics are owned by the trainer, not the optimizer.
Adam formulas (Kingma & Ba, 2015):
 m_t = beta1*m_{t-1} + (1-beta1)*g
 v_t = beta2*v_{t-1} + (1-beta2)*g^2
 m_hat = m_t / (1-beta1^t)           v_hat = v_t / (1-beta2^t)
 theta_t = theta_{t-1} - lr * m_hat / (sqrt(v_hat) + eps)
The bias correction terms matter on step 1 — without them the very
first update is scaled by lr/(1-beta1) silently.
"""
from __future__ import annotations
import numpy as np

def clip_by_global_norm(grads: list[np.ndarray],
                        max_norm: float) -> float:
    """Rescale all gradients jointly so ||g||_2 <= max_norm.
    Returns the pre-clip global norm (a vanishing/exploding detector:
    log it). When the norm is finite and under the cap this is a no-op,
    so it is safe to call on every step.
    """
    if max_norm <= 0:
        raise ValueError("max_norm must be positive")
    total = float(np.sqrt(sum(float((g * g).sum()) for g in grads)))
    if total > max_norm and np.isfinite(total):
        scale = max_norm / (total + 1e-12)
        for g in grads:
            g *= scale
    return total

class SGD:
    """Plain stochastic gradient descent with L2 weight decay."""
    def __init__(self, lr: float = 0.05, weight_decay: float = 0.0) -> None:
        if lr <= 0:
            raise ValueError("lr must be positive")
        self.lr = float(lr)
        self.weight_decay = float(weight_decay)

    def step(self, params: list[np.ndarray],
             grads: list[np.ndarray]) -> None:
        for p, g in zip(params, grads):
            update = g + self.weight_decay * p
            p -= self.lr * update

class Momentum:
    """SGD with classical momentum: v = mu*v - lr*g; p += v."""
    def __init__(self, lr: float = 0.05, mu: float = 0.9,
                 weight_decay: float = 0.0) -> None:
        self.lr, self.mu = float(lr), float(mu)
        self.weight_decay = float(weight_decay)
        self._v: list[np.ndarray] | None = None

    def step(self, params: list[np.ndarray],
             grads: list[np.ndarray]) -> None:
        if self._v is None:
            self._v = [np.zeros_like(p) for p in params]
        for p, g, v in zip(params, grads, self._v):
            v *= self.mu
            v -= self.lr * (g + self.weight_decay * p)
            p += v

class Adam:
    """Adam with bias-corrected first and second moments."""
    def __init__(self, lr: float = 0.01, beta1: float = 0.9,
                 beta2: float = 0.999, eps: float = 1e-8,
                 weight_decay: float = 0.0) -> None:
        self.lr, self.beta1, self.beta2 = float(lr), float(beta1), float(beta2)
        self.eps, self.weight_decay = float(eps), float(weight_decay)
        self._m: list[np.ndarray] | None = None
        self._v: list[np.ndarray] | None = None
        self._t = 0

    def _init_state(self, params: list[np.ndarray]) -> None:
        self._m = [np.zeros_like(p) for p in params]
        self._v = [np.zeros_like(p) for p in params]
        self._shapes = [p.shape for p in params]

    def _validate(self, params: list[np.ndarray]) -> None:
        """A silent no-op on a signature change is a training bug —
        refuse instead of zip-truncating."""
        if self._m is None:
            return
        if len(params) != len(self._m):
            raise ValueError(
                f"params signature changed: {len(params)} tensors "
                f"vs optimizer state {len(self._m)} — reset the optimizer")
        for p, s in zip(params, self._shapes):
            if p.shape != s:
                raise ValueError(
                    f"param shape changed {p.shape} vs state {s} — "
                    f"reset the optimizer")

    def step(self, params: list[np.ndarray],
             grads: list[np.ndarray]) -> None:
        if self._m is None:
            self._init_state(params)
        else:
            self._validate(params)
            
        self._t += 1
        b1c = 1.0 - self.beta1 ** self._t
        b2c = 1.0 - self.beta2 ** self._t
        
        for p, g, m, v in zip(params, grads, self._m, self._v):
            if self.weight_decay:
                g = g + self.weight_decay * p
            
            m *= self.beta1
            m += (1.0 - self.beta1) * g
            
            v *= self.beta2
            v += (1.0 - self.beta2) * (g * g)
            
            m_hat = m / b1c
            v_hat = v / b2c
            
            p -= self.lr * m_hat / (np.sqrt(v_hat) + self.eps)
