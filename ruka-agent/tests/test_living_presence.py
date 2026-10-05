# -*- coding: utf-8 -*-
"""Test Suite for Living Presence Engine (FR-PR / Boss Gate 4)."""
from __future__ import annotations

import time
import pytest

from src.gateway.events import EventBus
from src.presence.attention import AttentionEngine
from src.presence.blinking import BlinkingEngine
from src.presence.breathing import BreathingEngine
from src.presence.engine import LivingPresenceEngine
from src.presence.models import (
    AttentionTarget,
    DegradationLevel,
    MoodState,
    ValenceArousal,
)
from src.presence.mood_fsm import MoodStateMachine
from src.presence.observability import (
    PresenceRingBuffer,
    compute_frame_phash_64,
    hamming_distance,
    is_visual_regression,
)
from src.presence.spring_physics import EarPhysicsEngine, TailPhysicsEngine


class TestBreathingEngine:
    def test_calm_idle_breathing_asymmetry(self):
        engine = BreathingEngine()
        # Siklus tenang: periode 4.0s (15 bpm), inhale 1.6s, exhale 2.4s, skala 1.0 s.d. 1.04
        b_inhale = engine.compute(0.8, MoodState.CALM)
        assert b_inhale.is_inhale is True
        assert 1.0 <= b_inhale.chest_scale <= 1.04

        b_peak = engine.compute(1.6, MoodState.CALM)
        assert 1.035 <= b_peak.chest_scale <= 1.045

        b_exhale = engine.compute(2.8, MoodState.CALM)
        assert b_exhale.is_inhale is False
        assert 1.0 <= b_exhale.chest_scale <= 1.04

    def test_sleepy_pranayama_478_pattern(self):
        engine = BreathingEngine()
        # Siklus mengantuk: total 19.0s (Inhale 4s, Hold 7s, Exhale 8s)
        b_in = engine.compute(2.0, MoodState.SLEEPY)
        assert b_in.is_inhale is True
        assert 1.0 < b_in.chest_scale <= 1.03

        b_hold = engine.compute(6.0, MoodState.SLEEPY)
        assert b_hold.is_inhale is False
        assert b_hold.chest_scale == 1.03

        b_ex = engine.compute(15.0, MoodState.SLEEPY)
        assert b_ex.is_inhale is False
        assert 1.0 <= b_ex.chest_scale <= 1.03


class TestBlinkingEngine:
    def test_poisson_blinking_and_double_blink(self):
        engine = BlinkingEngine(rng_seed=42)
        blinks_detected = 0
        current_t = 0.0
        dt = 0.016  # 60 fps step

        # Simulasi 30 detik
        while current_t < 30.0:
            bl, br = engine.update(current_t, MoodState.CALM)
            assert bl == br
            assert 0.0 <= bl <= 1.0
            if bl > 0.8:
                blinks_detected += 1
            current_t += dt

        assert blinks_detected > 0


class TestSpringPhysics:
    def test_second_order_ear_spring(self):
        engine = EarPhysicsEngine()
        # Simulasikan respon terhadap target sudut 30 derajat
        pose = engine.update(target_left=30.0, target_right=-30.0, dt=0.016)
        assert isinstance(pose.left_angle_deg, float)

        # Trigger flick
        engine.trigger_flick(0.15)
        pose_flick = engine.update(target_left=30.0, target_right=-30.0, dt=0.016)
        assert pose_flick.flick_active is True

    def test_five_segment_tail_whip_amplification(self):
        engine = TailPhysicsEngine(delay_per_segment_ms=75.0)
        t = 1.0
        pose = engine.update(base_angle_deg=10.0, current_time=t)
        assert len(pose.segments_deg) == 5
        assert pose.whip_intensity == 1.6
        # Amplitudo ujung memiliki faktor pengali terbesar
        assert engine.whip_factors[4] == 1.6


class TestAttentionAndKinematics:
    def test_salience_priority_and_prey_lock(self):
        engine = AttentionEngine()
        target_lord = AttentionTarget(target_id="lord", x=0.2, y=0.1, salience=1.0, priority=2.0)
        score_lord = engine.calculate_score(target_lord)
        assert score_lord == 2.0

        target_prey = AttentionTarget(target_id="cursor", x=0.5, y=0.5, salience=1.0, priority=1.0, is_prey_lock=True)
        score_prey = engine.calculate_score(target_prey)
        assert score_prey == 1.6  # 1.0 * 1.0 * 1.6

        # Focus gate menekan non-work
        engine.set_focus_gate(True)
        score_suppressed = engine.calculate_score(target_prey, is_work_related=False)
        assert score_suppressed == pytest.approx(1.6 * 0.3)

    def test_head_kinematics_anatomical_bounds(self):
        engine = AttentionEngine()
        engine.target_yaw_deg = 80.0  # melebihi batas 75
        engine.target_pitch_deg = 40.0 # melebihi batas 30

        # Update step
        yaw, pitch, eye_x, eye_y = engine.update_kinematics(dt=0.1)
        assert abs(yaw) <= 75.0
        assert abs(pitch) <= 30.0


class TestMoodFSM:
    def test_three_eval_hysteresis(self):
        bus = EventBus()
        fsm = MoodStateMachine(event_bus=bus, initial_mood=MoodState.CALM)

        # Usulan perubahan ke HAPPY (0.7, 0.4)
        # Evaluasi 1
        m1 = fsm.update_va(0.7, 0.4)
        assert m1 == MoodState.CALM  # belum berubah karena histeresis

        # Evaluasi 2
        m2 = fsm.update_va(0.7, 0.4)
        assert m2 == MoodState.CALM  # masih menunggu konfirmasi ke-3

        # Evaluasi 3
        m3 = fsm.update_va(0.7, 0.4)
        assert m3 == MoodState.HAPPY  # berubah setelah 3 evaluasi berturut-turut!


class TestPresenceObservabilityAndPHash:
    def test_ring_buffer_and_p95(self):
        buffer = PresenceRingBuffer(capacity=100)
        engine = LivingPresenceEngine()
        frame = engine.step_frame(0.016)

        for i in range(50):
            buffer.record(frame, frame_duration_ms=10.0 + (i % 5))

        p95 = buffer.calculate_p95_latency(last_n_frames=50)
        assert 10.0 <= p95 <= 15.0

    def test_golden_frame_perceptual_hash(self):
        engine = LivingPresenceEngine()
        f1 = engine.step_frame(0.016)
        h1 = compute_frame_phash_64(f1)

        # Frame yang identik atau sangat mirip harus memiliki Hamming distance <= 10
        dist_self = hamming_distance(h1, h1)
        assert dist_self == 0
        assert not is_visual_regression(h1, h1, threshold=10)


class TestLivingPresenceEngine:
    def test_frame_generation_without_llm(self):
        bus = EventBus()
        engine = LivingPresenceEngine(event_bus=bus)

        frame = engine.step_frame(dt=0.016)
        assert frame.frame_index == 1
        assert frame.degradation == DegradationLevel.FULL
        assert 1.0 <= frame.breathing.chest_scale <= 1.05
        assert abs(frame.head_yaw_deg) <= 75.0

    def test_sleep_mode_activation_and_wake(self):
        engine = LivingPresenceEngine()
        engine.set_sleep_mode(True)
        assert engine.latest_frame is None or engine._is_sleep_mode

        f = engine.step_frame(dt=0.016)
        assert f.is_sleep_mode is True

        # Wake up seketika saat ada aktivitas pengguna
        engine.notify_user_activity()
        f_wake = engine.step_frame(dt=0.016)
        assert f_wake.is_sleep_mode is False
