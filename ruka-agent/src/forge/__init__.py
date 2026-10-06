# -*- coding: utf-8 -*-
"""PROJECT NOCTIS — Crimson Astral Forge & Design Lab Package.

Implements SRS Section 3.1.12 (FR-FG-01 s.d. FR-FG-11).
Polite Guest principle:
- forge.enabled defaults to False
- When disabled: 0 bus subscriptions, 0 memory allocated, import overhead < 5ms.
"""

from __future__ import annotations

import time

t_import_start = time.perf_counter()

from src.forge.config import ForgeConfig, PerformanceMode
from src.forge.manifest import HonestyManifest, ManifestRegistry, TruthType
from src.forge.solvers.physics import (
    ParticleSolverLite,
    SATCollisionSolver,
    SymplecticOrbitSolver,
    XPBDClothSolver,
)
from src.forge.solvers.quantum import (
    BlochSphereSimulator,
    DoubleSlitSimulator,
    QuantumTunnelingSolver,
)
from src.forge.design_lab import DesignBlueprint, DesignLab

t_import_elapsed = (time.perf_counter() - t_import_start) * 1000.0

__all__ = [
    "ForgeConfig",
    "PerformanceMode",
    "HonestyManifest",
    "ManifestRegistry",
    "TruthType",
    "SymplecticOrbitSolver",
    "SATCollisionSolver",
    "XPBDClothSolver",
    "ParticleSolverLite",
    "DoubleSlitSimulator",
    "QuantumTunnelingSolver",
    "BlochSphereSimulator",
    "DesignLab",
    "DesignBlueprint",
    "t_import_elapsed",
]
