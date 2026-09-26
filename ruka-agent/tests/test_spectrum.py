"""Unit tests for audio spectrum module in accordance with Ruka Volume IV."""

import numpy as np
import pytest

from ruka_perception.audio.spectrum import (
    dct_matrix,
    hz_to_mel,
    log_mel,
    mel_filterbank,
    mel_to_hz,
    mfcc,
    spectrogram,
)


def test_spectrogram_shape_and_peak():
    """Uji spektrum daya: nada murni 1000 Hz harus berpuncak di 1000 Hz +- 15 Hz."""
    rate = 16000
    t = np.linspace(0, 1.0, rate, endpoint=False)
    target_hz = 1000.0
    x = np.sin(2 * np.pi * target_hz * t)

    power, freqs = spectrogram(x, rate=rate, frame_ms=25.0, hop_ms=10.0)
    # Shape invariant: 98 frame, 201 bins (400 // 2 + 1)
    assert power.shape == (98, 201)
    assert len(freqs) == 201

    # Bin dengan daya tertinggi pada frame tengah
    mid_frame = power[49]
    peak_bin = np.argmax(mid_frame)
    peak_hz = freqs[peak_bin]
    assert np.isclose(peak_hz, target_hz, atol=15.0)


def test_hz_mel_roundtrip():
    """Uji inversi eksak mel_to_hz(hz_to_mel(f)) == f."""
    f = np.array([0.0, 100.0, 440.0, 1000.0, 4000.0, 8000.0])
    m = hz_to_mel(f)
    assert np.isclose(m[0], 0.0, atol=1e-6)
    f_rec = mel_to_hz(m)
    np.testing.assert_allclose(f, f_rec, rtol=1e-5)


def test_mel_filterbank_normalization():
    """Uji matriks filterbank mel triangular ternormalisasi."""
    fb = mel_filterbank(n_filters=26, n_bins=201, rate=16000, fmin=80.0, fmax=8000.0)
    assert fb.shape == (26, 201)
    # Setiap filter memiliki luas (sum) = 1.0 jika tidak kosong
    for m in range(26):
        s = np.sum(fb[m])
        if s > 0:
            assert np.isclose(s, 1.0, atol=1e-6)


def test_mel_filterbank_validation():
    """Validasi parameter filterbank mel."""
    with pytest.raises(ValueError, match="minimal 2 filter"):
        mel_filterbank(n_filters=1, n_bins=201, rate=16000)

    with pytest.raises(ValueError, match="0 < fmin < fmax"):
        mel_filterbank(n_filters=26, n_bins=201, rate=16000, fmin=9000.0, fmax=8000.0)


def test_dct_matrix_orthogonality_and_scipy():
    """Uji ortogonalitas matriks DCT-II dan verifikasi silang terhadap SciPy."""
    n_cepstra = 13
    n_filters = 26
    c = dct_matrix(n_cepstra, n_filters)
    assert c.shape == (n_cepstra, n_filters)

    # Ortogonalitas C @ C.T = I
    gram = c @ c.T
    np.testing.assert_allclose(gram, np.eye(n_cepstra), atol=1e-10)

    # Cross-check dengan scipy jika tersedia
    try:
        import scipy.fft
        np.random.seed(123)
        x = np.random.randn(n_filters)
        manual_dct = c @ x
        scipy_dct = scipy.fft.dct(x, type=2, norm="ortho")[:n_cepstra]
        np.testing.assert_allclose(manual_dct, scipy_dct, atol=1e-10)
    except ImportError:
        pass


def test_mfcc_shape():
    """Ekstraksi MFCC harus mengembalikan (n_frames, n_cepstra)."""
    rate = 16000
    x = np.random.randn(rate).astype(np.float32)
    feats = mfcc(x, rate=rate, n_filters=26, n_cepstra=13)
    assert feats.shape == (98, 13)
