"""Tests for RUKA VI Linear Algebra Invariants (Part III & XXV).
Strictly verifies:
- Cosine similarity: symmetry, Cauchy-Schwarz, scale invariance, self-similarity, orthogonality, zero/dim rejection
- Norms: homogeneity, positivity, triangle inequality
- Euclidean distance: metric axioms (identity, symmetry, triangle inequality)
- Projection: residual orthogonality, idempotence
- PCA & SVD: component orthogonality, reconstruction monotonicity, variance ordering
"""

import numpy as np
import pytest

from ruka_companion.math.linalg import (
    cosine_similarity,
    euclidean_distance,
    normalize_unit,
    project,
    pca,
    pca_reconstruct,
    rank,
    l2_norm,
)

RNG = np.random.default_rng(20260910)


class TestCosineSimilarity:
    def test_symmetry(self):
        for _ in range(50):
            x, y = RNG.normal(size=8), RNG.normal(size=8)
            assert cosine_similarity(x, y) == pytest.approx(
                cosine_similarity(y, x), abs=1e-12
            )

    def test_cauchy_schwarz(self):
        for _ in range(50):
            x, y = RNG.normal(size=16), RNG.normal(size=16)
            assert abs(cosine_similarity(x, y)) <= 1.0 + 1e-12

    def test_scale_invariance_positive(self):
        x, y = RNG.normal(size=10), RNG.normal(size=10)
        assert cosine_similarity(x, 3.7 * y) == pytest.approx(
            cosine_similarity(x, y), abs=1e-9
        )

    def test_self_is_one(self):
        x = RNG.normal(size=12)
        assert cosine_similarity(x, x) == pytest.approx(1.0, abs=1e-12)

    def test_orthogonal_is_zero(self):
        assert cosine_similarity([1, 0], [0, 1]) == pytest.approx(0.0, abs=1e-12)

    def test_opposite_is_minus_one(self):
        x = RNG.normal(size=8)
        assert cosine_similarity(x, -x) == pytest.approx(-1.0, abs=1e-12)

    def test_zero_vector_rejected(self):
        with pytest.raises(ValueError):
            cosine_similarity([0, 0, 0], [1, 2, 3])

    def test_dim_mismatch_rejected(self):
        with pytest.raises(ValueError):
            cosine_similarity([1, 2], [1, 2, 3])


class TestNorms:
    def test_homogeneity(self):
        x = RNG.normal(size=10)
        assert l2_norm(2.5 * x) == pytest.approx(2.5 * l2_norm(x), rel=1e-12)

    def test_positivity(self):
        x = RNG.normal(size=10)
        assert l2_norm(x) > 0.0

    def test_triangle_inequality(self):
        for _ in range(50):
            x, y = RNG.normal(size=8), RNG.normal(size=8)
            assert l2_norm(x + y) <= l2_norm(x) + l2_norm(y) + 1e-12

    def test_zero_norm(self):
        assert l2_norm([0, 0, 0]) == 0.0


class TestEuclideanDistance:
    def test_symmetry(self):
        for _ in range(30):
            x, y = RNG.normal(size=8), RNG.normal(size=8)
            assert euclidean_distance(x, y) == pytest.approx(
                euclidean_distance(y, x), abs=1e-12
            )

    def test_identity_of_indiscernibles(self):
        x = RNG.normal(size=10)
        assert euclidean_distance(x, x) == pytest.approx(0.0, abs=1e-12)

    def test_triangle_inequality(self):
        for _ in range(30):
            x, y, z = RNG.normal(size=8), RNG.normal(size=8), RNG.normal(size=8)
            d_xy = euclidean_distance(x, y)
            d_yz = euclidean_distance(y, z)
            d_xz = euclidean_distance(x, z)
            assert d_xz <= d_xy + d_yz + 1e-12


class TestNormalizeUnit:
    def test_unit_length(self):
        for _ in range(30):
            x = RNG.normal(size=16)
            u = normalize_unit(x)
            assert l2_norm(u) == pytest.approx(1.0, abs=1e-12)

    def test_direction_preserved(self):
        x = RNG.normal(size=8)
        u = normalize_unit(x)
        assert cosine_similarity(x, u) == pytest.approx(1.0, abs=1e-12)

    def test_zero_vector_rejected(self):
        with pytest.raises(ValueError):
            normalize_unit(np.zeros(5))


