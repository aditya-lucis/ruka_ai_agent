# -*- coding: utf-8 -*-
"""Living Presence Engine 60 Hz (FR-PR-01, FR-PR-08, FR-PR-09, FR-PR-10).

Mesin kehadiran visual 60 Hz murni matematika & fisika pegas:
- Berjalan di thread terpisah dengan anggaran frame 16.67 ms (0 token LLM, CPU < 1%)
- Tangga penurunan kualitas bertingkat (Full -> No secondary -> Low LOD -> 30 fps)
- Mode hemat mengantuk (Sleep Mode) 12 fps dengan waktu bangun < 1 detik
- Publikasi berkala ke EventBus V3 pada OrganNamespace.PRESENCE
"""
from __future__ import annotations

import logging
import math
import threading
import time
from typing import Optional

from src.gateway.events import Event, EventBus, OrganNamespace
from src.presence.attention import AttentionEngine
from src.presence.blinking import BlinkingEngine
from src.presence.breathing import BreathingEngine
from src.presence.models import (
    AttentionTarget,
    BreathingState,
    DegradationLevel,
    EarPose,
    MoodState,
    PresenceFrame,
    TailPose,
    ValenceArousal,
)
from src.presence.mood_fsm import MoodStateMachine
from src.presence.observability import PresenceRingBuffer
from src.presence.spring_physics import EarPhysicsEngine, TailPhysicsEngine

log = logging.getLogger("ruka.presence.engine")


