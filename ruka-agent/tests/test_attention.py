"""Unit tests for multimodal/attention.py — Listings 2.1, 3.1, 4.1, 7.1, 7.2."""

import numpy as np
import pytest

from ruka_perception.multimodal.attention import (
    attention_entropy,
    causal_mask,
    cross_modal_attention,
    scaled_dot_product_attention,
    stable_softmax,
)


class TestStableSoftmax:
    def test_rows_sum_to_one(self):
        """Setiap baris softmax harus Σ=1."""
        x = np.random.randn(4, 8)
        p = stable_softmax(x, axis=-1)
        np.testing.assert_allclose(p.sum(axis=-1), 1.0, atol=1e-7)

    def test_stability_extreme_values(self):
        """Softmax harus stabil pada input ±1000 (tanpa overflow/NaN)."""
        x = np.array([[1000, -1000, 0.0], [-999, 999, 500]])
        p = stable_softmax(x)
        assert np.all(np.isfinite(p))
        np.testing.assert_allclose(p.sum(axis=-1), 1.0, atol=1e-7)

    def test_temperature_sharpens(self):
        """T < 1 membuat distribusi lebih tajam (max lebih tinggi)."""
        x = np.array([[1.0, 2.0, 3.0]])
        p_hot = stable_softmax(x, temperature=2.0)
        p_cold = stable_softmax(x, temperature=0.5)
        assert p_cold.max() > p_hot.max()

    def test_temperature_zero_raises(self):
        with pytest.raises(ValueError, match="temperature"):
            stable_softmax(np.array([[1.0]]), temperature=0)


class TestAttentionEntropy:
    def test_uniform_max_entropy(self):
        """Distribusi seragam -> entropi ternormalisasi ~ 1.0."""
        w = np.ones((1, 8)) / 8
        h = attention_entropy(w)
        np.testing.assert_allclose(h, 1.0, atol=1e-5)

    def test_one_hot_zero_entropy(self):
        """Distribusi one-hot -> entropi 0."""
        w = np.zeros((1, 8))
        w[0, 3] = 1.0
        h = attention_entropy(w)
        np.testing.assert_allclose(h, 0.0, atol=1e-5)

    def test_must_be_2d(self):
        with pytest.raises(ValueError, match="2-D"):
            attention_entropy(np.ones(5))


class TestScaledDotProductAttention:
    def test_output_shape(self):
        """Output: (n_q, d_v), weights: (n_q, n_k)."""
        Q = np.random.randn(4, 32)
        K = np.random.randn(9, 32)
        V = np.random.randn(9, 16)
        out, w = scaled_dot_product_attention(Q, K, V)
        assert out.shape == (4, 16)
        assert w.shape == (4, 9)

    def test_weight_rows_sum_one(self):
        Q = np.random.randn(3, 8)
        K = np.random.randn(5, 8)
        V = np.random.randn(5, 8)
        _, w = scaled_dot_product_attention(Q, K, V)
        np.testing.assert_allclose(w.sum(axis=-1), 1.0, atol=1e-7)

    def test_identity_qk_highlights_diagonal(self):
        """Q == K: tiap token menonjolkan dirinya sendiri (diag == max)."""
        X = np.eye(4)
        _, w = scaled_dot_product_attention(X, X, X)
        for i in range(4):
            assert w[i, i] == pytest.approx(w[i].max(), abs=1e-5)

    def test_dim_mismatch_dk_raises(self):
        """d_k Q != d_k K -> ValueError."""
        Q = np.random.randn(3, 8)
        K = np.random.randn(5, 16)
        V = np.random.randn(5, 16)
        with pytest.raises(ValueError, match="d_k"):
            scaled_dot_product_attention(Q, K, V)

    def test_dim_mismatch_nk_raises(self):
        """Jumlah token K != V -> ValueError."""
        Q = np.random.randn(3, 8)
        K = np.random.randn(5, 8)
        V = np.random.randn(4, 8)
        with pytest.raises(ValueError, match="token"):
            scaled_dot_product_attention(Q, K, V)

    def test_not_2d_raises(self):
        with pytest.raises(ValueError, match="2-D"):
            scaled_dot_product_attention(
                np.random.randn(2, 3, 4),
                np.random.randn(5, 4),
                np.random.randn(5, 4),
            )


class TestCausalMask:
    def test_upper_triangle_zero_weights(self):
        """Mask kausal: segitiga atas weights harus TEPAT 0."""
        n = 6
        Q = np.random.randn(n, 8)
        mask = causal_mask(n)
        _, w = scaled_dot_product_attention(Q, Q, Q, mask=mask)
        upper = np.triu(w, k=1)
        np.testing.assert_allclose(upper, 0.0, atol=1e-10)

    def test_row_0_only_sees_self(self):
        """Baris 0 mask kausal hanya melihat posisi 0."""
        mask = causal_mask(4)
        assert mask[0, 0] == 1.0
        assert mask[0, 1] == 0.0

    def test_last_row_sees_all(self):
        """Baris terakhir melihat semua posisi."""
        mask = causal_mask(5)
        np.testing.assert_allclose(mask[-1], 1.0)


class TestCrossModalAttention:
    def test_shape_correct(self):
        """Output shape (n_text, d); weights (n_text, n_patch)."""
        text = np.random.randn(4, 32)
        image = np.random.randn(9, 32)
        ctx, w = cross_modal_attention(text, image)
        assert ctx.shape == (4, 32)
        assert w.shape == (4, 9)

    def test_matching_patch_gets_high_weight(self):
        """Patch yang cocok harus mendapat bobot tertinggi."""
        np.random.seed(42)
        text = np.random.randn(4, 32) * 0.1
        image = np.random.randn(9, 32) * 0.1
        # Buat patch-2 sangat cocok dengan token-0 (sinyal kuat)
        image[2] = text[0] * 20.0
        # Temperature rendah mempertajam — konsisten dengan eksperimen buku
        _, w = cross_modal_attention(text, image, temperature=0.3)
        assert w[0, 2] == pytest.approx(w[0].max(), abs=1e-3)
        assert w[0, 2] > 0.5

    def test_dim_mismatch_raises(self):
        with pytest.raises(ValueError, match="dimensi"):
            cross_modal_attention(
                np.random.randn(3, 32),
                np.random.randn(5, 64),
            )

    def test_temperature_flat(self):
        """Temperature tinggi -> distribusi lebih seragam."""
        text = np.random.randn(2, 16)
        image = np.random.randn(5, 16)
        _, w_cold = cross_modal_attention(text, image, temperature=0.5)
        _, w_hot = cross_modal_attention(text, image, temperature=5.0)
        # Entropi w_hot harus > w_cold
        h_cold = attention_entropy(w_cold).mean()
        h_hot = attention_entropy(w_hot).mean()
        assert h_hot > h_cold

    def test_worked_example(self):
        """Worked example buku: Q=eye, KV=[[1,0],[0,1],[1,1]]."""
        Q = np.array([[1.0, 0.0], [0.0, 1.0]])
        KV = np.array([[1.0, 0.0], [0.0, 1.0], [1.0, 1.0]])
        out, w = scaled_dot_product_attention(Q, KV, KV)
        np.testing.assert_allclose(w[0], [0.40, 0.20, 0.40], atol=0.01)
        np.testing.assert_allclose(out[0], [0.80, 0.60], atol=0.01)