class TestProjection:
    def test_residual_orthogonality(self):
        for _ in range(30):
            x = RNG.normal(size=6)
            u = RNG.normal(size=6)
            p = project(x, u)
            residual = x - p
            # residual harus tegak lurus dengan arah u
            assert np.dot(residual, u) == pytest.approx(0.0, abs=1e-11)

    def test_idempotence(self):
        x = RNG.normal(size=6)
        u = RNG.normal(size=6)
        p1 = project(x, u)
        p2 = project(p1, u)
        assert np.allclose(p1, p2, atol=1e-12)

    def test_zero_u_rejected(self):
        with pytest.raises(ValueError):
            project([1, 2], [0, 0])


class TestPCAAndRank:
    def test_component_orthonormality(self):
        X = RNG.normal(size=(20, 8))
        res = pca(X, k=4)
        Vk = res["components"]  # 8 x 4
        # Vk^T @ Vk = I_4
        assert np.allclose(Vk.T @ Vk, np.eye(4), atol=1e-11)

    def test_explained_variance_descending(self):
        X = RNG.normal(size=(30, 10))
        res = pca(X, k=5)
        ev = res["explained_variance"]
        for i in range(len(ev) - 1):
            assert ev[i] >= ev[i + 1] - 1e-12

    def test_reconstruction_monotonicity(self):
        X = RNG.normal(size=(20, 8))
        err1 = np.linalg.norm(X - pca_reconstruct(X, k=2))
        err2 = np.linalg.norm(X - pca_reconstruct(X, k=4))
        err3 = np.linalg.norm(X - pca_reconstruct(X, k=6))
        # Lebih banyak komponen -> error rekonstruksi lebih kecil
        assert err1 >= err2 - 1e-9
        assert err2 >= err3 - 1e-9

    def test_rank_identity(self):
        I5 = np.eye(5)
        assert rank(I5) == 5

    def test_rank_outer_product_is_one(self):
        u = RNG.normal(size=8)
        v = RNG.normal(size=6)
        A = np.outer(u, v)
        assert rank(A) == 1


# ============================================================ Extended Tests
class TestCosineSimilarityExtended:
    """Additional cosine invariants from Part III/XXV."""

    def test_anticommutative_with_negation(self):
        x, y = RNG.normal(size=8), RNG.normal(size=8)
        assert cosine_similarity(x, -y) == pytest.approx(
            -cosine_similarity(x, y), abs=1e-12
        )

    def test_scale_invariance_negative(self):
        x, y = RNG.normal(size=10), RNG.normal(size=10)
        assert cosine_similarity(-2.0 * x, y) == pytest.approx(
            -cosine_similarity(x, y), abs=1e-9
        )

    def test_identical_vectors_many_dims(self):
        for d in [2, 4, 8, 16, 32, 64, 128]:
            x = RNG.normal(size=d)
            assert cosine_similarity(x, x) == pytest.approx(1.0, abs=1e-12)

    def test_batch_cauchy_schwarz(self):
        for _ in range(100):
            x, y = RNG.normal(size=32), RNG.normal(size=32)
            assert abs(cosine_similarity(x, y)) <= 1.0 + 1e-12

    def test_perpendicular_3d(self):
        assert cosine_similarity([1, 0, 0], [0, 1, 0]) == pytest.approx(0.0, abs=1e-12)
        assert cosine_similarity([1, 0, 0], [0, 0, 1]) == pytest.approx(0.0, abs=1e-12)


class TestNormsExtended:
    def test_unit_vector_norm_is_one(self):
        x = RNG.normal(size=10)
        u = normalize_unit(x)
        assert l2_norm(u) == pytest.approx(1.0, abs=1e-12)

    def test_norm_nonneg(self):
        for _ in range(30):
            x = RNG.normal(size=16)
            assert l2_norm(x) >= 0.0

    def test_scalar_multiplication(self):
        x = RNG.normal(size=8)
        alpha = -3.14
        assert l2_norm(alpha * x) == pytest.approx(abs(alpha) * l2_norm(x), abs=1e-12)


