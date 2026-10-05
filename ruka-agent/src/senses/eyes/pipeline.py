# -*- coding: utf-8 -*-
"""Crimson Eyes Pipeline & Controller (FR-EY).

Pengendali terpadu modul penglihatan lokal Ruka / Project Noctis:
- 100% on-device vision dengan perlindungan privasi (PrivacyGuard)
- Arsitektur dua jalur (gerakan murah vs SCRFD/ArcFace terjadwal)
- Deteksi wajah, pengenalan Young Lord, estimasi arah pandang, dan kontak mata
- Terintegrasi dengan EventBus V3 pada OrganNamespace.EYES
"""
from __future__ import annotations

import time
from typing import Any, Sequence
import numpy as np

from src.gateway.events import Event, EventBus, OrganNamespace
from src.senses.eyes.detector import DualTrackDetector
from src.senses.eyes.gaze import GazeEstimator
from src.senses.eyes.models import (
    BoundingBox,
    FaceIdentity,
    GazeVector,
    VisionFrameVerdict,
    VisionMode,
)
from src.senses.eyes.privacy import PrivacyGuard
from src.senses.eyes.recognizer import FaceRecognizer


class CrimsonEyes:
    def __init__(
        self,
        event_bus: EventBus | None = None,
        initial_mode: VisionMode = VisionMode.NORMAL,
    ) -> None:
        self.event_bus = event_bus
        self.privacy = PrivacyGuard(initial_blind=(initial_mode == VisionMode.BLIND))
        self.detector = DualTrackDetector()
        self.recognizer = FaceRecognizer()
        self.gaze = GazeEstimator()
        self._mode: VisionMode = initial_mode
        self._was_present: bool = False

    @property
    def mode(self) -> VisionMode:
        return self._mode

    def set_mode(self, mode: VisionMode) -> None:
        self._mode = mode
        self.privacy.set_blind_mode(mode == VisionMode.BLIND)
        if self.event_bus and mode == VisionMode.BLIND:
            self.event_bus.publish(
                Event(
                    namespace=OrganNamespace.EYES.value,
                    event_type="eyes.privacy_audit",
                    source="crimson_eyes",
                    payload={"blind_mode": True, "zero_leak": True},
                )
            )

    def process_frame(
        self,
        raw_frame: np.ndarray,
        detected_hint: bool | None = None,
        bbox_hint: BoundingBox | None = None,
        embedding_hint: Sequence[float] | None = None,
        yaw_hint: float = 0.0,
        pitch_hint: float = 0.0,
        now: float | None = None,
    ) -> VisionFrameVerdict:
        """Memproses satu frame visual melalui seluruh rantai evaluasi indra mata."""
        start_t = time.perf_counter()

        # 1. Tapis privasi mutlak (Blind Shield)
        safe_frame, was_shielded = self.privacy.filter_frame(raw_frame)

        if was_shielded or safe_frame is None:
            latency_ms = (time.perf_counter() - start_t) * 1000.0
            return VisionFrameVerdict(
                mode=VisionMode.BLIND,
                motion_score=0.0,
                face_detected=False,
                privacy_shield_active=True,
                latency_ms=latency_ms,
            )

        # 2. Jalur Murah: Skor Gerakan
        motion = self.detector.calculate_motion(safe_frame)

        # 3. Jalur Deteksi Wajah
        has_face, bbox = self.detector.run_detection(
            safe_frame,
            motion_score=motion,
            detected_hint=detected_hint,
            bbox_hint=bbox_hint,
            now=now,
        )

        identity: FaceIdentity | None = None
        gaze_vector: GazeVector | None = None

        if has_face and embedding_hint:
            # 4. Pengenalan Wajah ArcFace
            identity = self.recognizer.recognize(embedding_hint)

            # 5. Estimasi Pandangan & Kontak Mata
            gaze_vector = self.gaze.estimate_gaze(yaw_deg=yaw_hint, pitch_deg=pitch_hint)

            # Deteksi kedatangan Young Lord (boss_arrived)
            if identity.is_young_lord and not self._was_present:
                self._was_present = True
                if self.event_bus:
                    self.event_bus.publish(
                        Event(
                            namespace=OrganNamespace.EYES.value,
                            event_type="eyes.boss_arrived",
                            source="crimson_eyes",
                            payload={"similarity": identity.similarity},
                        )
                    )

            if self.event_bus:
                self.event_bus.publish(
                    Event(
                        namespace=OrganNamespace.EYES.value,
                        event_type="eyes.face",
                        source="crimson_eyes",
                        payload={
                            "user_id": identity.user_id,
                            "similarity": identity.similarity,
                            "is_young_lord": identity.is_young_lord,
                        },
                    )
                )
                self.event_bus.publish(
                    Event(
                        namespace=OrganNamespace.EYES.value,
                        event_type="eyes.gaze",
                        source="crimson_eyes",
                        payload={
                            "yaw": gaze_vector.yaw_deg,
                            "pitch": gaze_vector.pitch_deg,
                            "is_eye_contact": gaze_vector.is_eye_contact,
                        },
                    )
                )
        elif not has_face:
            self._was_present = False

        latency_ms = (time.perf_counter() - start_t) * 1000.0

        return VisionFrameVerdict(
            mode=self._mode,
            motion_score=motion,
            face_detected=has_face,
            bbox=bbox,
            identity=identity,
            gaze=gaze_vector,
            privacy_shield_active=False,
            latency_ms=latency_ms,
        )
