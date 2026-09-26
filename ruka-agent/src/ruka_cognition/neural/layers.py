# -*- coding: utf-8 -*-
"""Dense layer: forward pass, backward pass, parameter ownership.
Shape contract used across the whole neural module (batch-first):
 x : (B, d_in)       W : (d_in, d_out)      b : (d_out,)
 z = xW + b          a = act(z)             a : (B, d_out)
Backward (the chain rule instantiated):
 dW = x^T @ dA       db = sum_B(dA)         dX = dA @ W^T
The layer caches exactly what backprop needs and nothing else, which
keeps memory proportional to activations, not to the batch history.
"""
from __future__ import annotations
import numpy as np
from .activations import ACTIVATIONS

class Dense:
    """Fully connected layer with He/Glorot-aware init and L2 support."""
    def __init__(self, d_in: int, d_out: int, activation: str = "relu",
                 seed: int | None = None, weight_scale: str = "he") -> None:
        if d_in <= 0 or d_out <= 0:
            raise ValueError("dimensions must be positive")
        if activation not in ACTIVATIONS:
            raise ValueError(f"unknown activation {activation!r}")
        rng = np.random.default_rng(seed)
        if weight_scale == "he":
            std = np.sqrt(2.0 / d_in) # keeps ReLU variance alive
        elif weight_scale == "glorot":
            std = np.sqrt(2.0 / (d_in + d_out)) # keeps tanh/sigmoid stable
        else:
            raise ValueError(f"unknown weight_scale {weight_scale!r}")
        self.W = rng.normal(0.0, std, size=(d_in, d_out))
        self.b = np.zeros(d_out, dtype=np.float64)
        self.activation = activation
        self._fwd, self._bwd = ACTIVATIONS[activation]
        
        # caches (valid between forward and the next forward)
        self._x: np.ndarray | None = None
        self._a: np.ndarray | None = None
        
        # gradient slots (filled by backward)
        self.dW = np.zeros_like(self.W)
        self.db = np.zeros_like(self.b)

    # ------------------------------------------------------------ API
    @property
    def params(self) -> list[np.ndarray]:
        return [self.W, self.b]

    @property
    def grads(self) -> list[np.ndarray]:
        return [self.dW, self.db]

    def forward(self, x: np.ndarray) -> np.ndarray:
        x = np.atleast_2d(np.asarray(x, dtype=np.float64))
        if x.shape[1] != self.W.shape[0]:
            raise ValueError(f"input dim {x.shape[1]} != layer dim {self.W.shape[0]}")
        z = x @ self.W + self.b
        a = self._fwd(z)
        self._x, self._a = x, a
        return a

    def backward(self, d_a: np.ndarray) -> np.ndarray:
        if self._x is None or self._a is None:
            raise RuntimeError("backward called before forward")
        d_a = np.atleast_2d(np.asarray(d_a, dtype=np.float64))
        d_z = self._bwd(d_a, self._a)
        self.dW = self._x.T @ d_z
        self.db = d_z.sum(axis=0)
        return d_z @ self.W.T