class TestEuclideanDistanceExtended:
    def test_non_negativity(self):
        for _ in range(30):
            x, y = RNG.normal(size=8), RNG.normal(size=8)
            assert euclidean_distance(x, y) >= -1e-12

    def test_distance_to_self_is_zero(self):
        for _ in range(10):
            x = RNG.normal(size=16)
            assert euclidean_distance(x, x) == pytest.approx(0.0, abs=1e-12)

    def test_distance_dim_mismatch(self):
        with pytest.raises(ValueError):
            euclidean_distance([1, 2, 3], [4, 5])

    def test_agrees_with_norm(self):
        x, y = RNG.normal(size=12), RNG.normal(size=12)
        assert euclidean_distance(x, y) == pytest.approx(l2_norm(x - y), abs=1e-12)


class TestProjectionExtended:
    def test_project_onto_self_is_self(self):
        x = RNG.normal(size=8)
        p = project(x, x)
        assert np.allclose(p, x, atol=1e-12)

    def test_project_orthogonal_is_zero(self):
        p = project([1, 0], [0, 1])
        assert np.allclose(p, [0, 0], atol=1e-12)

    def test_projection_length_bounded(self):
        for _ in range(30):
            x = RNG.normal(size=8)
            u = RNG.normal(size=8)
            p = project(x, u)
            assert l2_norm(p) <= l2_norm(x) + 1e-10

    def test_dim_mismatch_rejected(self):
        with pytest.raises(ValueError):
            project([1, 2, 3], [4, 5])


class TestPCAExtended:
    def test_mean_centering(self):
        X = RNG.normal(size=(30, 8))
        res = pca(X, k=3)
        mu = res["mean"]
        assert mu.shape == (8,)
        assert np.allclose(mu, X.mean(axis=0), atol=1e-12)

    def test_k_equals_d_perfect_reconstruction(self):
        X = RNG.normal(size=(15, 5))
        Xhat = pca_reconstruct(X, k=5)
        assert np.allclose(X, Xhat, atol=1e-10)

    def test_explained_ratio_nonnegative(self):
        X = RNG.normal(size=(20, 6))
        res = pca(X, k=6)
        for r in res["explained_ratio"]:
            assert r >= -1e-12

    def test_invalid_k_rejected(self):
        X = RNG.normal(size=(10, 5))
        with pytest.raises(ValueError):
            pca(X, k=0)
        with pytest.raises(ValueError):
            pca(X, k=6)

    def test_more_components_explains_more_variance(self):
        X = RNG.normal(size=(30, 6))
        res1 = pca(X, k=1)
        res3 = pca(X, k=3)
        assert sum(res3["explained_variance"]) >= sum(res1["explained_variance"]) - 1e-12


class TestRankExtended:
    def test_rank_zero_matrix(self):
        assert rank(np.zeros((3, 3))) == 0

    def test_rank_full_random(self):
        A = RNG.normal(size=(5, 5))
        assert rank(A) == 5

    def test_rank_submatrix_le_parent(self):
        A = RNG.normal(size=(6, 4))
        r = rank(A)
        assert r <= min(6, 4)

    def test_rank_transpose_invariant(self):
        A = RNG.normal(size=(5, 8))
        assert rank(A) == rank(A.T)

    def test_rank_1d_rejected(self):
        with pytest.raises(ValueError):
            rank(np.array([1, 2, 3]))


class TestNormalizeUnitExtended:
    def test_double_normalize_idempotent(self):
        x = RNG.normal(size=10)
        u = normalize_unit(x)
        u2 = normalize_unit(u)
        assert np.allclose(u, u2, atol=1e-12)

    def test_collinear_same_direction(self):
        x = RNG.normal(size=8)
        assert np.allclose(normalize_unit(x), normalize_unit(3.0 * x), atol=1e-12)

    def test_negative_scale_reverses(self):
        x = RNG.normal(size=8)
        u_pos = normalize_unit(x)
        u_neg = normalize_unit(-x)
        assert np.allclose(u_pos, -u_neg, atol=1e-12)

