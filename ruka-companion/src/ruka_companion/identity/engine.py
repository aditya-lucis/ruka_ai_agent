"""RUKA VI: Identity Engine — Multimodal recognition, authentication, and decision action.
Strictly follows RUKA-VI Chapter IX & X.
"""

from __future__ import annotations

import time
from typing import Any, Sequence

from ..math.decision import (
    LOSS_DESTRUCTIVE,
    LOSS_ROUTINE,
    Action,
    ExpectedLossEngine,
    decide as decide_loss,
)
from ..math.fusion import EvidenceFuser, ModalityEvidence
from .types import (
    AuthenticationStrength,
    IdentityEvidence,
    IdentityProfile,
    IdentityThresholds,
    Modality,
    RecognitionResult,
    RecognitionState,
)


class IdentityEngine:
    """Mesin pengenalan dan autentikasi identitas multimodal."""

    def __init__(
        self,
        thresholds: IdentityThresholds | None = None,
        fuser: EvidenceFuser | None = None,
    ) -> None:
        self.thresholds = thresholds or IdentityThresholds()
        self.fuser = fuser or EvidenceFuser()
        self.profiles: dict[str, IdentityProfile] = {}
        self._decision_engine = ExpectedLossEngine()

    def enroll(self, profile: IdentityProfile) -> None:
        if profile.profile_id in self.profiles:
            raise ValueError(f"Profil sudah terdaftar: {profile.profile_id}")
        self.profiles[profile.profile_id] = profile

    def recognize(
        self,
        evidence: IdentityEvidence,
        expected_modalities: Sequence[str] = ("voice", "face", "device"),
    ) -> RecognitionResult:
        """Bukti → posterior per kandidat → RecognitionResult terbaik.
        Kandidat = profil terdaftar. Prior seragam atas kandidat (bukan
        memihak Bos) — prior_bos hanya untuk lapisan autentikasi.
        """
        n = len(self.profiles)
        if n == 0:
            return RecognitionResult(
                state=RecognitionState.UNKNOWN,
                posterior_prob=0.0,
                note="tidak ada profil terdaftar — enrollment dahulu",
            )
        usable = [s for s in evidence.signals if s.available]
        if not usable:
            return RecognitionResult(
                state=RecognitionState.UNAVAILABLE,
                posterior_prob=0.0,
                missing=sorted({m.value for m in Modality}),
                evidence=evidence,
                note="semua modality unavailable — pengenalan TIDAK ditebak",
            )
        # posterior tiap profil terhadap "bukan siapa-siapa" (impostor)
        best: RecognitionResult | None = None
        for pid in sorted(self.profiles):
            evs = [
                ModalityEvidence(
                    modality=s.modality.value, llr=s.llr, weight=s.weight
                )
                for s in usable
            ]

            res = self.fuser.fuse(
                prior_prob=1.0 / (n + 1),
                evidences=evs,
                expected_modalities=list(expected_modalities),
            )
            cand = RecognitionResult(
                state=RecognitionState.UNKNOWN,  # sementara — diklasifikasi di bawah
                profile_id=pid,
                posterior_prob=res.posterior_prob,
                conflict=res.conflict,
                contributing=list(res.contributing),
                missing=list(res.missing_expected),
                evidence=evidence,
                note=f"fusi {len(usable)} modality atas kandidat {pid}",
            )
            if best is None or cand.posterior_prob > best.posterior_prob:
                best = cand
        assert best is not None
        # klasifikasi status
        if best.conflict >= self.thresholds.conflict:
            best.state = RecognitionState.SUSPICIOUS
            best.note += " | konflik bukti tinggi — angkat ke manusia"
        elif best.posterior_prob >= self.thresholds.known:
            best.state = RecognitionState.KNOWN
        elif best.posterior_prob < self.thresholds.reject:
            best.state = RecognitionState.UNKNOWN
        else:
            best.state = RecognitionState.LOW_CONFIDENCE
            best.note += " | zona abu-abu: jangan ambil tindakan ber-privilege"
        return best

    def authenticate(
        self, result: RecognitionResult, mfa_confirmed: bool = False
    ) -> AuthenticationStrength:
        """Kekuatan pembuktian klaim — ATURAN EKSPLISIT, bukan perasaan."""
        if mfa_confirmed:
            return AuthenticationStrength.MFA_CONFIRMED
        if result.state in (RecognitionState.UNAVAILABLE, RecognitionState.UNKNOWN):
            return AuthenticationStrength.NONE
        if result.evidence is None:
            return AuthenticationStrength.NONE
        avail = {s.modality.value for s in result.evidence.signals if s.available}
        independent = {"voice", "face", "device", "credential"}
        n_indep = len(avail & independent)
        if result.state == RecognitionState.KNOWN and n_indep >= 2:
            return AuthenticationStrength.STRONG
        return AuthenticationStrength.WEAK

    def decide_action(
        self,
        result: RecognitionResult,
        auth: AuthenticationStrength,
        risk_cost: float = 10.0,
    ) -> Action:
        """RECOGNITION + AUTH + RISK → tindakan decision theory."""
        p = result.posterior_prob
        if auth == AuthenticationStrength.NONE:
            p = 0.0
        elif auth == AuthenticationStrength.WEAK:
            p *= 0.5
        elif auth == AuthenticationStrength.STRONG:
            p *= 0.9
        else:  # MFA_CONFIRMED
            p = max(p, 0.95)
        if result.state == RecognitionState.SUSPICIOUS:
            p = min(p, 0.3)
        p = max(0.0, min(p, 0.99))
        floor = min(0.5, 0.01 * max(1.0, risk_cost / 10.0))
        posterior = self._decision_engine.posterior_from_confidence(p, floor)
        loss = LOSS_DESTRUCTIVE if risk_cost >= 50.0 else LOSS_ROUTINE
        decision = decide_loss(posterior, loss)
        return decision.action
