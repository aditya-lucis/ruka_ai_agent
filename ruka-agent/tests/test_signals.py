"""Unit tests for audio signals module in accordance with Ruka Volume IV."""

import numpy as np
import pytest

from ruka_perception.audio.signals import (
    frame_signal,
    hann_window,
    quantize,
    rms,
    to_db,
)


def test_frame_signal_dimension_check():
    """Input harus 1-D, tolak 2-D atau tensor lebih tinggi."""
    with pytest.raises(ValueError, match="input harus 1-D"):
        frame_signal(np.zeros((10, 10)))


def test_frame_signal_too_short():
    """Sinyal lebih pendek dari 1 frame (400 sampel) harus memicu ValueError."""
    with pytest.raises(ValueError, match="lebih pendek dari satu frame"):
        frame_signal(np.zeros(300), frame_ms=25.0, hop_ms=10.0, rate=16000)


def test_frame_signal_98_frames_invariant():
    """Invarian buku: sinyal 1 detik (16000 sampel) menghasilkan 98 frame.

    Sisa frame yang tidak utuh dibuang secara jujur, bukan diam-diam di-zero-pad.
    """
    x = np.sin(2 * np.pi * 440 * np.linspace(0, 1.0, 16000, endpoint=False))
    frames = frame_signal(x, frame_ms=25.0, hop_ms=10.0, rate=16000)
    assert frames.shape == (98, 400)
    assert frames.dtype == np.float32


def test_hann_window_invariants():
    """Window Hann harus endpoint 0, simetris, dan energi efektif ~0.375N."""
    N = 400
    w = hann_window(N)
    assert len(w) == N
    assert np.isclose(w[0], 0.0, atol=1e-6)
    assert np.isclose(w[-1], 0.0, atol=1e-6)
    # Simetris
    assert np.allclose(w, w[::-1], atol=1e-6)
    # Energi efektif sum(w^2) / N approx 0.375
    eff_energy = np.sum(w ** 2) / N
    assert np.isclose(eff_energy, 0.375, atol=0.01)


def test_rms():
    """Uji RMS untuk DC konstan dan gelombang sinus."""
    # DC konstan 0.5 -> RMS = 0.5
    dc = np.full(1000, 0.5)
    assert np.isclose(rms(dc), 0.5, atol=1e-6)

    # Gelombang sinus amplitudo A=2.0 -> RMS = A / sqrt(2) approx 1.4142
    t = np.linspace(0, 1.0, 16000, endpoint=False)
    sine = 2.0 * np.sin(2 * np.pi * 100 * t)
    assert np.isclose(rms(sine), 2.0 / np.sqrt(2.0), atol=1e-3)

    # Hening
    assert rms(np.zeros(100)) == 0.0


def test_to_db():
    """Uji konversi dB dengan floor pengaman."""
    # Sinyal hening tidak boleh menjadi -inf
    silence = np.zeros(100)
    db_silence = to_db(silence, floor_db=-80.0)
    assert np.all(db_silence == -80.0)

    # Puncak sinyal harus menghasilkan 0 dB jika reference=None
    sig = np.array([0.1, 0.5, 1.0])
    db_sig = to_db(sig)
    assert np.isclose(db_sig[-1], 0.0, atol=1e-6)


def test_quantize():
    """Uji kuantisasi seragam 16-bit."""
    x = np.array([-1.5, -1.0, 0.0, 1.0, 1.5])
    q = quantize(x, bits=16)
    assert np.all(q >= -1.0)
    assert np.all(q <= 1.0)
    step = 2.0 / (2 ** 16)
    # Nilai 0.0 terkuantisasi mendekati grid
    assert np.isclose(q[2], 0.0, atol=step)


def test_parseval_theorem():
    """Invarian matematis Parseval untuk setengah spektrum (rFFT).

    2 * sum(|X[k]|^2) - |X[0]|^2 - |X[N/2]|^2 = N * sum((x_n * w_n)^2)
    """
    N = 400
    np.random.seed(42)
    x = np.random.randn(N).astype(np.float64)
    w = hann_window(N).astype(np.float64)
    xw = x * w

    spec = np.fft.rfft(xw)
    power = np.abs(spec) ** 2

    # Parseval untuk setengah spektrum
    time_domain_energy = N * np.sum(xw ** 2)
    freq_domain_energy = 2.0 * np.sum(power) - power[0] - power[-1]

    np.testing.assert_allclose(time_domain_energy, freq_domain_energy, rtol=5e-5)
