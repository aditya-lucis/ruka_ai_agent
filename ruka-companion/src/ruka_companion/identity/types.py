"""RUKA VI: Identity subsystem types and contracts.
Four-layer separation: RECOGNITION != AUTHENTICATION != AUTHORIZATION != TRUST.
Strictly follows RUKA-VI Chapter IX.
"""

from __future__ import annotations

import time
import uuid
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, field_validator


class RecognitionState(str, Enum):
    """Status pengenalan — probabilistik murni, bukan otorisasi."""

    KNOWN = "KNOWN"  # posterior tinggi, bukti cukup
    LOW_CONFIDENCE = "LOW_CONFIDENCE"  # bukti ambigu → jangan ambil tindakan ber-privilege
    UNKNOWN = "UNKNOWN"  # tidak cocok dengan profil mana pun
    UNAVAILABLE = "UNAVAILABLE"  # modality tidak bisa menilai (sensor off)
    SUSPICIOUS = "SUSPICIOUS"  # konflik bukti / pola spoof


class Modality(str, Enum):
    VOICE = "voice"
    FACE = "face"
    DEVICE = "device"
    SESSION = "session"
    HISTORY = "history"
    CREDENTIAL = "credential"


class ModalitySignal(BaseModel):
    """Sinyal mentah satu modality, SEBELUM fusi.
    Skor asalnya bebas (cosine, LLR, dsb.) — satukan jadi LLR di identity.engine.
    """

    modality: Modality
    raw_score: float | None = None
    llr: float = 0.0
    weight: float = Field(default=1.0, ge=0.0, le=1.0)
    available: bool = True
    detail: dict[str, Any] = Field(default_factory=dict)

    @field_validator("llr")
    @classmethod
    def _finite(cls, v: float) -> float:
        if v != v or v in (float("inf"), float("-inf")):
            raise ValueError("llr harus finite")
        return v


class IdentityEvidence(BaseModel):
    """Agregat bukti satu kejadian identifikasi."""

    signals: list[ModalitySignal] = Field(default_factory=list)
    context: dict[str, Any] = Field(default_factory=dict)
    captured_at_ms: int = Field(default_factory=lambda: int(time.time() * 1000))


class RecognitionResult(BaseModel):
    """HASIL RECOGNITION — probabilistik murni, belum otorisasi."""

    state: RecognitionState
    posterior_prob: float = Field(ge=0.0, le=1.0)
    profile_id: str | None = None
    conflict: float = Field(default=0.0, ge=0.0, le=1.0)
    contributing: list[str] = Field(default_factory=list)
    missing: list[str] = Field(default_factory=list)
    evidence: IdentityEvidence | None = None
    note: str = ""


class AuthenticationStrength(str, Enum):
    """Kekuatan pembuktian — TERPISAH dari posterior recognition."""

    NONE = "NONE"  # tak ada pembuktian (mis. teks Telegram polos)
    WEAK = "WEAK"  # 1 modality, atau provider terbatas
    STRONG = "STRONG"  # ≥2 modality independen skor tinggi / kunci device
    MFA_CONFIRMED = "MFA_CONFIRMED"  # konfirmasi manusia eksplisit atas prompt


class AuthorizationDecision(BaseModel):
    """HASIL OTORISASI — kebijakan, bukan probabilitas."""

    allowed: bool = False
    required_human_confirm: bool = False
    capabilities: list[str] = Field(default_factory=list)
    reason: str = ""
    decided_by: str = "policy:v1"
    correlation_id: str = Field(default_factory=lambda: uuid.uuid4().hex[:16])


class TrustEstimate(BaseModel):
    """Estimasi kepercayaan — BOUNDED, TIDAK PERNAH meng-override otorisasi."""

    trust: float = Field(ge=0.0, le=1.0)
    factors: dict[str, float] = Field(default_factory=dict)
    computed_at_ms: int = Field(default_factory=lambda: int(time.time() * 1000))
    note: str = ""


class IdentityProfile(BaseModel):
    """Profil identitas satu orang (Bos atau orang yang diperkenalkan)."""

    profile_id: str
    display_name: str
    role: str = "user"  # 'owner' | 'guest' | 'service'
    relationship: str = "UNKNOWN"
    enrolled_at_ms: int = Field(default_factory=lambda: int(time.time() * 1000))
    metadata: dict[str, Any] = Field(default_factory=dict)


class IdentityThresholds(BaseModel):
    """Ambang keputusan pengenalan identitas."""

    known: float = 0.85
    reject: float = 0.20
    conflict: float = 0.40

    @field_validator("known")
    @classmethod
    def _validate_known(cls, v: float) -> float:
        if not (0.0 < v < 1.0):
            raise ValueError("known harus di rentang (0, 1)")
        return v

    def model_post_init(self, __context: Any) -> None:
        if self.reject >= self.known:
            raise ValueError(
                f"syarat validasi gagal: reject ({self.reject}) harus lebih kecil dari known ({self.known})"
            )
