# -*- coding: utf-8 -*-
"""Attention System & Anatomical Gaze/Head Tracking (FR-PR-05, FR-PR-06).

Sistem perhatian biologis dan kinematis kepala RUKA:
- Skor perhatian: Salience * Priority
- Tahan target minimal: 800 ms (mencegah saccade liar)
- Kunci mangsa (Prey lock): Pengali 1.6x
- Gerbang fokus (Focus gate): Menekan target non-kerja hingga 0.3x
- Batas anatomis kepala:
  * Yaw maksimum: 75 derajat
  * Pitch maksimum: 30 derajat
  * Dead zone: 5 derajat (tidak bergerak jika di bawah 5 derajat)
  * Kecepatan maksimum: 240 derajat per detik
  * Kedutan telinga (ear flick) aktif 150 ms sebelum rotasi kepala 300 ms
"""
from __future__ import annotations

import math
import time
from typing import Callable, Optional
from src.presence.models import AttentionTarget


class AttentionEngine:
    def __init__(
        self,
        min_hold_duration_s: float = 0.80,  # 800 ms
        on_ear_flick_needed: Optional[Callable[[], None]] = None,
    ) -> None:
        self.min_hold_duration_s = min_hold_duration_s
        self.on_ear_flick_needed = on_ear_flick_needed

        self.current_target: Optional[AttentionTarget] = None
        self.target_acquired_time: float = 0.0
        self.focus_gate_active: bool = False

        # Status kinematis kepala
        self.current_yaw_deg: float = 0.0
        self.current_pitch_deg: float = 0.0
        self.target_yaw_deg: float = 0.0
        self.target_pitch_deg: float = 0.0

        # Koordinat bola mata [-1.0, 1.0]
        self.eye_look_x: float = 0.0
        self.eye_look_y: float = 0.0

        self.max_speed_deg_per_s: float = 240.0
        self.dead_zone_deg: float = 5.0
        self.max_yaw_deg: float = 75.0
        self.max_pitch_deg: float = 30.0

    def set_focus_gate(self, active: bool) -> None:
        """Mengaktifkan gerbang fokus saat sedang bekerja."""
        self.focus_gate_active = active

    def calculate_score(self, target: AttentionTarget, is_work_related: bool = True) -> float:
        """Menghitung skor salience dengan pembobotan prioritas, prey lock, dan focus gate."""
        score = target.salience * target.priority
        if target.is_prey_lock:
            score *= 1.6
        if self.focus_gate_active and not is_work_related:
            score *= 0.3
        return score

    def evaluate_targets(
        self,
        candidates: list[tuple[AttentionTarget, bool]],
        current_time: float,
    ) -> Optional[AttentionTarget]:
        """Menentukan target perhatian terbaik dengan histeresis minimal 800 ms."""
        if not candidates:
            return self.current_target

        best_target = None
        best_score = -1.0
        for target, is_work in candidates:
            score = self.calculate_score(target, is_work_related=is_work)
            if score > best_score:
                best_score = score
                best_target = target

        # Periksa apakah target saat ini masih dalam batas minimal tahan (800 ms)
        if self.current_target is not None:
            time_held = current_time - self.target_acquired_time
            if time_held < self.min_hold_duration_s:
                # Tahan target saat ini kecuali kandidat baru memiliki skor jauh lebih tinggi (2.0x)
                current_score = self.calculate_score(self.current_target, is_work_related=True)
                if best_score < current_score * 2.0:
                    return self.current_target

        # Beralih ke target baru
        if best_target and (self.current_target is None or best_target.target_id != self.current_target.target_id):
            self.current_target = best_target
            self.target_acquired_time = current_time

            # Hitung target sudut kepala anatomis dari koordinat target [-1.0, 1.0]
            new_target_yaw = best_target.x * self.max_yaw_deg
            new_target_pitch = best_target.y * self.max_pitch_deg

            # Cek apakah selisih melewati dead zone 5 derajat
            delta_yaw = abs(new_target_yaw - self.current_yaw_deg)
            if delta_yaw > self.dead_zone_deg:
                self.target_yaw_deg = max(-self.max_yaw_deg, min(self.max_yaw_deg, new_target_yaw))
                self.target_pitch_deg = max(-self.max_pitch_deg, min(self.max_pitch_deg, new_target_pitch))

                # Pemicu kedutan telinga 150 ms sebelum kepala berputar
                if self.on_ear_flick_needed:
                    self.on_ear_flick_needed()

        return self.current_target

    def update_kinematics(self, dt: float) -> tuple[float, float, float, float]:
        """Memperbarui posisi kepala dan mata dengan batasan kecepatan 240 deg/s.

        Returns:
            (head_yaw_deg, head_pitch_deg, eye_look_x, eye_look_y)
        """
        dt = max(0.001, min(0.05, dt))
        max_step = self.max_speed_deg_per_s * dt

        # Perbarui Yaw
        diff_yaw = self.target_yaw_deg - self.current_yaw_deg
        if abs(diff_yaw) <= max_step:
            self.current_yaw_deg = self.target_yaw_deg
        else:
            self.current_yaw_deg += math.copysign(max_step, diff_yaw)

        # Perbarui Pitch
        diff_pitch = self.target_pitch_deg - self.current_pitch_deg
        if abs(diff_pitch) <= max_step:
            self.current_pitch_deg = self.target_pitch_deg
        else:
            self.current_pitch_deg += math.copysign(max_step, diff_pitch)

        # Bola mata bergerak lebih dulu dan sedikit melampaui kepala (micro-saccade offset)
        if self.current_target:
            self.eye_look_x = max(-1.0, min(1.0, self.current_target.x))
            self.eye_look_y = max(-1.0, min(1.0, self.current_target.y))
        else:
            self.eye_look_x = 0.0
            self.eye_look_y = 0.0

        return (
            round(self.current_yaw_deg, 2),
            round(self.current_pitch_deg, 2),
            round(self.eye_look_x, 3),
            round(self.eye_look_y, 3),
        )
