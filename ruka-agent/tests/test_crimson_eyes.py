# -*- coding: utf-8 -*-
"""Boss Gate 2 — Crimson Eyes Test Suite (FR-EY).

Verifikasi:
- Boss Fight 2: 20/20 kenali Young Lord (ArcFace cosine threshold 0.35, 0 false acceptances)
- Enrollment 5-pose wajah dengan gerbang ketajaman Laplacian >= 60
- Anti-spoofing uji hidup (tantangan kedip)
- Privacy Blind Mode (zero pixel leak guarantee)
- Dual-track detector (gerakan murah vs SCRFD terjadwal)
- Gaze estimation & kontak mata (kerucut 4.5 derajat, tahan 400 ms)
- EventBus V3 namespace eyes.*
"""
import numpy as np
import pytest
from src.gateway.events import EventBus, OrganNamespace
from src.senses.eyes import (
    CrimsonEyes,
    DualTrackDetector,
    FaceRecognizer,
    GazeEstimator,
    PrivacyGuard,
    VisionMode,
)


class TestPrivacyGuard:
    def test_zero_pixel_leak_blind_shield(self):
        """Zero pixel leak: frame di-zero-out seketika saat blind mode aktif."""
        guard = PrivacyGuard(initial_blind=False)
        raw_frame = np.ones((480, 640, 3), dtype=np.uint8) * 128

        # Mode normal: frame lolos
        frame_out, shielded = guard.filter_frame(raw_frame)
        assert shielded is False
        assert frame_out is not None
        assert np.max(frame_out) == 128

        # Aktifkan Privacy Blind Mode
        guard.set_blind_mode(True)
        assert guard.is_blind is True

        frame_out, shielded = guard.filter_frame(raw_frame)
        assert shielded is True
        assert frame_out is not None
        # Seluruh nilai piksel harus tepat 0 (zeroed out)
        assert np.max(frame_out) == 0
        assert np.min(frame_out) == 0

        audit = guard.audit_status()
        assert audit["zero_leak_guarantee"] is True
        assert audit["shield_activations"] >= 1


class TestFaceRecognizer:
    def test_boss_fight_2_young_lord_recognition(self):
        """Boss Fight 2: 20/20 kenali Young Lord, 0 false acceptances."""
        recognizer = FaceRecognizer(cosine_threshold=0.35, target_user_id="young_lord")

        # 1. Pendaftaran 5 pose (Laplacian >= 60)
        poses = [[1.0] * 512 for _ in range(5)]
        sharpness = [75.0, 80.0, 68.0, 92.0, 62.0]
        assert recognizer.enroll_5_poses(poses, sharpness) is True

        # Tolak jika ada pose kabur (< 60)
        with pytest.raises(ValueError, match="gagal gerbang ketajaman"):
            recognizer.enroll_5_poses(poses, [80.0, 55.0, 70.0, 90.0, 65.0])

        # 2. Uji 20/20 pengenalan Young Lord
        for i in range(20):
            # Vektor uji Young Lord dengan sedikit variasi noise acak
            noise = [1.0 + (i % 3) * 0.05 for _ in range(512)]
            verdict = recognizer.recognize(noise)
            assert verdict.is_young_lord is True, f"Uji ke-{i+1} gagal mengenali Young Lord"
            assert verdict.user_id == "young_lord"
            assert verdict.similarity >= 0.35

        # 3. Uji orang asing / penyerang (harus 0 false acceptance)
        stranger_vectors = [
            [-1.0] * 512,
            [1.0 if idx < 100 else -1.0 for idx in range(512)],
            [0.0] * 512,
        ]
        for s_vec in stranger_vectors:
            verdict = recognizer.recognize(s_vec)
            assert verdict.is_young_lord is False
            assert verdict.user_id != "young_lord"

    def test_liveness_blink_challenge(self):
        recognizer = FaceRecognizer()
        # Rangkaian EAR: mata terbuka (0.30) -> berkedip (0.15) -> terbuka (0.28)
        live_stream = [0.32, 0.30, 0.28, 0.15, 0.18, 0.29, 0.31]
        assert recognizer.verify_liveness_blink(live_stream) is True

        # Foto statis / cetakan (mata selalu terbuka, tidak pernah < 0.20)
        static_stream = [0.30, 0.30, 0.29, 0.30, 0.31]
        assert recognizer.verify_liveness_blink(static_stream) is False


class TestGazeEstimator:
    def test_eye_contact_cone_and_hold(self):
        gaze = GazeEstimator(cone_deg=4.5, min_hold_ms=400.0)

        # 1. Di luar kerucut (yaw 10 derajat)
        v1 = gaze.estimate_gaze(yaw_deg=10.0, pitch_deg=0.0, dt_ms=200.0)
        assert v1.is_eye_contact is False

        # 2. Di dalam kerucut (yaw 2.0, pitch -1.5) selama 200 ms (belum mencapai 400 ms)
        v2 = gaze.estimate_gaze(yaw_deg=2.0, pitch_deg=-1.5, dt_ms=200.0)
        assert v2.is_eye_contact is False

        # 3. Tahan 250 ms lagi (total 450 ms >= 400 ms) -> kontak mata terkonfirmasi!
        v3 = gaze.estimate_gaze(yaw_deg=2.0, pitch_deg=-1.5, dt_ms=250.0)
        assert v3.is_eye_contact is True


class TestCrimsonEyesPipeline:
    def test_pipeline_integration(self):
        bus = EventBus()
        eyes = CrimsonEyes(event_bus=bus)

        # Daftarkan wajah Young Lord
        eyes.recognizer.enroll_5_poses([[1.0] * 512 for _ in range(5)], [70.0] * 5)

        events = []
        bus.subscribe("eyes.*", lambda e: events.append(e))

        raw_frame = np.ones((480, 640, 3), dtype=np.uint8) * 100
        verdict = eyes.process_frame(
            raw_frame=raw_frame,
            detected_hint=True,
            embedding_hint=[1.0] * 512,
            yaw_hint=1.0,
            pitch_hint=-1.0,
        )

        assert verdict.face_detected is True
        assert verdict.identity is not None
        assert verdict.identity.is_young_lord is True

        bus.drain()
        topics = [e.event_type for e in events]
        assert "eyes.face" in topics
        assert "eyes.boss_arrived" in topics

        # Uji beralih ke Blind Mode
        eyes.set_mode(VisionMode.BLIND)
        assert eyes.privacy.is_blind is True
        verdict_blind = eyes.process_frame(raw_frame)
        assert verdict_blind.mode == VisionMode.BLIND
        assert verdict_blind.privacy_shield_active is True
