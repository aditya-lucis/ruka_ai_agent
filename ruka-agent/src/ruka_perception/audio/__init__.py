"""Audio processing module for Ruka Perception.

Exposes framing, windowing, spectrograms, MFCC features, and Voice Activity Detection (VAD).
"""

from .signals import frame_signal, hann_window, quantize, rms, to_db
from .spectrum import (
    dct_matrix,
    hz_to_mel,
    log_mel,
    mel_filterbank,
    mel_to_hz,
    mfcc,
    spectrogram,
)
from .vad import EnergyVAD, frame_features

__all__ = [
    "frame_signal",
    "hann_window",
    "rms",
    "to_db",
    "quantize",
    "spectrogram",
    "hz_to_mel",
    "mel_to_hz",
    "mel_filterbank",
    "log_mel",
    "dct_matrix",
    "mfcc",
    "EnergyVAD",
    "frame_features",
]
