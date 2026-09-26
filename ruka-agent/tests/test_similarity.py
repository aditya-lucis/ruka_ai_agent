# -*- coding: utf-8 -*-
"""Similarity kernels: mathematical invariants, not vibes."""
import numpy as np
import pytest

from src.ruka_cognition.vector.similarity import (cosine, cosine_to_distance,
                                              dot, euclidean, l2_norm,
                                              normalize)

class TestCosine:
    def test_identical_vectors_score_one(self):
        v = [1.0, 2.0, 3.0]
        assert cosine(v, v) == pytest.approx(1.0)
        
    def test_orthogonal_vectors_score_zero(self):
        assert cosine([1.0, 0.0], [0.0, 1.0]) == pytest.approx(0.0)
        
    def test_opposite_vectors_score_minus_one(self):
        assert cosine([2.0, 0.0], [-5.0, 0.0]) == pytest.approx(-1.0)
        
    def test_scale_invariance(self):
        a, b = [1.0, 2.0, 3.0], [4.0, 5.0, 6.0]
        assert cosine(a, b) == pytest.approx(cosine([10 * x for x in a],
                                                    [0.1 * x for x in b]))
                                                    
    def test_bounds_and_symmetry_batch(self):
        rng = np.random.default_rng(0)
        a = rng.normal(size=(16, 8))
        b = rng.normal(size=(16, 8))
        s = cosine(a, b)
        assert np.all(s <= 1.0 + 1e-9) and np.all(s >= -1.0 - 1e-9)
        assert np.allclose(s, cosine(b, a))
        
    def test_dimension_mismatch_raises(self):
        with pytest.raises(ValueError):
            cosine([1.0, 2.0], [1.0, 2.0, 3.0])

class TestNormalize:
    def test_unit_norm(self):
        rng = np.random.default_rng(1)
        m = normalize(rng.normal(size=(10, 5)) * 100.0)
        assert np.allclose(l2_norm(m), 1.0)
        
    def test_zero_vector_stays_zero(self):
        out = normalize([[0.0, 0.0, 0.0, 0.0]])
        assert np.allclose(out, 0.0)
        
    def test_cosine_equals_dot_on_normalized(self):
        rng = np.random.default_rng(2)
        a, b = rng.normal(size=(6, 7)), rng.normal(size=(6, 7))
        assert np.allclose(dot(normalize(a), normalize(b)), cosine(a, b))

class TestEuclidean:
    def test_known_distance(self):
        assert euclidean([0.0, 0.0], [3.0, 4.0]) == pytest.approx(5.0)
        
    def test_metric_property_random(self):
        """Triangle inequality on 200 random triples (the property
        cosine similarity itself lacks — the reason Part I converts)."""
        rng = np.random.default_rng(3)
        pts = rng.normal(size=(200, 3))
        d_ab = euclidean(pts[0], pts[1])
        d_bc = euclidean(pts[1], pts[2])
        d_ac = euclidean(pts[0], pts[2])
        assert np.all(d_ab + d_bc >= d_ac - 1e-9)

class TestCosineToDistance:
    def test_range_and_monotonic(self):
        sims = np.linspace(-1, 1, 9)
        d = cosine_to_distance(sims)
        assert d[0] == pytest.approx(2.0)    # s=-1 -> chord 2
        assert d[-1] == pytest.approx(0.0)   # s=+1 -> chord 0
        assert np.all(np.diff(d) <= 0)       # monotone decreasing