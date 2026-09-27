"""Tests for RUKA VI Multimodal Evidence Fusion Mathematics (Part X & XXV).
Strictly verifies:
- Independent evidence fusion (Naive Bayes in logit space)
- Correlated evidence discount (1 - \bar{\rho}_i)
- Conflict score: 0 for unanimous evidence, high for contradictory signals
- Missing expected modality reporting
- Prior preservation on empty evidence
- Prior probability bounds validation in (0, 1)
"""

import numpy as np
import pytest

from ruka_companion.math.fusion import (
    ModalityEvidence,
    FusionConfig,
    EvidenceFuser,
    conflict_score,
)
from ruka_companion.math.probability import log_odds_to_prob, prob_to_log_odds


class TestEvidenceFusion:
    def test_independent_modalities_pure_additivity(self):
        fuser = EvidenceFuser(FusionConfig())  # zero correlation
        prior = 0.5  # logit = 0.0
        evidences = [
            ModalityEvidence("voice", 2.0, weight=1.0),
            ModalityEvidence("face", 3.0, weight=1.0),
        ]
        res = fuser.fuse(prior, evidences)

        # Fused LLR = 2.0 + 3.0 = 5.0
        assert res.fused_llr == pytest.approx(5.0, abs=1e-9)
        expected_post = log_odds_to_prob(prob_to_log_odds(0.5) + 5.0)
        assert res.posterior_prob == pytest.approx(expected_post, abs=1e-9)
        assert res.conflict == 0.0

    def test_correlated_modalities_discounted(self):
        # Voice and lips correlated with rho = 0.6
        cfg = FusionConfig(correlation={frozenset({"voice", "lips"}): 0.6})
        fuser = EvidenceFuser(cfg)
        evidences = [
            ModalityEvidence("voice", 2.0, weight=1.0),
            ModalityEvidence("lips", 2.0, weight=1.0),
        ]
        res = fuser.fuse(0.5, evidences)

        # With discount, contribution is strictly less than 4.0
        assert res.fused_llr < 4.0
        assert res.fused_llr > 0.0

    def test_conflict_score_zero_when_unanimous(self):
        # All positive
        pos_ev = [
            ModalityEvidence("voice", 3.0),
            ModalityEvidence("face", 2.5),
            ModalityEvidence("device", 1.0),
        ]
        assert conflict_score(pos_ev) == 0.0

        # All negative
        neg_ev = [
            ModalityEvidence("voice", -2.0),
            ModalityEvidence("face", -4.0),
        ]
        assert conflict_score(neg_ev) == 0.0

    def test_conflict_score_high_when_contradictory(self):
        # Contradictory: voice says Bos (+4.0), face says stranger (-4.0)
        contra = [
            ModalityEvidence("voice", 4.0),
            ModalityEvidence("face", -4.0),
        ]
        c = conflict_score(contra)
        assert c == pytest.approx(0.5, abs=1e-3)

    def test_empty_evidences_preserves_prior(self):
        fuser = EvidenceFuser()
        res = fuser.fuse(0.35, [])
        assert res.posterior_prob == pytest.approx(0.35, abs=1e-9)
        assert res.fused_llr == 0.0
        assert res.conflict == 0.0
        assert res.contributing == ()

    def test_missing_expected_modalities_reported(self):
        fuser = EvidenceFuser()
        evidences = [ModalityEvidence("voice", 2.0)]
        res = fuser.fuse(
            0.5,
            evidences,
            expected_modalities=["voice", "face", "device"],
        )
        assert set(res.missing_expected) == {"face", "device"}
        assert res.contributing == ("voice",)

    def test_invalid_prior_bounds_rejected(self):
        fuser = EvidenceFuser()
        with pytest.raises(ValueError):
            fuser.fuse(0.0, [ModalityEvidence("voice", 1.0)])
        with pytest.raises(ValueError):
            fuser.fuse(1.0, [ModalityEvidence("voice", 1.0)])


