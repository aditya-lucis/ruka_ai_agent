# -*- coding: utf-8 -*-
"""MLP: a composition of Dense layers with forward/backward plumbing.
This is the engine Volume I sketched as an experiment and Volume III
builds as a component: typed layers, explicit caches, a backward()
that walks the chain rule backwards, and parameter access in a stable
order for optimizers and checkpointing.
"""
from __future__ import annotations
import numpy as np
from .layers import Dense

_DEFAULT_INIT = {"relu": "he", "tanh": "glorot", "sigmoid": "glorot",
                 "identity": "glorot"}

class MLP:
    """Multi-layer perceptron. ``hidden`` may be empty (logistic unit)."""
    def __init__(self, d_in: int, d_out: int,
                 hidden: tuple[int, ...] = (64,),
                 activation: str = "relu", seed: int = 0) -> None:
        if not hidden:
            sizes = [d_in, d_out]
            acts = ["identity"]
        else:
            sizes = [d_in, *hidden, d_out]
            acts = [activation] * len(hidden) + ["identity"]
            
        self.layers: list[Dense] = []
        rng = np.random.default_rng(seed)
        child = seed
        for i, (n_in, n_out) in enumerate(zip(sizes[:-1], sizes[1:])):
            child = int(rng.integers(0, 2**31 - 1))
            scale = _DEFAULT_INIT.get(acts[i], "glorot")
            self.layers.append(Dense(n_in, n_out, activation=acts[i],
                                     seed=child, weight_scale=scale))

    # ------------------------------------------------------------ API
    @property
    def params(self) -> list[np.ndarray]:
        return [p for layer in self.layers for p in layer.params]

    @property
    def grads(self) -> list[np.ndarray]:
        return [g for layer in self.layers for g in layer.grads]

    def forward(self, x: np.ndarray) -> np.ndarray:
        a = np.atleast_2d(np.asarray(x, dtype=np.float64))
        for layer in self.layers:
            a = layer.forward(a)
        return a # logits (no squash)

    def backward(self, d_logits: np.ndarray) -> None:
        grad = np.atleast_2d(np.asarray(d_logits, dtype=np.float64))
        for layer in reversed(self.layers):
            grad = layer.backward(grad)

    # ---------------------------------------------------- persistence
    def state_dict(self) -> dict:
        return {"shapes": [list(l.W.shape) for l in self.layers],
                "W": [l.W.copy() for l in self.layers],
                "b": [l.b.copy() for l in self.layers]}

    def load_state_dict(self, state: dict) -> None:
        if len(state["W"]) != len(self.layers):
            raise ValueError("checkpoint layer count mismatch")
        for layer, W, b in zip(self.layers, state["W"], state["b"]):
            if W.shape != layer.W.shape:
                raise ValueError(
                    f"checkpoint shape {W.shape} != layer {layer.W.shape}")
            layer.W = np.array(W, dtype=np.float64)
            layer.b = np.array(b, dtype=np.float64)
