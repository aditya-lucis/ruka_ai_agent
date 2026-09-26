"""Unit tests for conv2d, pooling, and receptive field — Ruka Volume IV."""

import numpy as np
import pytest

from ruka_perception.vision.convolution import (
    BOX_BLUR,
    SHARPEN,
    SOBEL_X,
    SOBEL_Y,
    avgpool2d,
    conv2d,
    maxpool2d,
    receptive_field,
)


def test_conv2d_output_shape_formula():
    """Invarian rumus: H_out = (H + 2P - kH) // S + 1."""
    # stride=1, padding=0
    x = np.ones((1, 1, 8, 8), dtype=np.float32)
    w = np.ones((1, 1, 3, 3), dtype=np.float32)
    out = conv2d(x, w, stride=1, padding=0)
    assert out.shape == (1, 1, 6, 6)

    # stride=2, padding=1
    out2 = conv2d(x, w, stride=2, padding=1)
    h_out = (8 + 2 * 1 - 3) // 2 + 1  # = 5
    assert out2.shape == (1, 1, h_out, h_out)


def test_conv2d_identity_kernel():
    """Kernel identitas (center=1, else 0) harus mengembalikan input (tanpa tepi)."""
    identity = np.zeros((1, 1, 3, 3), dtype=np.float32)
    identity[0, 0, 1, 1] = 1.0

    np.random.seed(7)
    x = np.random.randn(1, 1, 10, 10).astype(np.float32)
    out = conv2d(x, identity, stride=1, padding=0)
    # Hasil harus == isi input yang dicrop 1 piksel di tepi
    np.testing.assert_allclose(out[0, 0], x[0, 0, 1:-1, 1:-1], atol=1e-5)


def test_conv2d_flat_area_zero():
    """Area datar dengan kernel Sobel-X harus menghasilkan respons mendekati nol."""
    flat = np.ones((1, 1, 10, 10), dtype=np.float32) * 0.5
    out = conv2d(flat, SOBEL_X, stride=1, padding=0)
    assert np.allclose(out, 0.0, atol=1e-5)


def test_conv2d_delta_stamp_cross_correlation():
    """Buku 6.9: delta stamp membuktikan konvensi cross-correlation.

    Dalam cross-correlation, window bergerak melintasi input.
    Di posisi delta, patch = [0,0,...,delta,...,0]. Hasilnya adalah:
      out[j] = Σ patch[j..j+k] * w
    Di sekitar delta di posisi 2 (dari 5), window yang menggunakan delta:
      posisi j=0: patch=[delta,0,0] * w=[1,2,3] -> nilai w[0]=1... tapi patch slicing:
      einsum membaca patch kiri ke kanan. Karena delta di posisi tengah,
      saat window di posisi 0: x[0:3] = [0, 0, delta] -> dot [1,2,3] = 1 * delta
      saat window di posisi 1: x[1:4] = [0, delta, 0] -> dot [1,2,3] = 2 * delta
      saat window di posisi 2: x[2:5] = [delta, 0, 0] -> dot [1,2,3] = 3 * delta

    Jadi hasilnya [1, 2, 3] jika delta di posisi 0 (paling kiri yang masuk window).
    Kita tempatkan delta di posisi 0 dari padded:
    """
    kernel = np.array([[[[1.0, 2.0, 3.0]]]], dtype=np.float32)  # (1,1,1,3)
    delta = np.zeros((1, 1, 1, 5), dtype=np.float32)
    delta[0, 0, 0, 0] = 1.0  # delta di kiri

    out = conv2d(delta, kernel)
    # window di posisi 0: x[0:3]=[1,0,0] dot [1,2,3] = 1
    # window di posisi 1: x[1:4]=[0,0,0] dot [1,2,3] = 0
    # window di posisi 2: x[2:5]=[0,0,0] dot [1,2,3] = 0
    expected = np.array([[[[1.0, 0.0, 0.0]]]])
    np.testing.assert_allclose(out, expected, atol=1e-5)

    # Cek buku: delta di tengah (posisi 2) -> stamp kernel terbalik [3,2,1]
    # Ini membuktikan cross-correlation menempatkan kernel seperti "dibaca dari kanan"
    delta2 = np.zeros((1, 1, 1, 5), dtype=np.float32)
    delta2[0, 0, 0, 2] = 1.0
    out2 = conv2d(delta2, kernel)
    # window 0: x[0:3]=[0,0,delta] -> dot w=[1,2,3] = 3
    # window 1: x[1:4]=[0,delta,0] -> dot w=[1,2,3] = 2
    # window 2: x[2:5]=[delta,0,0] -> dot w=[1,2,3] = 1
    expected2 = np.array([[[[3.0, 2.0, 1.0]]]])
    np.testing.assert_allclose(out2, expected2, atol=1e-5)


