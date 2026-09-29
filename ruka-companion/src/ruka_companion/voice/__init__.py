"""RUKA VI: Voice subsystem package."""

from .audio import AudioBuffer, AudioCore, MicrophoneSource, WavIO
from .vad import EnergyVAD, VADConfig, VADResult
from .asr import Transcription, WhisperASR
from .speaker import (
    AcousticGaussianProvider,
    EnrollmentQuality,
    ExternalDVectorProvider,
    SpeakerProfile,
    mfcc,
)
from .tts import (
    HumanProsodyEngine,
    HumanVoiceSynthesizer,
    ProsodyConfig,
    compute_speaker_embedding,
    inv_mel_scale,
    mel_scale,
)

__all__ = [
    "AudioBuffer",
    "AudioCore",
    "MicrophoneSource",
    "WavIO",
    "EnergyVAD",
    "VADConfig",
    "VADResult",
    "Transcription",
    "WhisperASR",
    "AcousticGaussianProvider",
    "EnrollmentQuality",
    "ExternalDVectorProvider",
    "SpeakerProfile",
    "mfcc",
    "HumanProsodyEngine",
    "HumanVoiceSynthesizer",
    "ProsodyConfig",
    "compute_speaker_embedding",
    "inv_mel_scale",
    "mel_scale",
]
