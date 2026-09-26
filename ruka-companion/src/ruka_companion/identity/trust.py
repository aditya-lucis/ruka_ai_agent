"""RUKA VI: Trust Engine — Bounded advisory trust and friction mapping.
Strictly follows RUKA-VI Chapter IX.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

from .types import AuthenticationStrength, RecognitionState, TrustEstimate


@dataclass
class AnomalyLedger:
    """Pencatat anomali — penalti pada skor trust."""

    _count: int = 0
    _last_anomaly_ms: int | None = None

    def record(self, now_ms: int) -> None:
        self._count += 1
        self._last_anomaly_ms = now_ms

    @property
    def count(self) -> int:
        return self._count

    @property
    def last_anomaly_ms(self) -> int | None:
        return self._last_anomaly_ms


class TrustModel:
    """Model trust linear + sigmoid — parameter TERBUKA untuk audit."""

    WEIGHTS: dict[str, float] = {
        "identity": 0.34,
        "auth_strength": 0.22,
        "device": 0.16,
        "history": 0.16,
        "anomaly": 0.12,
    }
    BIAS: float = 1.0
    AUTH_SCORE: dict[AuthenticationStrength, float] = {
        AuthenticationStrength.NONE: 0.0,
        AuthenticationStrength.WEAK: 0.3,
        AuthenticationStrength.STRONG: 0.8,
        AuthenticationStrength.MFA_CONFIRMED: 1.0,
    }

    def __init__(self, ledger: AnomalyLedger | None = None) -> None:
        self.ledger = ledger or AnomalyLedger()

    def estimate(
        self,
        recognition_state: RecognitionState,
        posterior: float,
        auth: AuthenticationStrength,
        device_verified: bool = False,
        healthy_ratio: float = 0.5,
    ) -> TrustEstimate:
        """Hitung trust — PURE FUNCTION atas argumen; ledger hanya anomali."""
        if not 0.0 <= posterior <= 1.0:
            raise ValueError("posterior dalam [0,1]")
        if not 0.0 <= healthy_ratio <= 1.0:
            raise ValueError("healthy_ratio dalam [0,1]")
        identity_f = (
            posterior
            if recognition_state == RecognitionState.KNOWN
            else (
                posterior * 0.5
                if recognition_state == RecognitionState.LOW_CONFIDENCE
                else 0.0
            )
        )
        factors = {
            "identity": identity_f,
            "auth_strength": self.AUTH_SCORE[auth],
            "device": 1.0 if device_verified else 0.0,
            "history": healthy_ratio,
            "anomaly": 1.0 / (1.0 + self.ledger.count),
        }
        z = sum(self.WEIGHTS[k] * v for k, v in factors.items()) - self.BIAS
        trust = 1.0 / (1.0 + math.exp(-z))
        return TrustEstimate(
            trust=round(trust, 4),
            factors={k: round(v, 4) for k, v in factors.items()},
            note=(
                "advisory only — trust TIDAK membuka izin; hanya menyetel "
                "frekuensi konfirmasi manusia"
            ),
        )

    @staticmethod
    def friction_from_trust(trust: float) -> dict[str, Any]:
        """Pemetaan trust → tingkat friksi (KEBIJAKAN, bukan izin)."""
        if not 0.0 <= trust <= 1.0:
            raise ValueError("trust dalam [0,1]")

        if trust >= 0.75:
            tier = "low_friction"
        elif trust >= 0.40:
            tier = "medium_friction"
        else:
            tier = "high_friction"
        return {
            "trust": trust,
            "friction_tier": tier,
            "never_grants_permission": True,
        }
