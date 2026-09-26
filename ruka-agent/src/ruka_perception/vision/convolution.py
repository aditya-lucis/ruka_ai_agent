"""2D Convolution, MaxPool, AvgPool, and Receptive Field for Ruka Perception.

Implements Listings 6.2 and 6.3 from RUKA-IV.
Pure NumPy cross-correlation without black-box libraries.
Includes classic kernels: Sobel-X/Y, Box Blur, Sharpen.
"""

from __future__ import annotations

import numpy as np


def conv2d(
    x: np.ndarray,
    w: np.ndarray,
    stride: int = 1,
    padding: int = 0,
) -> np.ndarray:
    """Konvolusi (cross-correlation) 2D batch. Float32 keluar.

    Args:
        x : (N, C_in, H, W) input tensor
        w : (C_out, C_in, kH, kW) kernel tensor
        stride  : langkah sliding window, >= 1
        padding : jumlah nol di tepi, >= 0

    Returns:
        (N, C_out, H_out, W_out) feature map

    Catatan: ini adalah CROSS-CORRELATION (kernel tidak dibalik), meski
    disebut 'convolution' mengikuti konvensi CNN populer.
    """
    if x.ndim != 4:
        raise ValueError(f"x harus (N, C_in, H, W), dapat {x.shape}")
    if w.ndim != 4:
        raise ValueError(f"w harus (C_out, C_in, kH, kW), dapat {w.shape}")
    n, c_in, h, wd = x.shape
    c_out, w_cin, kh, kw = w.shape
    if c_in != w_cin:
        raise ValueError(f"channel mismatch: x punya {c_in}, kernel {w_cin}")
    if stride < 1 or padding < 0:
        raise ValueError("stride >= 1 dan padding >= 0 wajib")
    h_out = (h + 2 * padding - kh) // stride + 1
    w_out = (wd + 2 * padding - kw) // stride + 1
    if h_out < 1 or w_out < 1:
        raise ValueError(
            f"kernel ({kh},{kw}) lebih besar dari input efektif "
            f"({h + 2 * padding},{wd + 2 * padding})"
        )
    if padding:
        x = np.pad(x, ((0, 0), (0, 0), (padding, padding), (padding, padding)))
    out = np.zeros((n, c_out, h_out, w_out), dtype=np.float32)
    for i in range(h_out):
        for j in range(w_out):
            si = i * stride
            sj = j * stride
            patch = x[:, :, si:si + kh, sj:sj + kw]  # (N, C_in, kH, kW)
            out[:, :, i, j] = np.einsum("nchw,ochw->no", patch, w)
    return out


def maxpool2d(x: np.ndarray, k: int = 2, stride: int | None = None) -> np.ndarray:
    """Max pooling (N, C, H, W). Default stride = k (non-overlap).

    Invariansi translasi kecil: objek bergeser beberapa piksel -> respons serupa.
    Harga: posisi persis hilang.
    """
    if x.ndim != 4:
        raise ValueError(f"x harus (N, C, H, W), dapat {x.shape}")
    if stride is None:
        stride = k
    n, c, h, ww = x.shape
    h_out = (h - k) // stride + 1
    w_out = (ww - k) // stride + 1
    if h_out < 1 or w_out < 1:
        raise ValueError(f"pool kernel {k} lebih besar dari input ({h},{ww})")
    out = np.zeros((n, c, h_out, w_out), dtype=x.dtype)
    for i in range(h_out):
        for j in range(w_out):
            si, sj = i * stride, j * stride
            out[:, :, i, j] = x[:, :, si:si + k, sj:sj + k].max(axis=(2, 3))
    return out


def avgpool2d(x: np.ndarray, k: int = 2, stride: int | None = None) -> np.ndarray:
    """Average pooling (N, C, H, W).

    Untuk kasus sinyal kontinu yang butuh ringkasan, bukan maks.
    """
    if x.ndim != 4:
        raise ValueError(f"x harus (N, C, H, W), dapat {x.shape}")
    if stride is None:
        stride = k
    n, c, h, ww = x.shape
    h_out = (h - k) // stride + 1
    w_out = (ww - k) // stride + 1
    if h_out < 1 or w_out < 1:
        raise ValueError(f"pool kernel {k} lebih besar dari input ({h},{ww})")
    out = np.zeros((n, c, h_out, w_out), dtype=np.float32)
    for i in range(h_out):
        for j in range(w_out):
            si, sj = i * stride, j * stride
            out[:, :, i, j] = x[:, :, si:si + k, sj:sj + k].mean(axis=(2, 3))
    return out


# ---------------------------------------------------------------------------
# Kernel klasik (grayscale: 1-channel-in, 1-channel-out)
# Dokumentasi buku: deteksi blur, tepi, dan penajaman untuk diagnosis kualitas.
# ---------------------------------------------------------------------------

SOBEL_X: np.ndarray = np.array(
    [[-1, 0, +1], [-2, 0, +2], [-1, 0, +1]], dtype=np.float32
).reshape(1, 1, 3, 3)

SOBEL_Y: np.ndarray = np.array(
    [[-1, -2, -1], [0, 0, 0], [+1, +2, +1]], dtype=np.float32
).reshape(1, 1, 3, 3)

BOX_BLUR: np.ndarray = np.ones((1, 1, 3, 3), dtype=np.float32) / 9.0

SHARPEN: np.ndarray = np.array(
    [[0, -1, 0], [-1, +5, -1], [0, -1, 0]], dtype=np.float32
).reshape(1, 1, 3, 3)


def receptive_field(layers: list[tuple[int, int]]) -> int:
    """Receptive field kumulatif dari susunan (kernel, stride).

    RF bertambah: RF_{l+1} = RF_l + (k_l - 1) * j_l,
    dengan jump j adalah hasil kali semua stride sebelum layer l.

    Contoh: dua conv 3x3 stride 1 -> RF 5; ditambah maxpool 2x2
    stride 2 lalu conv 3x3 -> RF 14.
    """
    rf, jump = 1, 1
    for k, s in layers:
        if k < 1 or s < 1:
            raise ValueError("kernel dan stride harus >= 1")
        rf += (k - 1) * jump
        jump *= s
    return rf
