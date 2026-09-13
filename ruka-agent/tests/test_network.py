import numpy as np

import pytest
from experiments.network import TwoLayerNetwork

def test_output_shapes():
    net = TwoLayerNetwork()
    X = np.random.default_rng(0).normal(size=(5, 3))
    assert net.forward(X).shape == (5, 2)

def test_softmax_rows_sum_to_one():
    net = TwoLayerNetwork()
    X = np.random.default_rng(1).normal(size=(7, 3)) * 50 # skor ekstrem
    P = net.forward(X)
    assert np.allclose(P.sum(axis=1), 1.0)
    assert np.isfinite(P).all() # tidak ada nan/inf

def test_forward_deterministic():
    a = TwoLayerNetwork(seed=7).forward(np.ones((1, 3)))
    b = TwoLayerNetwork(seed=7).forward(np.ones((1, 3)))
    assert np.array_equal(a, b)