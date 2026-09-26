"""Spectrogram, Mel Filterbank, and MFCC extraction for Ruka Perception.

Implements Listings 5.2 & 5.3 from RUKA-IV without external black-box audio libraries.
Pure NumPy implementation verified against Parseval's theorem and SciPy orthogonal DCT-II.
"""

from __future__ import annotations

import numpy as np
from .signals import frame_signal, hann_window


def spectrogram(
    x: np.ndarray,
    rate: int = 16000,
    frame_ms: float = 25.0,
    hop_ms: float = 10.0,
) -> tuple[np.ndarray, np.ndarray]:
    """Power spectrogram via rFFT per frame.

    Return:
        power : (n_frames, n_bins) float — |rFFT|^2
        freqs : (n_bins,) frekuensi pusat bin dalam Hz
    rFFT dipilih karena sinyal real: spektrum simetris, simpan setengah.
    """
    frames = frame_signal(x, frame_ms=frame_ms, hop_ms=hop_ms, rate=rate)
    win = hann_window(frames.shape[1])
    windowed = frames * win[None, :]
    spec = np.fft.rfft(windowed, axis=1)
    power = (np.abs(spec) ** 2).astype(np.float64)
    freqs = np.fft.rfftfreq(frames.shape[1], d=1.0 / rate)
    return power, freqs


def hz_to_mel(f: np.ndarray | float) -> np.ndarray | float:
    """Hz -> mel (rumus 2595 log10(1 + f/700))."""
    return 2595.0 * np.log10(1.0 + np.asarray(f, dtype=np.float64) / 700.0)


def mel_to_hz(m: np.ndarray | float) -> np.ndarray | float:
    """mel -> Hz (invers persis)."""
    return 700.0 * (10.0 ** (np.asarray(m, dtype=np.float64) / 2595.0) - 1.0)


def mel_filterbank(
    n_filters: int,
    n_bins: int,
    rate: int,
    fmin: float = 80.0,
    fmax: float | None = None,
) -> np.ndarray:
    """Filterbank mel: matriks (n_filters, n_bins) triangular.

    Titik-titik batas di skala mel dibagi rata; setiap filter segitiga
    menumpang dua tetangga (overlap 50% wilayah — desain standar HTK).
    Return sudah dinormalkan per filter (luas segitiga = 1).
    """
    if n_filters < 2:
        raise ValueError("minimal 2 filter")
    fmax = fmax or rate / 2.0
    if not (0 < fmin < fmax <= rate / 2.0 + 1e-9):
        raise ValueError("0 < fmin < fmax <= rate/2 wajib")
    mel_pts = np.linspace(hz_to_mel(fmin), hz_to_mel(fmax), n_filters + 2)
    hz_pts = mel_to_hz(mel_pts)
    bins = np.floor(n_bins * hz_pts / (rate / 2.0)).astype(int)
    bins = np.clip(bins, 0, n_bins - 1)
    fb = np.zeros((n_filters, n_bins), dtype=np.float64)
    for m in range(n_filters):
        left, center, right = bins[m], bins[m + 1], bins[m + 2]
        up = np.maximum(0, (np.arange(n_bins) - left) / max(center - left, 1))
        down = np.maximum(0, (right - np.arange(n_bins)) / max(right - center, 1))
        tri = np.minimum(up, down)
        area = tri.sum()
        if area > 0:
            tri = tri / area  # normalisasi luas
        fb[m] = tri
    return fb


def log_mel(power: np.ndarray, fb: np.ndarray) -> np.ndarray:
    """Kompresi log energi per filterbank Mel.

    Menghindari log(0) dengan floor 1e-10 (memberikan rentang dinamis [-23.03, ...]).
    """
    mel_energy = power @ fb.T
    return np.log(np.maximum(mel_energy, 1e-10))


def dct_matrix(n_cepstra: int, n_filters: int) -> np.ndarray:
    """Matriks transformasi ortogonal DCT-II (ortho norm).

    Ekuivalen persis dengan scipy.fft.dct(x, type=2, norm='ortho')[:n_cepstra].
    """
    n = np.arange(n_filters)
    k = np.arange(n_cepstra)[:, None]
    c = np.sqrt(2.0 / n_filters) * np.cos(np.pi * k * (2 * n + 1) / (2.0 * n_filters))
    c[0] *= 1.0 / np.sqrt(2.0)
    return c


def mfcc(
    x: np.ndarray,
    rate: int = 16000,
    n_filters: int = 26,
    n_cepstra: int = 13,
    frame_ms: float = 25.0,
    hop_ms: float = 10.0,
) -> np.ndarray:
    """MFCC lengkap: spectrogram -> mel -> log -> DCT.

    Return (n_frames, n_cepstra). Koefisien ke-0 (C0) menangkap energi
    total — untuk fitur 'bentuk spektral' murni biasanya dibuang
    (liftering C0 dipisahkan sebagai keputusan pemanggil).
    """
    power, _freqs = spectrogram(x, rate, frame_ms, hop_ms)
    fb = mel_filterbank(n_filters, power.shape[1], rate)
    logmel = log_mel(power, fb)
    c = dct_matrix(n_cepstra, n_filters)
    return (logmel @ c.T).astype(np.float64)
