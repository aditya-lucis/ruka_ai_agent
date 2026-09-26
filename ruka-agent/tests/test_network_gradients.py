# -*- coding: utf-8 -*-
"""The lie-detector test: numerical gradient checking of MLP.backward.
If these tests fail, nothing else in the neural module matters — the
chain rule is wrong and every "training improvement" is noise.
"""
import numpy as np
import pytest

from src.ruka_cognition.neural.gradcheck import (check_gradients,
                                             numerical_gradient,
                                             relative_error)
from src.ruka_cognition.neural.losses import (bce_with_logits,
                                          bce_with_logits_backward,
                                          cce_with_logits,
                                          cce_with_logits_backward,
                                          mse, mse_backward)
from src.ruka_cognition.neural.network import MLP

def _gradient_is_wrong(network, x, y, loss_pair):
    """Shared harness: analytic backward vs central differences."""
    fwd, bwd = loss_pair
    report = check_gradients(
        network,
        loss_fn=lambda logits, targets: fwd(logits, targets),
        dloss_fn=lambda logits, targets: network.backward(
            bwd(logits, targets)),
        x=x, y=y, sample_per_param=24, tolerance=1e-6)
    return report

class TestGradientChecking:
    def test_mlp_relu_cce(self):
        rng = np.random.default_rng(0)
        net = MLP(12, 3, hidden=(8,), activation="relu", seed=1)
        x = rng.normal(size=(10, 12))
        y = rng.integers(0, 3, size=10)
        report = _gradient_is_wrong(net, x, y, (cce_with_logits,
                                                cce_with_logits_backward))
        assert report["passed"], f"max rel err {report['max_rel_error']:.2e}"
        assert report["max_rel_error"] < 1e-7

    def test_mlp_sigmoid_bce(self):
        rng = np.random.default_rng(1)
        net = MLP(9, 1, hidden=(), seed=2) # logistic unit
        x = rng.normal(size=(16, 9))
        y = (rng.random(16) > 0.5).astype(float).reshape(-1, 1)
        report = _gradient_is_wrong(net, x, y, (bce_with_logits,
                                                bce_with_logits_backward))
        assert report["passed"], f"max rel err {report['max_rel_error']:.2e}"

    def test_mlp_tanh_mse(self):
        rng = np.random.default_rng(2)
        net = MLP(7, 4, hidden=(10, 8), activation="tanh", seed=3)
        x = rng.normal(size=(12, 7)) * 0.5
        y = rng.normal(size=(12, 4)) * 0.5
        report = _gradient_is_wrong(net, x, y, (mse, mse_backward))
        assert report["passed"], f"max rel err {report['max_rel_error']:.2e}"

    def test_numerical_gradient_of_known_function(self):
        # f(w) = w^2 -> f'(3) = 6; the harness itself must be correct.
        w = np.array([3.0])
        num = numerical_gradient(lambda: float(w[0] ** 2), w,
                                 eps=1e-5, sample=None)
        assert num[0] == pytest.approx(6.0, rel=1e-4)

    def test_relative_error_zero_for_equal(self):
        a = np.array([1e-3, 2.0])
        assert np.allclose(relative_error(a, a.copy()), 0.0)

    def test_backward_before_forward_raises(self):
        net = MLP(4, 2, hidden=(4,))
        with pytest.raises(RuntimeError):
            net.layers[0].backward(np.zeros((1, 4)))
