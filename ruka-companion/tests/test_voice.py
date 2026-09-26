"""RUKA VI: Tests for Voice Subsystem (Audio, VAD, ASR, Speaker Recognition).
Strictly follows RUKA-VI Chapters XI & XII testing doctrine.
"""

from __future__ import annotations

import tempfile
from unittest.mock import MagicMock

import numpy as np
import pytest

from ruka_companion.voice.audio import (
    AudioBuffer,
    AudioCore,
    MicrophoneSource,
    WavIO,
    TARGET_FS,
)
from ruka_companion.voice.vad import EnergyVAD, VADConfig, segment_ms
from ruka_companion.voice.asr import Transcription, WhisperASR
from ruka_companion.voice.speaker import (
    AcousticGaussianProvider,
    ExternalDVectorProvider,
    SpeakerProfile,
    mfcc,
)


class TestAudio:
    def test_audio_buffer_validation(self):
        with pytest.raises(ValueError, match="mono 1-D"):
            AudioBuffer(samples=np.zeros((10, 2), dtype=np.float32), fs=16000)

        with pytest.raises(ValueError, match="fs > 0"):
            AudioBuffer(samples=np.zeros(1600, dtype=np.float32), fs=0)

        buf = AudioBuffer(samples=np.ones(16000, dtype=np.float32), fs=16000)
        assert buf.duration_s == 1.0
        assert buf.rms == pytest.approx(1.0)

        empty = AudioBuffer(samples=np.array([], dtype=np.float32), fs=16000)
        assert empty.rms == 0.0

    def test_wav_io_roundtrip(self):
        t = np.arange(16000) / 16000.0
        samples = (0.5 * np.sin(2 * np.pi * 440 * t)).astype(np.float32)

        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            tmp_path = tmp.name

        try:
            WavIO.save(tmp_path, samples, fs=16000)
            loaded = WavIO.load(tmp_path)
            assert loaded.fs == 16000
            # 16-bit PCM quantization error is <= 1e-3
            diff = np.max(np.abs(samples - loaded.samples))
            assert diff < 1e-3
        finally:
            import os

            if os.path.exists(tmp_path):
                os.remove(tmp_path)

    def test_audio_core_framing(self):
        samples = np.zeros(16000, dtype=np.float32)
        frames = AudioCore.frame(samples, fs=16000, frame_ms=25, hop_ms=10)
        frame_len = 400
        hop = 160
        expected_frames = 1 + (16000 - frame_len) // hop
        assert frames.shape == (expected_frames, frame_len)

    def test_audio_core_normalize_peak(self):
        samples = np.array([0.1, -0.2, 0.5, -0.1], dtype=np.float32)
        norm = AudioCore.normalize_peak(samples, target=0.7)
        assert np.max(np.abs(norm)) == pytest.approx(0.7)

        silence = np.zeros(10, dtype=np.float32)
        assert np.all(AudioCore.normalize_peak(silence) == 0.0)

    def test_audio_core_resample_linear(self):
        samples = np.sin(np.linspace(0, 10, 48000)).astype(np.float32)
        resampled = AudioCore.resample_linear(samples, fs_in=48000, fs_out=16000)
        assert resampled.size == 16000

        noop = AudioCore.resample_linear(samples, fs_in=16000, fs_out=16000)
        assert np.array_equal(noop, samples)

        with pytest.raises(ValueError):
            AudioCore.resample_linear(samples, fs_in=-1, fs_out=16000)

    def test_microphone_source_capability(self):
        cap = MicrophoneSource.capability()
        assert cap["layer"] == "device"
        assert cap["kind"] == "microphone"
        assert isinstance(cap["available"], bool)


class TestVAD:
    def test_vad_synthetic_speech_and_silence(self):
        fs = 16000
        t = np.arange(32000) / fs
        # Synthetic speech signal (frequency modulated sinusoid)
        f = 140 + 60 * np.sin(2 * np.pi * 3 * t)
        speech = (0.5 * np.sin(2 * np.pi * f * t)).astype(np.float32)

        vad = EnergyVAD()
        res_speech = vad.detect(speech, fs=fs)
        assert res_speech.speech_ratio > 0.5
        assert len(res_speech.segments_ms) >= 1

        silence = np.zeros(32000, dtype=np.float32)
        res_silence = vad.detect(silence, fs=fs)
        assert res_silence.speech_ratio == 0.0
        assert len(res_silence.segments_ms) == 0

    def test_vad_short_click_discarded(self):
        # 50 ms click (< min_speech_ms of 120 ms)
        fs = 16000
        click = np.zeros(16000, dtype=np.float32)
        click[1000:1800] = 0.8  # 800 samples = 50 ms
        vad = EnergyVAD()
        res = vad.detect(click, fs=fs)
        # click should be filtered out by min_speech_ms
        assert len(res.segments_ms) == 0


