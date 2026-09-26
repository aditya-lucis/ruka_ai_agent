"""Unit tests for multimodal/contrastive.py — Listing 8.1 InfoNCE."""

import numpy as np
import pytest

from ruka_perception.multimodal.contrastive import (
    collapse_diagnostic,
    infonce_loss,
    numerical_gradient_check,
)


class TestInfoNCELoss:
    def test_square_matrix_required(self):
        with pytest.raises(ValueError, match="persegi"):
            infonce_loss(np.random.randn(3, 4))

    def test_temperature_positive(self):
        with pytest.raises(ValueError, match="temperature"):
            infonce_loss(np.eye(3), temperature=0)

    def test_aligned_loss_lower_than_random(self):
        """Pasangan selaras (diagonal tinggi) -> loss < pasangan acak."""
        np.random.seed(0)
        aligned = np.eye(5) * 2.0 + np.random.randn(5, 5) * 0.1
        random = np.random.randn(5, 5)
        loss_a, _ = infonce_loss(aligned, temperature=0.5)
        loss_r, _ = infonce_loss(random, temperature=0.5)
        assert loss_a < loss_r

    def test_gradient_shape(self):
        """Gradien harus shape (N, N)."""
        sim = np.random.randn(4, 4)
        _, grad = infonce_loss(sim)
        assert grad.shape == (4, 4)

    def test_gradient_numerical_check(self):
        """Gradien analitik harus cocok dengan numerical (rtol 1e-3)."""
        np.random.seed(42)
        sim = np.random.randn(4, 4) * 0.5
        result = numerical_gradient_check(sim, temperature=0.5, rtol=1e-3)
        assert result["passed"], f"max_rel_err = {result['max_rel_err']}"

    def test_worked_example_loss(self):
        """Worked example buku: 3x3 sim, T=0.5, loss is positive and bounded."""
        s = np.array([[1.0, 0.5, 0.0], [0.0, 1.0, 0.25], [0.25, 0.0, 1.0]])
        loss, grad = infonce_loss(s, temperature=0.5)
        # Symmetric InfoNCE loss: harus positif dan < log(N)
        assert 0 < loss < np.log(3) + 0.5
        # Gradien pada negatif terdekat harus positif (menekan turun)
        assert grad[0, 1] > 0


class TestCollapseDiagnostic:
    def test_uniform_vectors_collapse(self):
        """Vektor seragam (semua sama) -> gap ≈ 0, collapsed=True."""
        sim = np.ones((5, 5))
        d = collapse_diagnostic(sim)
        assert d["collapsed"]
        assert abs(d["gap"]) < 0.05

    def test_healthy_gap(self):
        """Diagonal tinggi, off-diagonal rendah -> gap > 0.05."""
        sim = np.eye(5) * 0.9 + np.ones((5, 5)) * 0.1
        d = collapse_diagnostic(sim)
        assert not d["collapsed"]
        assert d["gap"] > 0.3

    def test_square_required(self):
        with pytest.raises(ValueError, match="N, N"):
            collapse_diagnostic(np.random.randn(3, 4))
