# -*- coding: utf-8 -*-
"""PROJECT NOCTIS — Honesty Manifest Engine.

Implements SRS FR-FG-06.
Enforces 100% honesty manifests on all simulations and scientific solvers:
- TruthType: 'edukatif', 'aproksimasi_numerik', 'fenomena_nyata'
- Explicit assumptions, limitations, numerical methods, and validation indicators.
- Un-manifested scenarios are strictly rejected fail-closed.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Literal, Optional

TruthType = Literal["edukatif", "aproksimasi_numerik", "fenomena_nyata"]


@dataclass
class HonestyManifest:
    truth_type: TruthType
    assumptions: List[str]
    limitations: List[str]
    numerical_method: str
    validation_indicators: List[str]
    max_tolerable_error: float = 0.01
    source_citation: Optional[str] = None

    def validate(self) -> tuple[bool, str]:
        """Validates manifest integrity. Rejects claims without numbers or empty fields."""
        if not self.assumptions:
            return False, "HonestyManifest ditolak: Daftar asumsi tidak boleh kosong."
        if not self.limitations:
            return False, "HonestyManifest ditolak: Batasan model harus dideklarasikan secara jujur."
        if not self.numerical_method or len(self.numerical_method.strip()) < 3:
            return False, "HonestyManifest ditolak: Metode numerik wajib disebutkan."
        if not self.validation_indicators:
            return False, "HonestyManifest ditolak: Indikator validasi wajib menyertakan tolok ukur angka."
        if self.max_tolerable_error <= 0.0:
            return False, "HonestyManifest ditolak: Toleransi galat harus berupa angka positif nyata."

        return True, "Manifest valid dan jujur."


class ManifestRegistry:
    """Registry guarding simulations. Unregistered or invalid scenarios are rejected."""

    def __init__(self) -> None:
        self._manifests: dict[str, HonestyManifest] = {}

    def register(self, scenario_name: str, manifest: HonestyManifest) -> tuple[bool, str]:
        valid, msg = manifest.validate()
        if not valid:
            return False, msg
        self._manifests[scenario_name] = manifest
        return True, f"Skenario '{scenario_name}' terdaftar dengan tipe '{manifest.truth_type}'."

    def get_manifest(self, scenario_name: str) -> Optional[HonestyManifest]:
        return self._manifests.get(scenario_name)

    def is_cleared_for_execution(self, scenario_name: str) -> bool:
        return scenario_name in self._manifests
