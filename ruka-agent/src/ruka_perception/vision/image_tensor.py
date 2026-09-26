"""Image tensor normalization and layout conversion for Ruka Perception.

Implements Listing 6.1 from RUKA-IV.
Strictly validates HWC/CHW conventions and prevents silent semantic errors.
"""

from __future__ import annotations

import numpy as np


def to_chw(t_hwc: np.ndarray) -> np.ndarray:
    """HWC -> CHW: (H, W, C) -> (C, H, W)."""
    if t_hwc.ndim != 3 or t_hwc.shape[2] not in (1, 3):
        raise ValueError(f"bukan tensor HWC image: shape {t_hwc.shape}")
    return np.transpose(t_hwc, (2, 0, 1))


def to_hwc(t_chw: np.ndarray) -> np.ndarray:
    """CHW -> HWC: (C, H, W) -> (H, W, C)."""
    if t_chw.ndim != 3 or t_chw.shape[0] not in (1, 3):
        raise ValueError(f"bukan tensor CHW image: shape {t_chw.shape}")
    return np.transpose(t_chw, (1, 2, 0))


def add_batch(t: np.ndarray) -> np.ndarray:
    """(C, H, W) -> (1, C, H, W). Dimensi batch SELALU eksplisit.

    Validasi bentuk CHW: channel harus di depan dan bernilai 1/3 —
    menolak tensor HWC yang terkirim diam-diam.
    """
    if t.ndim != 3 or t.shape[0] not in (1, 3):
        raise ValueError(
            f"butuh (C, H, W) dengan C in (1, 3), dapat {t.shape} "
            f"— kemungkinan ini tensor HWC, konversi dulu"
        )
    return t[np.newaxis, ...]


def normalize_01(t: np.ndarray) -> np.ndarray:
    """Normalisasi uint8 -> float32 [0, 1].

    Wajib sebelum memasuki jalur neural network.
    Mengalikan tanpa /255 membuat gradien training meledak.
    """
    arr = np.asarray(t, dtype=np.float32)
    if arr.max() > 1.0:
        arr = arr / 255.0
    return np.clip(arr, 0.0, 1.0)


_IMAGENET_MEAN = np.array([0.485, 0.456, 0.406], dtype=np.float32)
_IMAGENET_STD = np.array([0.229, 0.224, 0.225], dtype=np.float32)


def normalize_imagenet(t_chw: np.ndarray) -> np.ndarray:
    """Normalisasi statistik ImageNet per channel (mean/std baku).

    Konvensi model vision terlatih (ResNet, ViT, dll).
    Menggunakan statistik berbeda dari model yang mengharapkan ini = akurasi turun senyap.
    Input harus (3, H, W) float [0,1].
    """
    if t_chw.ndim != 3 or t_chw.shape[0] != 3:
        raise ValueError(f"butuh (3, H, W) float, dapat {t_chw.shape}")
    mean = _IMAGENET_MEAN[:, None, None]
    std = _IMAGENET_STD[:, None, None]
    return (t_chw - mean) / std


def to_grayscale(t_hwc: np.ndarray) -> np.ndarray:
    """Konversi RGB (H, W, 3) -> grayscale (H, W, 1) dengan bobot luminance BT.601.

    Y = 0.299 R + 0.587 G + 0.114 B
    Bobot bukan mistik: mata manusia lebih sensitif ke hijau.
    Test memverifikasi invarian 'jumlah bobot = 1'.
    """
    if t_hwc.ndim != 3 or t_hwc.shape[2] != 3:
        raise ValueError(f"butuh (H, W, 3) float, dapat {t_hwc.shape}")
    luma = (
        0.299 * t_hwc[:, :, 0] +
        0.587 * t_hwc[:, :, 1] +
        0.114 * t_hwc[:, :, 2]
    )
    return luma[:, :, np.newaxis].astype(np.float32)


def estimate_image_tokens(width: int, height: int) -> int:
    """Estimasi token Gemini untuk gambar dengan aturan resmi (September 2026).

    Gambar <= 384px kedua sisi: 258 token.
    Lebih besar: dipotong ubin 768x768, tiap ubin 258 token.
    Jumlah ubin = ceil(H / 768) * ceil(W / 768).
    """
    import math
    if width <= 384 and height <= 384:
        return 258
    n_tiles_w = math.ceil(width / 768)
    n_tiles_h = math.ceil(height / 768)
    return n_tiles_w * n_tiles_h * 258


def laplacian_variance(t_hwc: np.ndarray) -> float:
    """Estimasi ketajaman gambar dengan variansi Laplacian.

    Nilai rendah = blur. Dipakai dalam diagnosis kualitas pre-process.
    Dikomputasi dari luma grayscale.
    """
    gray = to_grayscale(t_hwc)[:, :, 0]
    kernel = np.array([[0, 1, 0], [1, -4, 1], [0, 1, 0]], dtype=np.float32)
    h, w = gray.shape
    h_out, w_out = h - 2, w - 2
    lap = np.zeros((h_out, w_out), dtype=np.float32)
    for i in range(h_out):
        for j in range(w_out):
            patch = gray[i:i + 3, j:j + 3]
            lap[i, j] = np.sum(patch * kernel)
    return float(np.var(lap))
