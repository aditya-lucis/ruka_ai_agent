"""Signal processing foundation for Ruka Perception.

Implements Listing 5.1 and signal processing primitives from RUKA-IV.
Provides deterministic framing, Hann windowing, RMS energy, and dB conversion.
"""

from __future__ import annotations

import numpy as np


def frame_signal(
    x: np.ndarray,
    frame_ms: float = 25.0,
    hop_ms: float = 10.0,
    rate: int = 16000,
) -> np.ndarray:
    """Potong sinyal jadi frame tumpang tindih.

    Return (n_frames, frame_len). Frame terakhir yang tidak utuh
    DIBUANG (konvensi umum) — jumlahnya dilaporkan di catatan modul,
    bukan diam-diam di-zero-pad.
    """
    if len(x.shape) != 1:
        raise ValueError("input harus 1-D")
    frame_len = int(rate * frame_ms / 1000.0)
    hop_len = int(rate * hop_ms / 1000.0)
    if frame_len < 2 or hop_len < 1:
        raise ValueError("frame/hop terlalu kecil")
    n_frames = 1 + (len(x) - frame_len) // hop_len
    if n_frames < 1:
        raise ValueError(
            f"sinyal {len(x)} sampel lebih pendek dari satu frame "
            f"{frame_len} sampel"
        )
    idx = np.arange(n_frames)[:, None] * hop_len + np.arange(frame_len)[None, :]
    return x[idx].astype(np.float32)


def hann_window(frame_len: int) -> np.ndarray:
    """Window Hann: w[n] = 0.5(1 - cos(2 pi n / (N-1))).

    Endpoint 0 — mencegah diskontinuitas saat FFT.
    """
    if frame_len < 2:
        raise ValueError("frame_len minimal 2")
    n = np.arange(frame_len)
    return (0.5 * (1.0 - np.cos(2 * np.pi * n / (frame_len - 1)))).astype(np.float32)


def rms(x: np.ndarray) -> float:
    """Root-mean-square: energi rata-rata sinyal/frame."""
    if x.size == 0:
        return 0.0
    return float(np.sqrt(np.mean(np.square(x.astype(np.float64)))))


def to_db(
    x: np.ndarray,
    floor_db: float = -80.0,
    reference: float | None = None,
) -> np.ndarray:
    """Konversi amplitudo/energi ke dB.

    floor mencegah log(0) = -inf merusak visualisasi dan metrik.
    Referensi default = max.
    """
    mag = np.abs(x.astype(np.float64))
    if reference is None:
        reference = float(mag.max()) if mag.max() > 0 else 1.0
    db = 20.0 * np.log10(mag / reference + 1e-12)
    return np.maximum(db, floor_db)


def quantize(x: np.ndarray, bits: int = 16) -> np.ndarray:
    """Kuantisasi seragam pada rentang [-1.0, 1.0].

    Menghasilkan grid step = 2 / (2^bits).
    """
    levels = 2 ** bits
    step = 2.0 / levels
    # Clamping and mapping to integer grid
    clipped = np.clip(x, -1.0, 1.0)
    indices = np.round((clipped + 1.0) / step)
    indices = np.clip(indices, 0, levels - 1)
    return (indices * step - 1.0).astype(np.float32)
