"""Unit tests for Voice Activity Detection (VAD) module in accordance with Ruka Volume IV."""

import numpy as np
import pytest

from ruka_perception.audio.vad import EnergyVAD, frame_features


def test_frame_features_shapes():
    """Uji bentuk keluaran frame_features (energy_db dan zcr)."""
    rate = 16000
    x = np.random.randn(rate).astype(np.float32)
    energy_db, zcr = frame_features(x, rate=rate)
    assert len(energy_db) == 98
    assert len(zcr) == 98
    assert np.all(zcr >= 0.0) and np.all(zcr <= 1.0)


def test_silence_only_returns_no_segments():
    """Audio hening murni harus mengembalikan 0 segmen ucapan (noise floor guard)."""
    vad = EnergyVAD(rate=16000)
    silence = np.zeros(16000, dtype=np.float32)
    segments = vad.detect(silence)
    assert segments == []
    assert vad.speech_ratio(silence) == 0.0


def test_flat_signal_dynamic_guard():
    """Sinyal datar tanpa dinamika (dynamic < min_dynamic_db) ditolak."""
    vad = EnergyVAD(rate=16000, min_dynamic_db=6.0)
    flat = np.full(16000, 0.1, dtype=np.float32)
    segments = vad.detect(flat)
    assert segments == []


def test_click_rejection():
    """Suara klik sangat pendek (misal 2.5 ms = 40 sampel) dibuang."""
    vad = EnergyVAD(rate=16000, min_segment_ms=50.0)
    x = np.zeros(16000, dtype=np.float32)
    # Impuls klik 40 sampel
    x[8000:8040] = 0.8
    segments = vad.detect(x)
    assert segments == []


def test_hysteresis_and_hangover():
    """Uji jeda napas:

    - Jeda pendek (< hangover 8 frame / 80ms) tidak memotong segmen
    - Jeda panjang (> hangover) memisahkan segmen menjadi dua
    """
    rate = 16000
    vad = EnergyVAD(rate=rate, hangover=8, min_segment_ms=50.0)

    # 1. Dua blok suara dengan jeda pendek (40 ms = 4 frame) dan padding hening
    t_block = np.linspace(0, 0.5, 8000, endpoint=False)
    voice = 0.5 * np.sin(2 * np.pi * 300 * t_block)
    silence_pad = np.zeros(3200, dtype=np.float32)  # 200 ms padding hening
    short_pause = np.zeros(int(rate * 0.04), dtype=np.float32)

    speech_with_short_pause = np.concatenate([silence_pad, voice, short_pause, voice, silence_pad])
    segments_short = vad.detect(speech_with_short_pause)
    # Harus menjadi 1 segmen tunggal karena jeda lebih pendek dari hangover (8 frame)
    assert len(segments_short) == 1

    # 2. Dua blok suara dengan jeda panjang (400 ms = 40 frame > 8)
    long_pause = np.zeros(int(rate * 0.4), dtype=np.float32)
    speech_with_long_pause = np.concatenate([silence_pad, voice, long_pause, voice, silence_pad])
    segments_long = vad.detect(speech_with_long_pause)
    # Harus terbelah menjadi 2 segmen terpisah
    assert len(segments_long) == 2
