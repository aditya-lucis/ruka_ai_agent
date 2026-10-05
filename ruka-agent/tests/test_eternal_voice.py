# -*- coding: utf-8 -*-
"""Boss Gate 2 — Eternal Voice Test Suite (FR-VO).

Verifikasi:
- Boss Fight 3: TTFB < 200 ms, 0 rahasia terucap (100% token/kunci terfilter)
- 8 gaya prosodi mood Marquis dengan jepitan mutlak [-2.5, 2.5] semitone
- Viseme stream 25 fps untuk sinkronisasi avatar
- LRU phrase cache 96 entri dan invalidasi hash DNA suara
- EventBus V3 namespace voice.*
"""
import time
import pytest
from src.gateway.events import EventBus, OrganNamespace
from src.senses.voice import (
    EternalVoice,
    MarquisMood,
    ProsodyController,
    SecretScrubber,
    StreamingTTSEngine,
)


class TestSecretScrubber:
    def test_boss_fight_3_zero_secrets_vocalized(self):
        """Boss Fight 3: 0 rahasia terucap, seluruh token/kunci tersaring mutlak."""
        scrubber = SecretScrubber()

        test_cases = [
            ("API key OpenAI adalah sk-abcdef1234567890abcdef1234567890", "[KODE_RAHASIA]"),
            ("Token GitHub saya: ghp_123456789012345678901234567890123456", "[KODE_RAHASIA]"),
            ("Google API key: AIzaSyD9x7aBcDeFgHiJkLmNoPqRsTuVwXyZ123", "[KODE_RAHASIA]"),
            ("Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.doNotRevealSignatureToken12345", "[TOKEN_JWT_TERSEMBUNYI]"),
            ("AWS key AKIAIOSFODNN7EXAMPLE", "[KODE_RAHASIA]"),
            ("password: SuperSecretP@ssword123", "[KATA_SANDI_TERSEMBUNYI]"),
            ("postgres://admin:secret12345@localhost:5432/mydb", "[KONEKSI_DATABASE_TERSEMBUNYI]"),
            ("-----BEGIN RSA PRIVATE KEY-----\nMIIEowIBAAKCAQEA0\n-----END RSA PRIVATE KEY-----", "[KUNCI_PRIVAT_TERSEMBUNYI]"),
        ]

        for secret_text, expected_tag in test_cases:
            clean = scrubber.scrub(secret_text)
            # Pastikan teks rahasia asli tidak muncul sama sekali
            assert "sk-abc" not in clean
            assert "ghp_123" not in clean
            assert "AIzaSy" not in clean
            assert "SuperSecret" not in clean
            assert "secret12345" not in clean
            assert "BEGIN RSA" not in clean
            assert expected_tag in clean or "[KODE_RAHASIA]" in clean


class TestProsodyController:
    def test_eight_marquis_moods(self):
        controller = ProsodyController()
        moods = [
            MarquisMood.SASSY, MarquisMood.LOYAL, MarquisMood.ANALYTICAL,
            MarquisMood.DRAMATIC, MarquisMood.WHISPERED, MarquisMood.MOCKING,
            MarquisMood.PROTECTIVE, MarquisMood.NEUTRAL
        ]

        for m in moods:
            settings = controller.get_settings(m)
            assert -2.5 <= settings.pitch_semitones <= 2.5
            assert 0.75 <= settings.rate_multiplier <= 1.35
            assert 0.5 <= settings.energy_multiplier <= 1.5

    def test_pitch_clamping(self):
        controller = ProsodyController()
        # Offset ekstrim +10 semitone harus dijepit ke +2.5
        clamped_high = controller.get_settings(MarquisMood.SASSY, custom_pitch_offset=10.0)
        assert clamped_high.pitch_semitones == 2.5

        # Offset ekstrim -10 semitone harus dijepit ke -2.5
        clamped_low = controller.get_settings(MarquisMood.PROTECTIVE, custom_pitch_offset=-10.0)
        assert clamped_low.pitch_semitones == -2.5


class TestStreamingTTSEngine:
    def test_ttfb_and_phrase_cache(self):
        engine = StreamingTTSEngine(cache_capacity=96)
        controller = ProsodyController()
        prosody = controller.get_settings(MarquisMood.LOYAL)

        # 1. Panggilan pertama: sintesis nyata dengan TTFB < 200 ms
        chunks = list(engine.synthesize_stream("Selamat pagi My Lord, sistem siap.", prosody, mood=MarquisMood.LOYAL))
        assert len(chunks) > 0
        first_chunk = chunks[0]
        assert first_chunk.is_first_chunk is True
        assert first_chunk.ttfb_ms < 200.0
        assert len(first_chunk.visemes) > 0

        # 2. Panggilan kedua: hit cache LRU
        start_cache = time.perf_counter()
        cached_chunks = list(engine.synthesize_stream("Selamat pagi My Lord, sistem siap.", prosody, mood=MarquisMood.LOYAL))
        hit_latency_ms = (time.perf_counter() - start_cache) * 1000.0
        assert hit_latency_ms < 50.0
        assert len(cached_chunks) == len(chunks)

        # 3. Invalidasi cache jika DNA suara berubah
        engine.set_voice_dna(b"new_voice_actor_sample_v2")
        assert len(engine.cache) == 0


class TestEternalVoicePipeline:
    def test_speak_with_eventbus_and_visemes(self):
        bus = EventBus()
        voice = EternalVoice(event_bus=bus)

        events = []
        bus.subscribe("voice.*", lambda e: events.append(e))

        chunks = list(voice.speak("Perintah Anda telah saya laksanakan dengan sempurna, Young Lord.", mood=MarquisMood.SASSY))
        assert len(chunks) > 0

        bus.drain()
        topics = [e.event_type for e in events]
        assert "voice.speaking_start" in topics
        assert "voice.viseme" in topics
        assert "voice.speaking_stop" in topics