# ============================================================ Extended Tests
class TestFusionExtended:
    def test_single_modality_equals_raw_llr(self):
        fuser = EvidenceFuser(FusionConfig())
        res = fuser.fuse(0.5, [ModalityEvidence("voice", 3.0)])
        assert res.fused_llr == pytest.approx(3.0, abs=1e-9)

    def test_negative_evidence_decreases_posterior(self):
        fuser = EvidenceFuser()
        res = fuser.fuse(0.7, [ModalityEvidence("voice", -5.0)])
        assert res.posterior_prob < 0.7

    def test_positive_evidence_increases_posterior(self):
        fuser = EvidenceFuser()
        res = fuser.fuse(0.3, [ModalityEvidence("voice", 5.0)])
        assert res.posterior_prob > 0.3

    def test_weight_amplifies_contribution(self):
        fuser = EvidenceFuser(FusionConfig())
        res1 = fuser.fuse(0.5, [ModalityEvidence("voice", 2.0, weight=1.0)])
        res2 = fuser.fuse(0.5, [ModalityEvidence("voice", 2.0, weight=2.0)])
        assert res2.fused_llr > res1.fused_llr

    def test_posterior_logodds_consistent(self):
        fuser = EvidenceFuser()
        res = fuser.fuse(0.5, [ModalityEvidence("voice", 2.0)])
        expected = prob_to_log_odds(0.5) + 2.0
        assert res.posterior_logodds == pytest.approx(expected, abs=1e-9)

    def test_effective_contributions_keys(self):
        fuser = EvidenceFuser()
        res = fuser.fuse(
            0.5,
            [ModalityEvidence("voice", 2.0), ModalityEvidence("face", 3.0)],
        )
        assert "voice" in res.effective_contributions
        assert "face" in res.effective_contributions

    def test_correlation_matrix_explicit(self):
        fuser = EvidenceFuser()
        evidences = [
            ModalityEvidence("voice", 2.0),
            ModalityEvidence("face", 2.0),
        ]
        corr = np.array([[1.0, 0.5], [0.5, 1.0]])
        res = fuser.fuse(0.5, evidences, correlation_matrix=corr)
        # With correlation, fused LLR < 4.0 (independent sum)
        assert res.fused_llr < 4.0
        assert res.fused_llr > 0.0

    def test_correlation_matrix_wrong_size_rejected(self):
        fuser = EvidenceFuser()
        evidences = [ModalityEvidence("voice", 2.0), ModalityEvidence("face", 2.0)]
        bad_corr = np.eye(3)  # 3x3 for 2 evidences
        with pytest.raises(ValueError):
            fuser.fuse(0.5, evidences, correlation_matrix=bad_corr)

    def test_missing_penalty_shrinks_posterior(self):
        cfg = FusionConfig(missing_penalty=0.5)
        fuser = EvidenceFuser(cfg)
        res = fuser.fuse(
            0.7,
            [ModalityEvidence("voice", 2.0)],
            expected_modalities=["voice", "face"],
        )
        # Compare with no penalty
        fuser_no = EvidenceFuser(FusionConfig())
        res_no = fuser_no.fuse(0.7, [ModalityEvidence("voice", 2.0)])
        assert res.posterior_prob < res_no.posterior_prob

    def test_conflict_empty_is_zero(self):
        assert conflict_score([]) == 0.0

    def test_conflict_single_is_zero(self):
        assert conflict_score([ModalityEvidence("v", 3.0)]) == 0.0

    def test_fused_llr_monotone_with_evidence(self):
        fuser = EvidenceFuser()
        r1 = fuser.fuse(0.5, [ModalityEvidence("v", 2.0)])
        r2 = fuser.fuse(0.5, [ModalityEvidence("v", 2.0), ModalityEvidence("f", 2.0)])
        assert r2.fused_llr >= r1.fused_llr

