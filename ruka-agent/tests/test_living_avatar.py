# -*- coding: utf-8 -*-
"""Test Suite for Living Avatar VRM Engine (FR-AV / Boss Gate 4)."""
from __future__ import annotations

import time
import pytest

from src.avatar.arbitrator import ChannelArbitrator
from src.avatar.engine import LivingAvatarEngine
from src.avatar.expressions import ExpressionLayerManager
from src.avatar.eye_animator import AvatarEyeAnimator
from src.avatar.idle_tree import IdleAnimationTree
from src.avatar.lip_sync import LipSyncEngine
from src.avatar.models import (
    ALL_SUPPORTED_BLENDSHAPES,
    CUSTOM_RUKA_BLENDSHAPES,
    BonePose,
    IdleBranch,
    PupilPose,
)
from src.avatar.verlet_physics import CapsuleCollider, VerletPhysicsEngine
from src.presence.models import MoodState


class TestChannelArbitrator:
    def test_single_writer_discipline(self):
        arb = ChannelArbitrator()

        # Bones hanya boleh ditulis presence
        assert arb.write_bones(BonePose(head_yaw=10.0), writer_id="presence") is True
        assert arb.write_bones(BonePose(head_yaw=20.0), writer_id="mood") is False

        # Visemes hanya boleh ditulis voice
        assert arb.write_viseme("A", 1.0, writer_id="voice") is True
        assert arb.write_viseme("O", 1.0, writer_id="eyes") is False

        # Pupils hanya boleh ditulis eyes
        assert arb.write_pupil(PupilPose(dilation=0.7), writer_id="eyes") is True
        assert arb.write_pupil(PupilPose(dilation=0.2), writer_id="presence") is False

    def test_viseme_persistence_120ms_retention(self):
        arb = ChannelArbitrator()
        arb.write_viseme("A", 1.0, writer_id="voice")

        # Frame segera: viseme A tetap aktif
        f1 = arb.render_frame()
        assert f1.viseme.viseme_id == "A"
        assert f1.viseme.weight == 1.0

        # Simulasikan selang waktu 150 ms (> 120 ms) tanpa update event
        arb._current_viseme = f1.viseme
        arb._current_viseme = type(f1.viseme)(
            viseme_id="A", weight=1.0, timestamp=time.time() - 0.150
        )
        f2 = arb.render_frame()
        # Harus otomatis teredam ke sil
        assert f2.viseme.viseme_id == "sil"
        assert f2.viseme.weight == 0.0


class TestLipSyncAndEyeDynamics:
    def test_lip_sync_min_vowel_duration(self):
        lip = LipSyncEngine()
        timeline = lip.generate_timed_visemes("halo", speech_rate_cps=20.0)
        vowel_visemes = [tv for tv in timeline if tv.viseme_id in ("A", "O")]
        assert len(vowel_visemes) >= 2
        for vv in vowel_visemes:
            # Minimal 70 ms (0.07 detik)
            assert vv.duration_s >= 0.070

    def test_eye_saccade_and_pupil_arousal_lag(self):
        animator = AvatarEyeAnimator(rng_seed=42)
        animator.set_target_dilation_from_arousal(1.0) # Pupil melebar

        dt = 0.016
        # Update langkah demi langkah mendekati target
        pupil_before = animator.current_dilation
        for _ in range(10):
            p = animator.update(current_time=1.0, dt=dt)
        # Menunjukkan kenaikan teredam (orde satu)
        assert p.dilation > pupil_before


class TestVerletPhysicsAndCapsuleColliders:
    def test_zero_penetration_capsule_collider(self):
        engine = VerletPhysicsEngine()
        # Letakkan partikel di dalam kapsul kepala (0.0, 1.55, 0.0, radius=0.12)
        p_idx = engine.add_particle(x=0.0, y=1.55, z=0.01, radius=0.02)

        # Lakukan langkah simulasi
        engine.step()

        p = engine.particles[p_idx]
        # Pastikan partikel terdorong keluar dari radius kapsul + radius partikel + epsilon (0.001)
        # Jarak dari sumbu kepala (x=0, z=0)
        dist_axis = (p.x**2 + p.z**2) ** 0.5
        min_allowed = 0.12 + 0.02 + 0.001
        assert dist_axis >= (min_allowed - 1e-4)


class TestIdleTreeAndExpressions:
    def test_idle_tree_max_two_repeats(self):
        tree = IdleAnimationTree(rng_seed=10)
        history: list[IdleBranch] = []

        for _ in range(25):
            branch = tree.select_next_branch(mood=MoodState.VAMPIRE_NOBLE, energy=0.5)
            history.append(branch)

        # Verifikasi tidak ada cabang yang berulang lebih dari 2 kali berturut-turut
        repeat_streak = 1
        for i in range(1, len(history)):
            if history[i] == history[i - 1]:
                repeat_streak += 1
                assert repeat_streak <= 2, f"Cabang {history[i]} berulang {repeat_streak} kali!"
            else:
                repeat_streak = 1

    def test_blush_asymmetric_rise_decay(self):
        layer = ExpressionLayerManager()
        layer.trigger_blush(intensity=1.0)

        # Naik selama 1.2 detik
        layer.update(dt=0.6)
        assert 0.4 <= layer.blush_intensity <= 0.6
        layer.update(dt=0.7)
        assert layer.blush_intensity == 1.0

        # Luruh perlahan (8.0 detik)
        layer.update(dt=4.0)
        assert 0.4 <= layer.blush_intensity <= 0.6


class TestLivingAvatarEngineAPI:
    def test_public_api_and_morph_cache(self):
        engine = LivingAvatarEngine()

        # set_expression dengan validasi nama keras
        assert engine.set_expression("mouthSmileLeft", 0.8) is True
        assert engine.set_expression("nonExistentBlendshape", 0.8) is False

        # set_viseme
        assert engine.set_viseme("E", 1.0) is True

        # get_pose
        frame = engine.get_pose()
        assert frame.blendshapes["mouthSmileLeft"] == 0.8
        assert frame.viseme.viseme_id == "E"

        # Morph LRU Cache
        engine.cache_morph_state("smile_noble", {"mouthSmileLeft": 0.8, "fangs": 0.5})
        cached = engine.get_cached_morph_state("smile_noble")
        assert cached is not None
        assert cached["fangs"] == 0.5
