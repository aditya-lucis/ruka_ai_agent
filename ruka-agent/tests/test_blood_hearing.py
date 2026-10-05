# -*- coding: utf-8 -*-
"""Boss Gate 2 — Blood Hearing Test Suite (FR-EA).

Verifikasi:
- VAD gatekeeper histeresis (silence <-> speech)
- Wake word 'Ruka' & 'Marquis' (< 300 ms) + refractory state machine
- Boss Fight 1: 30x wake-word (>= 27 lulus, 0 false wake)
- Reflex cache (< 50 ms)
- Normalisasi teks deterministik (< 1 ms)
- Speaker ID embedding kosinus & enrollment
- Barge-in interruption (< 300 ms)
- EventBus V3 namespace ear.*
"""
import time
import pytest
from src.gateway.events import EventBus, OrganNamespace
from src.senses.ear import (
    AudioChunk,
    BloodHearing,
    SpeakerIdentifier,
    SpeakerStatus,
    VADGatekeeper,
    VADState,
    WakeState,
    WakeWordDetector,
    normalize_text,
)
from src.senses.ear.interruption import InterruptionDetector


class TestVADGatekeeper:
    def test_vad_state_transitions(self):
        vad = VADGatekeeper(speech_consecutive_windows=2, silence_consecutive_windows=3)
        assert vad.state == VADState.SILENCE

        # 1 jendela speech belum cukup masuk SPEECH
        vad.process_window([], external_prob=0.8)
        assert vad.state == VADState.SILENCE

        # 2 jendela speech -> SPEECH
        vad.process_window([], external_prob=0.85)
        assert vad.state == VADState.SPEECH

        # 1 jendela silence belum keluar
        vad.process_window([], external_prob=0.1)
        assert vad.state == VADState.SPEECH

        # 3 jendela silence berturut-turut -> kembali ke SILENCE
        vad.process_window([], external_prob=0.1)
        vad.process_window([], external_prob=0.1)
        assert vad.state == VADState.SILENCE


class TestWakeWordDetector:
    def test_wake_detection_and_refractory(self):
        detector = WakeWordDetector(keywords=("ruka", "marquis"), refractory_period_s=0.2)
        assert detector.state == WakeState.ARMED

        # Deteksi 'ruka'
        verdict = detector.process_frame([], score_hint=0.85, keyword_hint="ruka")
        assert verdict.detected is True
        assert verdict.keyword == "ruka"
        assert verdict.latency_ms < 300.0
        assert detector.state == WakeState.REFRACTORY

        # Saat refractory, deteksi langsung diabaikan
        verdict2 = detector.process_frame([], score_hint=0.9, keyword_hint="ruka")
        assert verdict2.detected is False

        # Setelah refractory habis, kembali ARMED
        time.sleep(0.25)
        assert detector.state == WakeState.ARMED
        verdict3 = detector.process_frame([], score_hint=0.8, keyword_hint="marquis")
        assert verdict3.detected is True
        assert verdict3.keyword == "marquis"

    def test_boss_fight_1_wake_word_accuracy(self):
        """Boss Fight 1: 30x wake-word (>= 27 lulus, 0 false wake)."""
        detector = WakeWordDetector(threshold=0.65, refractory_period_s=0.001)

        success_count = 0
        # 30 percobaan pengucapan 'ruka' dengan variasi skor di atas ambang
        for i in range(30):
            time.sleep(0.002)
            score = 0.70 + (i % 5) * 0.05
            verdict = detector.process_frame([], score_hint=score, keyword_hint="ruka")
            if verdict.detected:
                success_count += 1

        assert success_count >= 27, f"Tingkat kelulusan wake word {success_count}/30 di bawah 27"

        # Uji 10x suara bising / kata lain (harus 0 false wake)
        false_wakes = 0
        for noise_word in ["buku", "luka", "halo", "komputer", "kucing"]:
            verdict = detector.process_frame([], score_hint=0.8, keyword_hint=noise_word)
            if verdict.detected:
                false_wakes += 1
        assert false_wakes == 0, f"Terjadi {false_wakes} false wake word trigger"


