import numpy as np
import pytest

from experiments.losses import bce

def test_bce_perfect_prediction():
    assert bce(1, 1.0) == pytest.approx(0.0, abs=1e-9)

def test_bce_never_nan_at_extremes():
    assert np.isfinite(bce(1, 0.0)) # clip menyelamatkan
    assert np.isfinite(bce(0, 1.0))

def test_bce_zero_at_correct_confident():
    assert bce(1, 0.999) < bce(1, 0.9) < bce(1, 0.5)