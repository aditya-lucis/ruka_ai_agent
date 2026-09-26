"""RUKA VI: Tests for Identity & Trust Subsystem.
Strictly follows RUKA-VI Chapter IX & XXV testing protocol.
"""

from __future__ import annotations

import pytest

from ruka_companion.math.decision import Action
from ruka_companion.identity.types import (
    AuthenticationStrength,
    IdentityEvidence,
    IdentityProfile,
    IdentityThresholds,
    Modality,
    ModalitySignal,
    RecognitionResult,
    RecognitionState,
)
from ruka_companion.identity.delegation import (
    DelegationRegistry,
    DelegationState,
)
from ruka_companion.identity.trust import AnomalyLedger, TrustModel
from ruka_companion.identity.relationship import (
    Relationship,
    RelationshipEngine,
    RelationshipType,
)
from ruka_companion.identity.engine import IdentityEngine

PROFILE_BOS = IdentityProfile(profile_id="bos", display_name="Bos", role="owner")
PROFILE_ALICE = IdentityProfile(profile_id="alice", display_name="Alice", role="guest")


def _evidence(*signals: ModalitySignal) -> IdentityEvidence:
    return IdentityEvidence(signals=list(signals))


class TestRecognition:
    def test_contradictory_evidence_suspicious(self):
        eng = IdentityEngine()
        eng.enroll(PROFILE_BOS)
        r = eng.recognize(
            _evidence(
                ModalitySignal(modality=Modality.VOICE, llr=5.0),
                ModalitySignal(modality=Modality.FACE, llr=-5.0),
            )
        )
        assert r.state == RecognitionState.SUSPICIOUS
        assert r.conflict > 0.4

    def test_best_profile_chosen(self):
        eng = IdentityEngine()
        eng.enroll(PROFILE_BOS)
        eng.enroll(PROFILE_ALICE)
        ev = _evidence(ModalitySignal(modality=Modality.VOICE, llr=0.1))
        r = eng.recognize(ev)
        # dua kandidat dengan bukti lemah → posterior rendah, tak ada pemenang jelas
        assert r.state in (
            RecognitionState.LOW_CONFIDENCE,
            RecognitionState.UNKNOWN,
        )

    def test_duplicate_enroll_rejected(self):
        eng = IdentityEngine()
        eng.enroll(PROFILE_BOS)
        with pytest.raises(ValueError, match="sudah terdaftar"):
            eng.enroll(PROFILE_BOS)

    def test_threshold_validation(self):
        with pytest.raises(ValueError, match="reject"):
            IdentityThresholds(known=0.5, reject=0.9)  # reject > known

    def test_empty_profiles_and_unavailable(self):
        eng = IdentityEngine()
        r = eng.recognize(_evidence())
        assert r.state == RecognitionState.UNKNOWN

        eng.enroll(PROFILE_BOS)
        r_unavail = eng.recognize(
            _evidence(ModalitySignal(modality=Modality.VOICE, available=False))
        )
        assert r_unavail.state == RecognitionState.UNAVAILABLE


class TestAuthentication:
    def test_mfa_confirmed(self):
        eng = IdentityEngine()
        r = eng.recognize(_evidence())
        s = eng.authenticate(r, mfa_confirmed=True)
        assert s == AuthenticationStrength.MFA_CONFIRMED

    def test_strong_two_independent_modalities(self):
        eng = IdentityEngine()
        eng.enroll(PROFILE_BOS)
        ev = _evidence(
            ModalitySignal(modality=Modality.VOICE, llr=4.0),
            ModalitySignal(modality=Modality.FACE, llr=4.0),
        )
        r = eng.recognize(ev)
        assert eng.authenticate(r) == AuthenticationStrength.STRONG

    def test_weak_single_modality(self):
        eng = IdentityEngine()
        eng.enroll(PROFILE_BOS)
        ev = _evidence(ModalitySignal(modality=Modality.VOICE, llr=4.0))
        r = eng.recognize(ev)
        assert eng.authenticate(r) == AuthenticationStrength.WEAK

    def test_none_strength(self):
        eng = IdentityEngine()
        eng.enroll(PROFILE_BOS)
        ev = _evidence(ModalitySignal(modality=Modality.VOICE, available=False))
        r = eng.recognize(ev)
        assert eng.authenticate(r) == AuthenticationStrength.NONE


