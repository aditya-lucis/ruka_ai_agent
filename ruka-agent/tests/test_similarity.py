import numpy as np
import pytest
from experiments.similarity import cosine_similarity

def test_identical_vectors():
    v = np.array([1.0, 2.0, 3.0])
    assert cosine_similarity(v, v) == pytest.approx(1.0)

def test_orthogonal_vectors():
    a, b = np.array([1.0, 0.0]), np.array([0.0, 1.0])
    assert cosine_similarity(a, b) == pytest.approx(0.0)

def test_scale_invariance():
    a, b = np.array([1.0, 1.0]), np.array([5.0, 5.0])
    assert cosine_similarity(a, b) == pytest.approx(1.0)

def test_zero_vector_rejected():
    with pytest.raises(ValueError):
        cosine_similarity(np.zeros(3), np.ones(3))