def test_conv2d_channel_mismatch():
    """channel mismatch antara input dan kernel harus memicu ValueError."""
    x = np.ones((1, 3, 8, 8), dtype=np.float32)  # 3 channel input
    w = np.ones((1, 1, 3, 3), dtype=np.float32)   # 1 channel kernel
    with pytest.raises(ValueError, match="channel mismatch"):
        conv2d(x, w)


def test_conv2d_invalid_ndim():
    """Input bukan 4D harus ditolak."""
    with pytest.raises(ValueError, match="x harus \\(N, C_in, H, W\\)"):
        conv2d(np.ones((8, 8)), np.ones((1, 1, 3, 3)))
    with pytest.raises(ValueError, match="w harus \\(C_out, C_in, kH, kW\\)"):
        conv2d(np.ones((1, 1, 8, 8)), np.ones((3, 3)))


def test_conv2d_kernel_too_large():
    """Kernel lebih besar dari input efektif harus memicu ValueError."""
    x = np.ones((1, 1, 4, 4), dtype=np.float32)
    w = np.ones((1, 1, 5, 5), dtype=np.float32)
    with pytest.raises(ValueError, match="lebih besar dari input efektif"):
        conv2d(x, w)


def test_maxpool2d_shape_and_max():
    """MaxPool 2x2 harus memilih nilai terbesar tiap blok 2x2."""
    x = np.array([[[[1, 3, 2, 0],
                    [4, 2, 5, 1],
                    [0, 1, 3, 2],
                    [6, 0, 1, 4]]]], dtype=np.float32)
    out = maxpool2d(x, k=2, stride=2)
    assert out.shape == (1, 1, 2, 2)
    assert np.isclose(out[0, 0, 0, 0], 4.0)
    assert np.isclose(out[0, 0, 0, 1], 5.0)
    assert np.isclose(out[0, 0, 1, 0], 6.0)
    assert np.isclose(out[0, 0, 1, 1], 4.0)


def test_maxpool2d_invalid_ndim():
    """MaxPool pada bukan 4D harus ditolak."""
    with pytest.raises(ValueError, match="x harus \\(N, C, H, W\\)"):
        maxpool2d(np.ones((4, 4)))


def test_avgpool2d_shape():
    """AvgPool harus menghitung rata-rata per blok."""
    x = np.array([[[[1.0, 3.0, 5.0, 7.0],
                    [2.0, 4.0, 6.0, 8.0],
                    [0.0, 0.0, 0.0, 0.0],
                    [0.0, 0.0, 0.0, 0.0]]]], dtype=np.float32)
    out = avgpool2d(x, k=2, stride=2)
    assert out.shape == (1, 1, 2, 2)
    assert np.isclose(out[0, 0, 0, 0], 2.5)  # (1+3+2+4)/4


def test_receptive_field_table_62():
    """Invarian Tabel 6.2: tumpukan 5 layer menghasilkan RF = 18 (bukan 13).

    Sesuai tabel buku:
      conv3x3 s=1  -> RF=3,  jump=1
      pool2x2 s=2  -> RF=4,  jump=2
      conv3x3 s=1  -> RF=8,  jump=2
      pool2x2 s=2  -> RF=10, jump=4
      conv3x3 s=1  -> RF=18, jump=4
    """
    layers = [(3, 1), (2, 2), (3, 1), (2, 2), (3, 1)]
    assert receptive_field(layers) == 18


def test_receptive_field_single_conv3x3():
    """Satu conv 3x3 -> RF = 3."""
    assert receptive_field([(3, 1)]) == 3


def test_receptive_field_two_conv3x3():
    """Dua conv 3x3 stride 1 -> RF = 5."""
    assert receptive_field([(3, 1), (3, 1)]) == 5


def test_receptive_field_invalid():
    """Kernel <= 0 atau stride <= 0 harus ditolak."""
    with pytest.raises(ValueError, match="kernel dan stride harus >= 1"):
        receptive_field([(0, 1)])
    with pytest.raises(ValueError, match="kernel dan stride harus >= 1"):
        receptive_field([(3, 0)])


def test_sobel_x_edge_response():
    """Buku 6.9: kolom dengan perubahan drastis harus menyala di Sobel-X."""
    # Seluruh area datar -> 0
    flat = np.ones((1, 1, 5, 5), dtype=np.float32) * 0.5
    assert np.allclose(conv2d(flat, SOBEL_X), 0.0, atol=1e-5)

    # Tepi vertikal di kolom 2 -> respons positif
    edge = np.zeros((1, 1, 5, 5), dtype=np.float32)
    edge[0, 0, :, 3:] = 1.0
    out = conv2d(edge, SOBEL_X)
    # Kolom tepi (tengah) harus punya respons positif
    assert out.max() > 0.0