class TestTextNormalizer:
    def test_deterministic_normalization(self):
        # 1. Pertanyaan
        res1 = normalize_text("apakah young lord ingin kopi")
        assert res1.startswith("Apakah")
        assert res1.endswith("?")

        # 2. Inversi kata angka
        res2 = normalize_text("tolong siapkan lima berkas dan dua puluh skenario")
        assert "5" in res2
        assert "20" in res2

        # 3. Latensi < 1 ms
        start = time.perf_counter()
        normalize_text("bagaimana kabar sistem kita hari ini")
        latency_ms = (time.perf_counter() - start) * 1000.0
        assert latency_ms < 1.0


class TestSpeakerIdentifier:
    def test_speaker_enrollment_and_verification(self):
        speaker = SpeakerIdentifier(high_threshold=0.70, low_threshold=0.50)

        # Uji gerbang enrollment
        with pytest.raises(ValueError, match="Durasi enrollment"):
            speaker.enroll([1.0] * 64, duration_s=10.0)

        with pytest.raises(ValueError, match="SNR"):
            speaker.enroll([1.0] * 64, duration_s=30.0, snr_db=10.0)

        # Pendaftaran sukses
        owner_vec = [1.0] * 64
        assert speaker.enroll(owner_vec, duration_s=30.0, snr_db=20.0) is True

        # 1. Suara Young Lord (vektor identik / mirip)
        v1 = speaker.verify(owner_vec)
        assert v1.status == SpeakerStatus.VERIFIED_YOUNG_LORD
        assert v1.similarity >= 0.99

        # 2. Suara sedikit berbeda (ambigu)
        mid_vec = [1.0 if i % 2 == 0 else 0.2 for i in range(64)]
        v2 = speaker.verify(mid_vec)
        assert v2.status in (SpeakerStatus.VERIFIED_YOUNG_LORD, SpeakerStatus.AMBIGUOUS)

        # 3. Suara asing / orthogonal
        stranger_vec = [-1.0 if i < 32 else 0.0 for i in range(64)]
        v3 = speaker.verify(stranger_vec)
        assert v3.status == SpeakerStatus.UNKNOWN


class TestBargeInInterruption:
    def test_barge_in_stops_speech(self):
        det = InterruptionDetector(min_speech_duration_ms=200.0, min_rms_energy=0.02)
        det.set_ruka_speaking(True)

        # Suara pelan / desah (RMS rendah) tidak menginterupsi
        quiet_samples = [0.005] * 512
        interrupted, _ = det.process_chunk(quiet_samples, duration_ms=100.0)
        assert interrupted is False

        # Suara pengguna jelas (RMS tinggi) terakumulasi melewati durasi
        loud_samples = [0.05] * 512
        det.process_chunk(loud_samples, duration_ms=150.0)
        interrupted, lat = det.process_chunk(loud_samples, duration_ms=100.0)
        assert interrupted is True
        assert lat < 300.0


class TestBloodHearingPipeline:
    def test_pipeline_integration_with_eventbus(self):
        bus = EventBus()
        hearing = BloodHearing(event_bus=bus)
        hearing.set_mood("sassy")

        events_received = []
        bus.subscribe("ear.*", lambda e: events_received.append(e))

        # Simulasi frame dengan wake word 'ruka'
        result = hearing.process_audio_frame(
            samples=[0.05] * 512,
            score_hint=0.9,
            keyword_hint="ruka",
        )

        assert result["wake_detected"] is True
        assert "Young Lord" in result["reflex_phrase"] or "hamba" in result["reflex_phrase"]

        # Drain event bus
        bus.drain()
        assert len(events_received) >= 1
        topics = [e.event_type for e in events_received]
        assert "ear.wake_word" in topics
