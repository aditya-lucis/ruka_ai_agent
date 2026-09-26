"""RUKA VI: The Presence Engine — Read-Only Projection of Runtime & Capability Probes.
Strictly follows RUKA-VI Chapter XV (baris 64-215).
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable

from ruka_companion.voice.asr import asr_capability
from ruka_companion.voice.speaker import AcousticGaussianProvider


class OperatingMode(str, Enum):
    """Tiga mode operasi nyata Ruka (Part XV)."""

    LOCAL_ONLY = "LOCAL_ONLY"
    HYBRID = "HYBRID"
    REMOTE = "REMOTE"


@dataclass
class CapabilityStatus:
    name: str
    available: bool
    reason: str
    layer: str


Probe = Callable[[], CapabilityStatus]


class PresenceEngine:
    """PresenceEngine: membaca kenyataan lewat probe, tanpa menjadi mesin status sendiri."""

    def __init__(
        self,
        runtime_state: str = "READY",
        cloud_link: str = "DISCONNECTED",
        probes: dict[str, Probe] | None = None,
    ) -> None:
        self.runtime_state = runtime_state
        self.cloud_link = cloud_link
        self.probes = probes or {}

    def capability_matrix(self) -> list[CapabilityStatus]:
        results: list[CapabilityStatus] = []
        for name, probe in self.probes.items():
            results.append(probe())
        return results

    # ------------------------------------------------------------- mode
    def effective_mode(self) -> OperatingMode:
        """Mode menurut keadaan NYATA (bukan konfigurasi):
        laptop mati/offline → REMOTE; link cloud hidup → HYBRID; else LOCAL_ONLY."""
        if self.runtime_state in ("OFFLINE", "SHUTDOWN", "CRASHED"):
            return OperatingMode.REMOTE if self.cloud_link == "CONNECTED" else OperatingMode.LOCAL_ONLY
        if self.cloud_link == "CONNECTED":
            return OperatingMode.HYBRID

        return OperatingMode.LOCAL_ONLY

    def report(self) -> dict[str, Any]:
        caps = self.capability_matrix()
        return {
            "runtime_state": self.runtime_state,
            "cloud_link": self.cloud_link,
            "mode": self.effective_mode().value,
            "capabilities": [
                {
                    "name": c.name,
                    "available": c.available,
                    "reason": c.reason,
                    "layer": c.layer,
                }
                for c in caps
            ],
            "n_available": sum(1 for c in caps if c.available),
            "privacy": {"mic": "OFF", "camera": "OFF"},  # default; sensor FSM di modul masing-masing
        }

    # ------------------------------------------------------- honest answers
    def answer_availability(self, capability: str) -> str:
        """Kalimat jujur untuk kanal chat — TIDAK pernah pura-pura bisa."""
        for c in self.capability_matrix():
            if c.name == capability:
                if c.available:
                    return f"{capability} tersedia."
                return f"{capability} TIDAK tersedia saat ini ({c.reason})."
        return f"{capability} tidak dikenal sistem."


def default_probes(
    matcher_face: Any | None = None,
    speaker_provider: AcousticGaussianProvider | None = None,
    cloud_link_state: Callable[[], str] | None = None,
) -> dict[str, Probe]:
    """Probe default Volume VI — dipakai book & integration tests."""
    probes: dict[str, Probe] = {}

    def _asr() -> CapabilityStatus:
        cap = asr_capability()
        return CapabilityStatus(
            "voice.asr", bool(cap.get("available")), cap.get("reason", ""), "local"
        )

    def _speaker() -> CapabilityStatus:
        p = speaker_provider or AcousticGaussianProvider()
        cap = p.capability()
        return CapabilityStatus(
            "voice.speaker", bool(cap.get("available")), cap.get("reason", ""), "local"
        )

    def _face() -> CapabilityStatus:
        if matcher_face is None:
            return CapabilityStatus(
                "vision.face", False, "matcher tidak diinisialisasi", "local"
            )
        cap = matcher_face.capability()
        return CapabilityStatus(
            "vision.face", bool(cap.get("available")), cap.get("reason", ""), "local"
        )

    def _cloud() -> CapabilityStatus:
        state = cloud_link_state() if cloud_link_state else "DISCONNECTED"
        return CapabilityStatus(
            "cloud.link", state == "CONNECTED", f"link {state}", "remote-bridge"
        )

    def _terminal() -> CapabilityStatus:
        # Alat lokal Vol V hadir by design; tapi hanya berguna saat runtime lokal hidup
        return CapabilityStatus("tools.terminal", True, "runtime lokal", "local")

    probes["voice.asr"] = _asr
    probes["voice.speaker"] = _speaker
    probes["vision.face"] = _face
    probes["cloud.link"] = _cloud
    probes["tools.terminal"] = _terminal
    return probes
