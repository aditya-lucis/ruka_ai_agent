# -*- coding: utf-8 -*-
"""60 FPS Multi-Channel Arbitrator (FR-AV-01).

Menegakkan disiplin satu penulis tunggal per kanal (Single-Writer Per Channel):
- Kanal 1 (Bones): Ditulis hanya oleh Living Presence Engine
- Kanal 2 (Expressions / Blendshapes): Ditulis hanya oleh Mood FSM & Micro-expressions
- Kanal 3 (Visemes): Ditulis hanya oleh Eternal Voice (dengan retensi 120 ms tanpa event)
- Kanal 4 (Pupils): Ditulis hanya oleh Crimson Eyes & Arousal Lag
"""
from __future__ import annotations

import threading
import time
from typing import Dict, Optional

from src.avatar.models import (
    ALL_SUPPORTED_BLENDSHAPES,
    AvatarFrame,
    BonePose,
    PupilPose,
    VisemePose,
)


class ChannelArbitrator:
    VISEME_PERSISTENCE_S = 0.120  # 120 ms retensi tanpa event (FR-AV-01)

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._current_bones: BonePose = BonePose()
        self._current_blendshapes: Dict[str, float] = {k: 0.0 for k in ALL_SUPPORTED_BLENDSHAPES}
        self._current_viseme: VisemePose = VisemePose()
        self._current_pupil: PupilPose = PupilPose()
        self._frame_index: int = 0

    def write_bones(self, bones: BonePose, writer_id: str = "presence") -> bool:
        """Kanal Bones: Hanya boleh ditulis oleh 'presence'."""
        if writer_id != "presence":
            return False
        with self._lock:
            self._current_bones = bones
        return True

    def write_expression(self, blendshapes: Dict[str, float], writer_id: str = "mood") -> bool:
        """Kanal Expressions: Hanya boleh ditulis oleh 'mood'."""
        if writer_id not in ("mood", "expression"):
            return False
        with self._lock:
            for k, v in blendshapes.items():
                if k in ALL_SUPPORTED_BLENDSHAPES:
                    self._current_blendshapes[k] = max(0.0, min(1.0, float(v)))
        return True

    def write_viseme(self, viseme_id: str, weight: float, writer_id: str = "voice") -> bool:
        """Kanal Visemes: Hanya boleh ditulis oleh 'voice'."""
        if writer_id != "voice":
            return False
        with self._lock:
            self._current_viseme = VisemePose(
                viseme_id=viseme_id,
                weight=max(0.0, min(1.0, weight)),
                timestamp=time.time(),
            )
        return True

    def write_pupil(self, pupil: PupilPose, writer_id: str = "eyes") -> bool:
        """Kanal Pupils: Hanya boleh ditulis oleh 'eyes'."""
        if writer_id != "eyes":
            return False
        with self._lock:
            self._current_pupil = pupil
        return True

    def render_frame(self, lod_level: int = 0) -> AvatarFrame:
        """Menghasilkan satu AvatarFrame 60 fps terpadu dengan aturan retensi viseme 120 ms."""
        now = time.time()
        with self._lock:
            self._frame_index += 1

            # Retensi viseme 120 ms: jika sudah lewat 120 ms tanpa event baru, redam ke sil
            viseme = self._current_viseme
            if (now - viseme.timestamp) > self.VISEME_PERSISTENCE_S and viseme.viseme_id != "sil":
                viseme = VisemePose(viseme_id="sil", weight=0.0, timestamp=now)
                self._current_viseme = viseme

            frame = AvatarFrame(
                frame_index=self._frame_index,
                timestamp=now,
                bones=self._current_bones,
                blendshapes=dict(self._current_blendshapes),
                viseme=viseme,
                pupil=self._current_pupil,
                lod_level=lod_level,
            )
            return frame
