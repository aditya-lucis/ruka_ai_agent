"""RUKA VI: Tests for Identity & Trust Subsystem.
Strictly follows RUKA-VI Chapter IX & XXV testing protocol.
"""

from __future__ import annotations

import time
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


class TestIdentityExtended:
    """Tambahan uji 4-lapis identitas: Recognition, Authentication, Authorization/Delegation, Trust, Relasi."""

    def test_unregistered_profile_unknown_state(self):
        eng = IdentityEngine()
        eng.enroll(PROFILE_BOS)
        # Sinyal negatif kuat -> bukan Bos
        ev = _evidence(ModalitySignal(modality=Modality.VOICE, llr=-5.0))
        r = eng.recognize(ev)
        assert r.state == RecognitionState.UNKNOWN
        assert r.posterior_prob < 0.2

    def test_low_confidence_llr(self):
        eng = IdentityEngine()
        eng.enroll(PROFILE_BOS)
        # Sinyal positif sangat lemah
        ev = _evidence(ModalitySignal(modality=Modality.VOICE, llr=0.4))
        r = eng.recognize(ev)
        assert r.state in (RecognitionState.LOW_CONFIDENCE, RecognitionState.UNKNOWN)

    def test_reject_state_large_negative_llr(self):
        eng = IdentityEngine()
        eng.enroll(PROFILE_BOS)
        ev = _evidence(
            ModalitySignal(modality=Modality.VOICE, llr=-8.0),
            ModalitySignal(modality=Modality.FACE, llr=-8.0),
        )
        r = eng.recognize(ev)
        assert r.state == RecognitionState.UNKNOWN
        assert r.posterior_prob < 0.01

    def test_winner_takes_it_multiple_profiles(self):
        eng = IdentityEngine()
        eng.enroll(PROFILE_BOS)
        eng.enroll(PROFILE_ALICE)
        ev = _evidence(
            ModalitySignal(modality=Modality.VOICE, llr=4.0),
            ModalitySignal(modality=Modality.FACE, llr=4.0),
        )
        r = eng.recognize(ev)
        assert r.profile_id in ("bos", "alice")
        assert r.state == RecognitionState.KNOWN

    def test_evidence_discount_applied_on_correlated_signals(self):
        eng = IdentityEngine()
        eng.enroll(PROFILE_BOS)
        # Dua sinyal voice independen vs 1 sinyal
        ev_single = _evidence(ModalitySignal(modality=Modality.VOICE, llr=2.0))
        ev_dual = _evidence(
            ModalitySignal(modality=Modality.VOICE, llr=2.0),
            ModalitySignal(modality=Modality.FACE, llr=2.0),
        )
        r_single = eng.recognize(ev_single)
        r_dual = eng.recognize(ev_dual)
        assert r_dual.posterior_prob > r_single.posterior_prob

    def test_two_same_modalities_not_strong(self):
        eng = IdentityEngine()
        eng.enroll(PROFILE_BOS)
        # Dua sinyal modality yang sama (keduanya VOICE)
        ev = _evidence(
            ModalitySignal(modality=Modality.VOICE, llr=3.0),
            ModalitySignal(modality=Modality.VOICE, llr=3.0),
        )
        r = eng.recognize(ev)
        auth = eng.authenticate(r)
        # Harus tetap WEAK karena hanya ada 1 modalitas independen
        assert auth == AuthenticationStrength.WEAK

    def test_unknown_recognition_gives_none_auth(self):
        eng = IdentityEngine()
        eng.enroll(PROFILE_BOS)
        ev = _evidence(ModalitySignal(modality=Modality.VOICE, llr=-10.0))
        r = eng.recognize(ev)
        assert r.state == RecognitionState.UNKNOWN
        auth = eng.authenticate(r)
        assert auth == AuthenticationStrength.NONE

    def test_mfa_overrides_weak_evidence(self):
        eng = IdentityEngine()
        eng.enroll(PROFILE_BOS)
        ev = _evidence(ModalitySignal(modality=Modality.VOICE, llr=1.0))
        r = eng.recognize(ev)
        auth = eng.authenticate(r, mfa_confirmed=True)
        assert auth == AuthenticationStrength.MFA_CONFIRMED

    def test_suspicious_recognition_gives_none_or_weak_auth(self):
        eng = IdentityEngine()
        eng.enroll(PROFILE_BOS)
        ev = _evidence(
            ModalitySignal(modality=Modality.VOICE, llr=5.0),
            ModalitySignal(modality=Modality.FACE, llr=-5.0),
        )
        r = eng.recognize(ev)
        assert r.state == RecognitionState.SUSPICIOUS
        auth = eng.authenticate(r)
        assert auth in (AuthenticationStrength.NONE, AuthenticationStrength.WEAK)

    def test_suspicious_state_forces_deny_or_ask(self):
        eng = IdentityEngine()
        eng.enroll(PROFILE_BOS)
        ev = _evidence(
            ModalitySignal(modality=Modality.VOICE, llr=5.0),
            ModalitySignal(modality=Modality.FACE, llr=-5.0),
        )
        r = eng.recognize(ev)
        auth = eng.authenticate(r)
        action = eng.decide_action(r, auth, risk_cost=10.0)
        assert action in (Action.ASK, Action.DENY)
        assert action != Action.EXECUTE

    def test_unknown_state_denies_medium_risk(self):
        eng = IdentityEngine()
        eng.enroll(PROFILE_BOS)
        ev = _evidence(ModalitySignal(modality=Modality.VOICE, llr=-5.0))
        r = eng.recognize(ev)
        auth = eng.authenticate(r)
        action = eng.decide_action(r, auth, risk_cost=30.0)
        assert action in (Action.DENY, Action.ASK)

    def test_mfa_confirmed_allows_destructive_action(self):
        eng = IdentityEngine()
        eng.enroll(PROFILE_BOS)
        ev = _evidence(
            ModalitySignal(modality=Modality.VOICE, llr=3.0),
            ModalitySignal(modality=Modality.FACE, llr=3.0),
        )
        r = eng.recognize(ev)
        auth = eng.authenticate(r, mfa_confirmed=True)
        action = eng.decide_action(r, auth, risk_cost=100.0)
        assert action in (Action.ASK, Action.ASK_HUMAN)

    def test_delegation_expired_at_check(self):
        reg = DelegationRegistry()
        grant = reg.propose("bos", "alice", {"filesystem.read"}, ttl_ms=100)
        reg.confirm(grant.grant_id)
        now = int(time.time() * 1000)

        # Before expiry
        ok, _ = reg.check("alice", "filesystem.read", now_ms=now)
        assert ok is True

        # After expiry
        ok_expired, reason = reg.check("alice", "filesystem.read", now_ms=now + 500)
        assert ok_expired is False
        assert "EXPIRED" in reason or "state=" in reason

    def test_delegation_double_activate_raises(self):
        reg = DelegationRegistry()
        grant = reg.propose("bos", "alice", {"filesystem.read"})
        reg.confirm(grant.grant_id)
        with pytest.raises(ValueError, match="aktivasi ilegal"):
            grant.activate()

    def test_delegation_revoke_with_reason(self):
        reg = DelegationRegistry()
        grant = reg.propose("bos", "alice", {"filesystem.read"})
        reg.confirm(grant.grant_id)
        reg.revoke(grant.grant_id, reason="security_audit")
        assert grant.state == DelegationState.REVOKED
        assert grant.revoked_reason == "security_audit"

    def test_delegation_invalid_ttl_raises(self):
        reg = DelegationRegistry()
        with pytest.raises(ValueError, match="ttl_ms > 0"):
            reg.propose("bos", "alice", {"filesystem.read"}, ttl_ms=-100)

    def test_delegation_unknown_grant_keyerror(self):
        reg = DelegationRegistry()
        with pytest.raises(KeyError):
            reg.confirm("dlg-nonexistent")
        with pytest.raises(KeyError):
            reg.revoke("dlg-nonexistent")

    def test_trust_unverified_device_penalty(self):
        model = TrustModel()
        est_verified = model.estimate(
            recognition_state=RecognitionState.KNOWN,
            posterior=0.9,
            auth=AuthenticationStrength.STRONG,
            device_verified=True,
        )
        est_unverified = model.estimate(
            recognition_state=RecognitionState.KNOWN,
            posterior=0.9,
            auth=AuthenticationStrength.STRONG,
            device_verified=False,
        )
        assert est_verified.trust > est_unverified.trust

    def test_trust_posterior_out_of_bounds_raises(self):
        model = TrustModel()
        with pytest.raises(ValueError, match="posterior"):
            model.estimate(RecognitionState.KNOWN, posterior=1.5, auth=AuthenticationStrength.STRONG)
        with pytest.raises(ValueError, match="posterior"):
            model.estimate(RecognitionState.KNOWN, posterior=-0.1, auth=AuthenticationStrength.STRONG)

    def test_trust_healthy_ratio_out_of_bounds_raises(self):
        model = TrustModel()
        with pytest.raises(ValueError, match="healthy_ratio"):
            model.estimate(RecognitionState.KNOWN, posterior=0.8, auth=AuthenticationStrength.STRONG, healthy_ratio=1.2)

    def test_relationship_stranger_initial(self):
        eng = RelationshipEngine()
        assert eng.get("unknown_person") is None

    def test_relationship_type_transitions(self):
        eng = RelationshipEngine()
        rel = Relationship(profile_id="charlie", rel_type=RelationshipType.UNKNOWN)
        eng.upsert(rel)
        assert eng.get("charlie").rel_type == RelationshipType.UNKNOWN

        rel_upgraded = Relationship(profile_id="charlie", rel_type=RelationshipType.INTRODUCED)
        eng.upsert(rel_upgraded)
        assert eng.get("charlie").rel_type == RelationshipType.INTRODUCED

    def test_relationship_negative_interactions_decay_ratio(self):
        eng = RelationshipEngine()
        rel = Relationship(profile_id="bad_actor", rel_type=RelationshipType.SERVICE)
        eng.upsert(rel)
        for _ in range(5):
            eng.record_interaction("bad_actor", positive=False)
        assert eng.get("bad_actor").healthy_ratio == 0.0

