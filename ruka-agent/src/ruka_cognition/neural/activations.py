# -*- coding: utf-8 -*-
"""Activation functions and their exact derivatives.
Every activation is implemented as (forward, backward) pairs where
backward receives the *upstream gradient* and the *cached forward
output* (the "activation cache" trick) — never the input, because for
these functions the derivative is a function of the output alone.
"""
from __future__ import annotations
import numpy as np

def relu(z: np.ndarray) -> np.ndarray:
    """max(0, z). Non-saturating for z > 0; dead for z < 0."""
    return np.maximum(0.0, z)

def relu_backward(upstream: np.ndarray, out: np.ndarray) -> np.ndarray:
    return upstream * (out > 0.0)

def sigmoid(z: np.ndarray) -> np.ndarray:
    """Numerically stable logistic function."""
    out = np.empty_like(z, dtype=np.float64)
    pos = z >= 0
    out[pos] = 1.0 / (1.0 + np.exp(-z[pos]))
    ez = np.exp(z[~pos])
    out[~pos] = ez / (1.0 + ez)
    return out

def sigmoid_backward(upstream: np.ndarray, out: np.ndarray) -> np.ndarray:
    return upstream * out * (1.0 - out)

def tanh(z: np.ndarray) -> np.ndarray:
    return np.tanh(z)

def tanh_backward(upstream: np.ndarray, out: np.ndarray) -> np.ndarray:
    return upstream * (1.0 - out * out)

def softmax(z: np.ndarray) -> np.ndarray:
    """Row-wise softmax with the max-subtraction stability trick."""
    shifted = z - z.max(axis=-1, keepdims=True)
    e = np.exp(shifted)
    return e / e.sum(axis=-1, keepdims=True)

ACTIVATIONS = {
    "relu": (relu, relu_backward),
    "sigmoid": (sigmoid, sigmoid_backward),
    "tanh": (tanh, tanh_backward),
    "identity": (lambda z: z, lambda up, out: up),
}