class TestASR:
    def test_asr_lifecycle_and_validation(self):
        asr = WhisperASR("tiny")
        assert not asr.loaded

        buf_wrong_fs = AudioBuffer(samples=np.zeros(8000, dtype=np.float32), fs=8000)
        with pytest.raises(RuntimeError, match="belum dimuat"):
            asr.transcribe(buf_wrong_fs)

        # Mock model to avoid downloading model weights in unit test
        mock_model = MagicMock()
        mock_segment = MagicMock()
        mock_segment.start = 0.0
        mock_segment.end = 2.0
        mock_segment.text = "halo ruka"
        mock_info = MagicMock()
        mock_info.language = "id"
        mock_model.transcribe.return_value = ([mock_segment], mock_info)

        asr._model = mock_model
        assert asr.loaded

        with pytest.raises(ValueError, match="ASR butuh 16000 Hz"):
            asr.transcribe(buf_wrong_fs)

        buf = AudioBuffer(samples=np.zeros(32000, dtype=np.float32), fs=16000)
        tr = asr.transcribe(buf, language="id")
        assert tr.text == "halo ruka"
        assert tr.language == "id"
        assert tr.duration_s == 2.0
        assert tr.latency_s >= 0.0
        assert len(tr.segments) == 1

        # Test transcribe_segments
        segs = asr.transcribe_segments(np.zeros(32000, dtype=np.float32), [(0, 1000)])
        assert len(segs) == 1
        assert segs[0].text == "halo ruka"


class TestSpeaker:
    def test_mfcc_shape_and_values(self):
        t = np.arange(16000) / 16000.0
        sig = (0.5 * np.sin(2 * np.pi * 200 * t)).astype(np.float32)
        feats = mfcc(sig, fs=16000, n_mfcc=20)
        assert feats.ndim == 2
        assert feats.shape[1] == 20
        assert np.all(np.isfinite(feats))

    def test_speaker_profile_roundtrip(self):
        prof = SpeakerProfile(
            profile_id="bos",
            mean=np.ones(20),
            cov_diag=np.ones(20) * 0.5,
            n_frames=100,
            created_at_ms=12345,
            variance_floor=1e-4,
        )
        d = prof.as_dict()
        prof2 = SpeakerProfile.from_dict(d)
        assert prof2.profile_id == prof.profile_id
        assert np.allclose(prof2.mean, prof.mean)
        assert np.allclose(prof2.cov_diag, prof.cov_diag)
        assert prof2.n_frames == prof.n_frames

    def test_acoustic_gaussian_provider_enroll_and_verify(self):
        np.random.seed(42)
        fs = 16000
        t = np.arange(32000) / fs
        # 2s speaker A (pitch 150 Hz + harmonics/noise)
        sig_a = (0.5 * np.sin(2 * np.pi * 150 * t) + 0.05 * np.random.randn(len(t))).astype(np.float32)
        sig_a_test = (0.5 * np.sin(2 * np.pi * 150 * t) + 0.05 * np.random.randn(len(t))).astype(np.float32)
        # 2s speaker B (pitch 300 Hz + harmonics/noise)
        sig_b = (0.5 * np.sin(2 * np.pi * 300 * t) + 0.05 * np.random.randn(len(t))).astype(np.float32)

        prov = AcousticGaussianProvider(threshold=0.0)

        # short enrollment rejected (< 40 frames)
        with pytest.raises(ValueError, match="butuh ≥40 frame"):
            prov.enroll("short", sig_a[:300])

        prov.enroll("speaker_a", sig_a)
        prov.enroll("speaker_b", sig_b)

        q = prov.enrollment_quality("speaker_a")
        assert q.score > 0.0
        assert q.n_frames >= 40

        # Verify matching speaker
        llr_a, verdict_a = prov.verify(sig_a_test, "speaker_a")
        assert llr_a > 0.0
        assert verdict_a == "ACCEPT"

        # Verify impostor speaker B against claimed speaker A
        llr_b, verdict_b = prov.verify(sig_b, "speaker_a")
        assert llr_b < llr_a

        # 1 kHz pure tone against speech profile
        pure_tone = (0.5 * np.sin(2 * np.pi * 1000 * t)).astype(np.float32)
        llr_tone, verdict_tone = prov.verify(pure_tone, "speaker_a")
        assert llr_tone < 0.0
        assert verdict_tone == "REJECT"

        # Non-existent profile
        llr_none, verdict_none = prov.verify(sig_a, "unknown")
        assert verdict_none == "NO_PROFILE"

        # Identify
        best_id, best_llr = prov.identify(sig_a)
        assert best_id == "speaker_a"

        # Calibration
        rep = prov.calibrate(
            genuine={"speaker_a": [sig_a], "speaker_b": [sig_b]},
            impostor_pairs=[("speaker_a", sig_b), ("speaker_b", sig_a)],
        )
        assert "eer_threshold" in rep
        assert prov.capability()["available"] is True

    def test_external_dvector_provider(self):
        ext = ExternalDVectorProvider()
        assert ext.capability()["available"] is False

        with pytest.raises(RuntimeError, match="belum diikat"):
            ext.embed(np.zeros(16000, dtype=np.float32))

        with pytest.raises(ValueError, match="callable"):
            ext.bind_embed_function("not_callable")

        mock_embed = lambda samples, fs: np.ones(128, dtype=np.float32)
        ext.bind_embed_function(mock_embed)
        out = ext.embed(np.zeros(16000, dtype=np.float32))
        assert out.shape == (128,)
        assert ext.capability()["available"] is True