class LivingPresenceEngine:
    def __init__(
        self,
        event_bus: Optional[EventBus] = None,
        target_fps: float = 60.0,
    ) -> None:
        self.event_bus = event_bus
        self.target_fps = target_fps
        self.frame_budget_s = 1.0 / target_fps  # 16.67 ms

        self.breathing = BreathingEngine()
        self.blinking = BlinkingEngine()
        self.ear_physics = EarPhysicsEngine()
        self.tail_physics = TailPhysicsEngine()
        self.mood_fsm = MoodStateMachine(event_bus=event_bus)
        self.attention = AttentionEngine(on_ear_flick_needed=self._on_ear_flick)
        self.observability = PresenceRingBuffer(capacity=18000)

        self._running: bool = False
        self._thread: Optional[threading.Thread] = None
        self._lock = threading.RLock()

        self._frame_index: int = 0
        self._start_time: float = time.time()
        self._last_user_activity: float = time.time()
        self._is_sleep_mode: bool = False
        self._degradation: DegradationLevel = DegradationLevel.FULL
        self._latest_frame: Optional[PresenceFrame] = None

    def _on_ear_flick(self) -> None:
        self.ear_physics.trigger_flick(duration_s=0.15)

    @property
    def is_running(self) -> bool:
        return self._running

    @property
    def latest_frame(self) -> Optional[PresenceFrame]:
        with self._lock:
            return self._latest_frame

    def notify_user_activity(self) -> None:
        """Membangunkan RUKA seketika jika dalam mode tidur (< 1 detik)."""
        with self._lock:
            self._last_user_activity = time.time()
            if self._is_sleep_mode:
                self._is_sleep_mode = False
                self.mood_fsm.update_va(0.3, -0.1, immediate=True)

    def set_sleep_mode(self, active: bool) -> None:
        """Mengatur mode tidur 12 fps secara eksplisit."""
        with self._lock:
            self._is_sleep_mode = active
            if active:
                self.mood_fsm.update_va(0.0, -0.8, immediate=True)

    def step_frame(self, dt: float) -> PresenceFrame:
        """Mengeksekusi satu siklus kalkulasi frame kehadiran."""
        now = time.time()
        with self._lock:
            self._frame_index += 1
            frame_idx = self._frame_index

            # Periksa keaktifan idle > 600 detik -> Mode Tidur
            if (now - self._last_user_activity) > 600.0 and not self._is_sleep_mode:
                self._is_sleep_mode = True
                self.mood_fsm.update_va(0.0, -0.8, immediate=True)

            current_mood = self.mood_fsm.current_mood

            # 1. Hitung napas menganggur asimetris (FR-PR-02)
            breathing_state = self.breathing.compute(now, current_mood)

            # 2. Hitung kedipan mata Poisson (FR-PR-03)
            blink_l, blink_r = self.blinking.update(now, current_mood)

            # 3. Hitung kinamatika kepala & mata (FR-PR-05, FR-PR-06)
            head_yaw, head_pitch, eye_x, eye_y = self.attention.update_kinematics(dt)

            # 4. Fisika sekunder telinga & ekor (FR-PR-04) dengan tangga degradasi (FR-PR-09)
            if self._degradation == DegradationLevel.NO_SECONDARY or self._degradation == DegradationLevel.LOW_LOD:
                ear_pose = EarPose(left_angle_deg=0.0, right_angle_deg=0.0)
                tail_pose = TailPose(segments_deg=(0.0, 0.0, 0.0, 0.0, 0.0))
            else:
                target_ear_left = head_yaw * 0.2
                target_ear_right = -head_yaw * 0.2
                ear_pose = self.ear_physics.update(target_ear_left, target_ear_right, dt)

                # Goyangan ekor periodik
                tail_base_oscillation = 15.0 * math.sin(now * 1.5)
                tail_pose = self.tail_physics.update(tail_base_oscillation, now)

            frame = PresenceFrame(
                frame_index=frame_idx,
                timestamp=now,
                mood=current_mood,
                valence_arousal=self.mood_fsm.current_va,
                breathing=breathing_state,
                blink_left=blink_l,
                blink_right=blink_r,
                ear=ear_pose,
                tail=tail_pose,
                head_yaw_deg=head_yaw,
                head_pitch_deg=head_pitch,
                eye_look_x=eye_x,
                eye_look_y=eye_y,
                degradation=self._degradation,
                is_sleep_mode=self._is_sleep_mode,
            )
            self._latest_frame = frame
            return frame

    def _evaluate_degradation(self, p95_latency_ms: float) -> None:
        """Tangga penurunan kualitas bertangga (FR-PR-09)."""
        if p95_latency_ms > 16.6:
            self._degradation = DegradationLevel.HALF_FPS
        elif p95_latency_ms > 14.0:
            self._degradation = DegradationLevel.LOW_LOD
        elif p95_latency_ms > 12.0:
            self._degradation = DegradationLevel.NO_SECONDARY
        elif p95_latency_ms < 7.2:  # Histeresis pemulihan 0.6x dari 12ms
            self._degradation = DegradationLevel.FULL

    def _run_loop(self) -> None:
        last_time = time.perf_counter()
        publish_counter = 0

        while self._running:
            start_t = time.perf_counter()
            dt = start_t - last_time
            last_time = start_t

            # Eksekusi satu frame
            frame = self.step_frame(dt)

            elapsed_ms = (time.perf_counter() - start_t) * 1000.0
            self.observability.record(frame, elapsed_ms)

            # Evaluasi p95 setiap 120 frame (~2 detik)
            if frame.frame_index % 120 == 0:
                p95 = self.observability.calculate_p95_latency(last_n_frames=120)
                self._evaluate_degradation(p95)

            # Publikasikan status kehadiran ke EventBus V3 secara teratur (maks 60/15 fps)
            publish_counter += 1
            if self.event_bus and (publish_counter % 10 == 0):
                self.event_bus.publish(
                    Event(
                        namespace=OrganNamespace.PRESENCE.value,
                        event_type="presence.pose",
                        source="living_presence",
                        payload={
                            "frame": frame.frame_index,
                            "mood": frame.mood.value,
                            "chest_scale": frame.breathing.chest_scale,
                            "blink": frame.blink_left,
                            "head_yaw": frame.head_yaw_deg,
                            "head_pitch": frame.head_pitch_deg,
                            "degradation": frame.degradation.value,
                        },
                    )
                )

            # Penjadwalan frame: 12 fps saat tidur, 30 fps saat half_fps, 60 fps normal
            if self._is_sleep_mode:
                target_period = 1.0 / 12.0  # 83.3 ms
            elif self._degradation == DegradationLevel.HALF_FPS:
                target_period = 1.0 / 30.0  # 33.3 ms
            else:
                target_period = self.frame_budget_s  # 16.67 ms

            spent = time.perf_counter() - start_t
            sleep_duration = max(0.001, target_period - spent)
            time.sleep(sleep_duration)

    def start(self) -> None:
        with self._lock:
            if self._running:
                return
            self._running = True
            self._thread = threading.Thread(target=self._run_loop, daemon=True)
            self._thread.start()

    def stop(self) -> None:
        with self._lock:
            self._running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2.0)
