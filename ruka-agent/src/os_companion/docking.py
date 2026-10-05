# -*- coding: utf-8 -*-
"""Floating Mini Avatar & 8-Compass Magnetic Docking (FR-OS-02).

Mengatur penempatan avatar mengapung 200px dan dok magnetik 8 mata angin:
- Avatar mini 200 piksel pada 30 fps
- Pembeda klik vs seret (drag) dengan ambang 4 piksel
- Magnetik dok menempel pada 8 mata angin dengan jarak snap 48 piksel
- Terkunci ganda di dalam batas monitor dan workspace
"""
from __future__ import annotations

import math
from typing import Optional, Tuple
from src.os_companion.models import CompassPoint, DockPosition


class MagneticDockManager:
    AVATAR_SIZE = 200
    SNAP_DISTANCE = 48
    DRAG_THRESHOLD_PX = 4

    def __init__(
        self,
        screen_width: int = 1920,
        screen_height: int = 1080,
        margin: int = 16,
    ) -> None:
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.margin = margin

        # Posisi awal: Tenggara (SE) di atas taskbar
        self.current_dock: DockPosition = self.calculate_compass_dock(CompassPoint.SE)
        self.drag_start_pos: Optional[Tuple[int, int]] = None
        self.is_dragging: bool = False

    def calculate_compass_dock(self, compass: CompassPoint) -> DockPosition:
        """Menghitung koordinat piksel ideal untuk 8 titik mata angin."""
        w, h = self.AVATAR_SIZE, self.AVATAR_SIZE
        left = self.margin
        center_x = (self.screen_width - w) // 2
        right = self.screen_width - w - self.margin

        top = self.margin
        center_y = (self.screen_height - h) // 2
        bottom = self.screen_height - h - self.margin

        coords = {
            CompassPoint.NW: (left, top),
            CompassPoint.N: (center_x, top),
            CompassPoint.NE: (right, top),
            CompassPoint.W: (left, center_y),
            CompassPoint.E: (right, center_y),
            CompassPoint.SW: (left, bottom),
            CompassPoint.S: (center_x, bottom),
            CompassPoint.SE: (right, bottom),
        }
        x, y = coords[compass]
        return DockPosition(compass=compass, x=x, y=y, is_snapped=True)

    def on_pointer_down(self, x: int, y: int) -> None:
        self.drag_start_pos = (x, y)
        self.is_dragging = False

    def on_pointer_move(self, x: int, y: int) -> bool:
        """Memeriksa apakah pergerakan melebihi ambang 4px untuk dinyatakan sebagai seret (drag)."""
        if self.drag_start_pos is None:
            return False
        dx = x - self.drag_start_pos[0]
        dy = y - self.drag_start_pos[1]
        if math.hypot(dx, dy) >= self.DRAG_THRESHOLD_PX:
            self.is_dragging = True
        return self.is_dragging

    def on_pointer_up(self, release_x: int, release_y: int) -> tuple[DockPosition, bool]:
        """Menyelesaikan interaksi saat mouse dilepas.

        Returns:
            tuple (posisi_dok_final, was_click)
        """
        was_click = not self.is_dragging
        self.drag_start_pos = None
        self.is_dragging = False

        if was_click:
            return self.current_dock, True

        # Evaluasi snap magnetik 48px ke 8 mata angin terdekat
        best_dock = self._find_nearest_magnetic_dock(release_x, release_y)
        self.current_dock = best_dock
        return best_dock, False

    def _find_nearest_magnetic_dock(self, x: int, y: int) -> DockPosition:
        """Mencari titik kompas dalam jarak snap 48px, atau mengunci di dalam batas monitor."""
        # Kunci di dalam batas monitor
        clamped_x = max(self.margin, min(self.screen_width - self.AVATAR_SIZE - self.margin, x))
        clamped_y = max(self.margin, min(self.screen_height - self.AVATAR_SIZE - self.margin, y))

        for cp in CompassPoint:
            ideal = self.calculate_compass_dock(cp)
            dist = math.hypot(clamped_x - ideal.x, clamped_y - ideal.y)
            if dist <= self.SNAP_DISTANCE:
                return ideal

        # Jika tidak ada titik dalam 48px, pasang pada titik terdekat tapi tandai not snapped
        nearest_cp = min(
            CompassPoint,
            key=lambda cp: math.hypot(clamped_x - self.calculate_compass_dock(cp).x, clamped_y - self.calculate_compass_dock(cp).y),
        )
        return DockPosition(compass=nearest_cp, x=clamped_x, y=clamped_y, is_snapped=False)
