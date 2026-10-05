# -*- coding: utf-8 -*-
"""Living Avatar Engine Controller & Public API (FR-AV-09, FR-AV-10).

Pengendali terpadu mesin avatar VRM 1.0:
- Arbitrase 4 kanal 60 fps (Bones, Expressions, Visemes, Pupils)
- API Ekspresi Publik: set_expression, set_viseme, get_pose dengan validasi ketat
- LOD 3 Tingkat (hemat 25% waktu frame tanpa merusak pose)
- LRU Morph Cache 96 entri dengan hit-rate tinggi
"""
from __future__ import annotations

import collections
import logging
from typing import Dict, Optional

from src.avatar.arbitrator import ChannelArbitrator
from src.avatar.expressions import ExpressionLayerManager
from src.avatar.eye_animator import AvatarEyeAnimator
from src.avatar.idle_tree import IdleAnimationTree
from src.avatar.lip_sync import LipSyncEngine
from src.avatar.models import (
    ALL_SUPPORTED_BLENDSHAPES,
    AvatarFrame,
    BonePose,
    PupilPose,
    VisemePose,
)
from src.avatar.verlet_physics import VerletPhysicsEngine

log = logging.getLogger("ruka.avatar.engine")


class LivingAvatarEngine:
    MORPH_CACHE_CAPACITY = 96

    def __init__(self) -> None:
        self.arbitrator = ChannelArbitrator()
        self.expression_layer = ExpressionLayerManager()
        self.eye_animator = AvatarEyeAnimator()
        self.idle_tree = IdleAnimationTree()
        self.lip_sync = LipSyncEngine()
        self.verlet_physics = VerletPhysicsEngine()

        self.lod_level: int = 0  # 0=Full, 1=No secondary, 2=Minimal
        self.morph_cache: collections.OrderedDict[str, Dict[str, float]] = collections.OrderedDict()

    def set_lod_level(self, level: int) -> None:
        """Mengatur LOD 3-tingkat (0, 1, 2) untuk menghemat 25% beban frame (FR-AV-09)."""
        self.lod_level = max(0, min(2, level))

    def set_expression(self, name: str, weight: float) -> bool:
        """API Publik: Mengatur bobot ekspresi blendshape dengan validasi nama keras (FR-AV-10)."""
        if name not in ALL_SUPPORTED_BLENDSHAPES:
            log.warning("Blendshape '%s' ditolak: tidak terdaftar dalam kontrak VRM RUKA.", name)
            return False

        clamped_weight = max(0.0, min(1.0, float(weight)))
        return self.arbitrator.write_expression({name: clamped_weight}, writer_id="mood")

    def set_viseme(self, viseme_id: str, weight: float = 1.0) -> bool:
        """API Publik: Mengatur viseme fonemik dengan validasi bobot [0.0, 1.0] (FR-AV-10)."""
        clamped_weight = max(0.0, min(1.0, float(weight)))
        return self.arbitrator.write_viseme(viseme_id, clamped_weight, writer_id="voice")

    def get_pose(self) -> AvatarFrame:
        """API Publik: Mengambil snapshot AvatarFrame terkini pada 60 fps (FR-AV-10)."""
        return self.arbitrator.render_frame(lod_level=self.lod_level)

    def cache_morph_state(self, key: str, weights: Dict[str, float]) -> None:
        """Menyimpan kombinasi bobot morph ke LRU cache 96 entri (FR-AV-09)."""
        if len(self.morph_cache) >= self.MORPH_CACHE_CAPACITY:
            self.morph_cache.popitem(last=False)
        self.morph_cache[key] = dict(weights)

    def get_cached_morph_state(self, key: str) -> Optional[Dict[str, float]]:
        if key in self.morph_cache:
            self.morph_cache.move_to_end(key)
            return self.morph_cache[key]
        return None