class TestDecisionAction:
    def test_routine_action_decision(self):
        eng = IdentityEngine()
        eng.enroll(PROFILE_BOS)
        ev = _evidence(
            ModalitySignal(modality=Modality.VOICE, llr=4.0),
            ModalitySignal(modality=Modality.FACE, llr=4.0),
        )
        r = eng.recognize(ev)
        auth = eng.authenticate(r)
        # Routine action (risk_cost < 50) with strong authentication
        action = eng.decide_action(r, auth, risk_cost=10.0)
        assert action == Action.EXECUTE

    def test_destructive_action_decision(self):
        eng = IdentityEngine()
        eng.enroll(PROFILE_BOS)
        ev = _evidence(ModalitySignal(modality=Modality.VOICE, llr=4.0))
        r = eng.recognize(ev)
        auth = eng.authenticate(r)  # WEAK
        # Destructive action (risk_cost >= 50) with weak auth asks for confirmation
        action = eng.decide_action(r, auth, risk_cost=100.0)
        assert action in (Action.ASK, Action.DENY)


class TestDelegation:
    def test_delegation_lifecycle(self):
        reg = DelegationRegistry()
        grant = reg.propose(
            grantor="bos",
            grantee="alice",
            capabilities={"filesystem.read", "excel.read"},
            scope={"path": "/docs"},
            ttl_ms=3600_000,
        )
        assert grant.state == DelegationState.PENDING_CONFIRM

        # Before confirm: not active
        allowed, _ = reg.check("alice", "filesystem.read")
        assert not allowed

        # Confirm
        reg.confirm(grant.grant_id)
        assert grant.state == DelegationState.ACTIVE
        allowed, reason = reg.check("alice", "filesystem.read")
        assert allowed

        # Revoke
        reg.revoke(grant.grant_id, reason="done")
        allowed, _ = reg.check("alice", "filesystem.read")
        assert not allowed

    def test_non_delegatable_rejected(self):
        reg = DelegationRegistry()
        with pytest.raises(ValueError, match="tak bisa didelegasikan"):
            reg.propose("bos", "alice", {"terminal.execute"})

        with pytest.raises(ValueError, match="tak dikenal"):
            reg.propose("bos", "alice", {"unknown.capability"})

    def test_delegation_check_with_recognition(self):
        reg = DelegationRegistry()
        grant = reg.propose("bos", "alice", {"filesystem.read"})
        reg.confirm(grant.grant_id)

        # UNKNOWN recognition rejected
        ok, _ = reg.check_with_recognition(
            "alice",
            "filesystem.read",
            recognition_state=RecognitionState.UNKNOWN,
            auth=AuthenticationStrength.WEAK,
        )
        assert not ok

        # NONE auth rejected
        ok, _ = reg.check_with_recognition(
            "alice",
            "filesystem.read",
            recognition_state=RecognitionState.KNOWN,
            auth=AuthenticationStrength.NONE,
        )
        assert not ok

        # KNOWN + WEAK/STRONG accepted
        ok, _ = reg.check_with_recognition(
            "alice",
            "filesystem.read",
            recognition_state=RecognitionState.KNOWN,
            auth=AuthenticationStrength.WEAK,
        )
        assert ok


class TestTrust:
    def test_trust_estimation_and_friction(self):
        model = TrustModel()
        est = model.estimate(
            recognition_state=RecognitionState.KNOWN,
            posterior=0.95,
            auth=AuthenticationStrength.STRONG,
            device_verified=True,
            healthy_ratio=0.8,
        )
        assert 0.0 <= est.trust <= 1.0
        friction = TrustModel.friction_from_trust(est.trust)
        assert friction["never_grants_permission"] is True
        assert friction["friction_tier"] in ("low_friction", "medium_friction")

    def test_anomaly_ledger_impact(self):
        ledger = AnomalyLedger()
        model = TrustModel(ledger=ledger)

        est_clean = model.estimate(
            recognition_state=RecognitionState.KNOWN,
            posterior=0.9,
            auth=AuthenticationStrength.STRONG,
        )

        ledger.record(1000)
        ledger.record(2000)
        assert ledger.count == 2

        est_anomaly = model.estimate(
            recognition_state=RecognitionState.KNOWN,
            posterior=0.9,
            auth=AuthenticationStrength.STRONG,
        )
        assert est_anomaly.trust < est_clean.trust


class TestRelationship:
    def test_relationship_engine_and_healthy_ratio(self):
        eng = RelationshipEngine()
        rel = Relationship(profile_id="alice", rel_type=RelationshipType.INTRODUCED)
        eng.upsert(rel)

        assert eng.get("alice") is not None
        assert eng.get("alice").healthy_ratio == 0.5  # neutral initially

        eng.record_interaction("alice", positive=True)
        eng.record_interaction("alice", positive=True)
        eng.record_interaction("alice", positive=False)

        assert eng.get("alice").interaction_count == 3
        assert eng.get("alice").healthy_ratio == pytest.approx(2 / 3)
