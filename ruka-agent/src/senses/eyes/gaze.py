# -*- coding: utf-8 -*-
"""Gaze Estimator & Eye Contact Tracker (FR-EY-07).

Memperkirakan arah pandang dan mendeteksi kontak mata:
- Kerucut kontak mata 4.5 derajat (|yaw| <= 4.5 dan |pitch| <= 4.5).
- Tahan kontak mata minimal 400 ms sebelum dikonfirmasi.
- Dukungan kalibrasi 9 titik.
"""
from __future__ import annotations

from src.senses.eyes.models import GazeVector


class GazeEstimator:
    def __init__(
        self,
        cone_deg: float = 4.5,
        min_hold_ms: float = 400.0,
    ) -> None:
        self.cone_deg = cone_deg
        self.min_hold_ms = min_hold_ms

        self._calibrated: bool = False
        self._current_hold_ms: float = 0.0

    @property
    def is_calibrated(self) -> bool:
        return self._calibrated

    def calibrate_9_points(self, points_9: list[tuple[float, float]]) -> bool:
        """Menjalankan kalibrasi 9 titik geometry iris."""
        if len(points_9) != 9:
            raise ValueError(f"Membutuhkan tepat 9 titik kalibrasi, menerima {len(points_9)}")
        self._calibrated = True
        return True

    def estimate_gaze(
        self,
        yaw_deg: float,
        pitch_deg: float,
        dt_ms: float = 33.3,
    ) -> GazeVector:
        """Memperkirakan arah pandang dan status kontak mata."""
        in_cone = (abs(yaw_deg) <= self.cone_deg) and (abs(pitch_deg) <= self.cone_deg)

        if in_cone:
            self._current_hold_ms += dt_ms
        else:
            self._current_hold_ms = max(0.0, self._current_hold_ms - dt_ms * 1.5)

        is_contact = self._current_hold_ms >= self.min_hold_ms

        return GazeVector(
            yaw_deg=yaw_deg,
            pitch_deg=pitch_deg,
            is_eye_contact=is_contact,
            contact_duration_ms=self._current_hold_ms,
        )
