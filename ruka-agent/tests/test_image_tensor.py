"""Unit tests for image tensor normalization and layout conversion — Ruka Volume IV."""

import numpy as np
import pytest

from ruka_perception.vision.image_tensor import (
    add_batch,
    estimate_image_tokens,
    laplacian_variance,
    normalize_01,
    normalize_imagenet,
    to_chw,
    to_grayscale,
    to_hwc,
)


def test_to_chw_shape_and_values():
    """HWC -> CHW transpose harus mengubah dimensi tanpa mengubah nilai."""
    img = np.random.randint(0, 255, (32, 48, 3), dtype=np.uint8)
    chw = to_chw(img)
    assert chw.shape == (3, 32, 48)
    # Nilai channel 0 pixel (0,0) identik
    assert img[0, 0, 0] == chw[0, 0, 0]


def test_to_hwc_roundtrip():
    """HWC -> CHW -> HWC harus identik nilai."""
    img = np.random.randint(0, 255, (64, 64, 3), dtype=np.uint8)
    assert np.array_equal(img, to_hwc(to_chw(img)))


def test_to_chw_invalid_shape():
    """HWC dengan jumlah channel bukan 1/3 harus ditolak."""
    with pytest.raises(ValueError, match="bukan tensor HWC image"):
        to_chw(np.zeros((8, 8, 4)))
    with pytest.raises(ValueError, match="bukan tensor HWC image"):
        to_chw(np.zeros((8, 8)))


def test_to_hwc_invalid_shape():
    """CHW dengan channel bukan 1/3 harus ditolak."""
    with pytest.raises(ValueError, match="bukan tensor CHW image"):
        to_hwc(np.zeros((4, 8, 8)))
    with pytest.raises(ValueError, match="bukan tensor CHW image"):
        to_hwc(np.zeros((8, 8)))


def test_add_batch_hwc_rejected():
    """Bug terbuku: tensor (8, 6, 3) bentuk HWC tidak boleh lolos sebagai CHW."""
    with pytest.raises(ValueError, match="kemungkinan ini tensor HWC"):
        add_batch(np.zeros((8, 6, 3)))


def test_add_batch_valid_chw():
    """add_batch harus menambahkan dimensi batch menjadi (1, C, H, W)."""
    t = np.zeros((3, 32, 48))
    b = add_batch(t)
    assert b.shape == (1, 3, 32, 48)


def test_normalize_01():
    """uint8 [0, 255] -> float32 [0, 1]."""
    img = np.array([[[0, 128, 255]]], dtype=np.uint8)
    n = normalize_01(img)
    assert n.dtype == np.float32
    assert np.isclose(n[0, 0, 0], 0.0, atol=1e-3)
    assert np.isclose(n[0, 0, 2], 1.0, atol=1e-3)
    # Sudah di [0,1]: tidak dibagi 255 lagi
    n2 = normalize_01(np.array([[[0.5, 0.8]]], dtype=np.float32))
    assert np.isclose(n2[0, 0, 0], 0.5, atol=1e-6)


def test_normalize_imagenet_shape():
    """normalize_imagenet harus bekerja pada (3, H, W) float."""
    t = np.random.rand(3, 224, 224).astype(np.float32)
    n = normalize_imagenet(t)
    assert n.shape == (3, 224, 224)
    with pytest.raises(ValueError, match="butuh \\(3, H, W\\)"):
        normalize_imagenet(np.zeros((1, 224, 224)))


def test_to_grayscale_luminance_weights():
    """Invarian: jumlah bobot BT.601 = 1 (0.299 + 0.587 + 0.114)."""
    weights = np.array([0.299, 0.587, 0.114])
    assert np.isclose(weights.sum(), 1.0, atol=1e-6)

    # Citra merah murni harus menjadi 0.299
    red = np.zeros((10, 10, 3), dtype=np.float32)
    red[:, :, 0] = 1.0
    gray = to_grayscale(red)
    assert np.isclose(gray[0, 0, 0], 0.299, atol=1e-5)

    # Grayscale murni (R=G=B) harus identik semua channel
    pure_gray = np.full((5, 5, 3), 0.6, dtype=np.float32)
    g = to_grayscale(pure_gray)
    assert np.allclose(g, 0.6, atol=1e-5)


def test_estimate_image_tokens_small():
    """Gambar <= 384px = 258 token (aturan resmi)."""
    assert estimate_image_tokens(384, 384) == 258
    assert estimate_image_tokens(100, 100) == 258


def test_estimate_image_tokens_960x540():
    """Gambar 960x540 = ceil(960/768) * ceil(540/768) = 2 * 1 = 2 ubin = 516 token."""
    assert estimate_image_tokens(960, 540) == 2 * 1 * 258


def test_laplacian_variance_sharp_vs_blur():
    """Gambar dengan tepi tajam harus memiliki variansi Laplacian lebih tinggi dari gambar datar."""
    # Gambar datar
    flat = np.full((32, 32, 3), 0.5, dtype=np.float32)
    var_flat = laplacian_variance(flat)

    # Gambar dengan tepi vertikal
    edge = np.zeros((32, 32, 3), dtype=np.float32)
    edge[:, 16:, :] = 1.0
    var_edge = laplacian_variance(edge)

    assert var_edge > var_flat
    assert np.isclose(var_flat, 0.0, atol=1e-5)
