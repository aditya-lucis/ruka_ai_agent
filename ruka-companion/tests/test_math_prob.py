"""Tests for RUKA VI Probability, Decision Theory, and Biometric Metrics (Part V, VI, XXV).
Strictly verifies:
- Log-odds & probability: bijection, symmetry, monotonicity, domain bounds
- Sequential Bayesian updating: additivity, neutral evidence, directional shifts
- Statistical Decision Theory: expected loss minimization, matrix comparison (routine vs destructive)
- Biometric Metrics: EER interpolation, FAR/FRR monotonicity
"""

import math
import numpy as np
import pytest

from ruka_companion.math.probability import (
    log_odds_to_prob,
    prob_to_log_odds,
    bayes_update_logodds,
)
from ruka_companion.math.decision import (
    decide,
    WorldState,
    Action,
    LOSS_ROUTINE,
    LOSS_DESTRUCTIVE,
    ExpectedLossEngine,
)
from ruka_companion.math.metrics import eer


class TestLogOddsAndBayes:
    def test_roundtrip_bijection(self):
        for p in np.linspace(0.01, 0.99, 50):
            lo = prob_to_log_odds(p)
            p_rec = log_odds_to_prob(lo)
            assert p_rec == pytest.approx(p, abs=1e-12)

    def test_symmetry(self):
        for p in np.linspace(0.01, 0.49, 25):
            assert prob_to_log_odds(p) == pytest.approx(
                -prob_to_log_odds(1.0 - p), abs=1e-12
            )

    def test_half_is_zero(self):
        assert prob_to_log_odds(0.5) == pytest.approx(0.0, abs=1e-12)
        assert log_odds_to_prob(0.0) == pytest.approx(0.5, abs=1e-12)

    def test_monotonicity(self):
        probs = np.linspace(0.01, 0.99, 40)
        logodds = [prob_to_log_odds(p) for p in probs]
        for i in range(len(logodds) - 1):
            assert logodds[i] < logodds[i + 1]

    def test_invalid_probability_rejected(self):
        with pytest.raises(ValueError):
            prob_to_log_odds(0.0)
        with pytest.raises(ValueError):
            prob_to_log_odds(1.0)
        with pytest.raises(ValueError):
            prob_to_log_odds(-0.1)
        with pytest.raises(ValueError):
            prob_to_log_odds(1.1)

    def test_bayes_additivity(self):
        p0 = 0.5
        llr1 = 1.5
        llr2 = -0.5
        # One-step
        lo_combined = bayes_update_logodds(p0, llr1 + llr2)
        # Sequential
        lo_step1 = bayes_update_logodds(p0, llr1)
        p_step1 = log_odds_to_prob(lo_step1)
        lo_step2 = bayes_update_logodds(p_step1, llr2)

        assert lo_combined == pytest.approx(lo_step2, abs=1e-12)

    def test_neutral_evidence_preserves_prior(self):
        for p in [0.1, 0.3, 0.5, 0.7, 0.9]:
            lo = bayes_update_logodds(p, 0.0)
            assert log_odds_to_prob(lo) == pytest.approx(p, abs=1e-12)

    def test_positive_evidence_increases_posterior(self):
        p0 = 0.4
        lo = bayes_update_logodds(p0, 2.0)
        assert log_odds_to_prob(lo) > p0

    def test_negative_evidence_decreases_posterior(self):
        p0 = 0.6
        lo = bayes_update_logodds(p0, -2.0)
        assert log_odds_to_prob(lo) < p0


class TestDecisionTheory:
    def test_high_legitimate_chooses_execute(self):
        dist = {
            WorldState.REQUEST_LEGITIMATE: 0.98,
            WorldState.REQUEST_ADRIFT: 0.015,
            WorldState.REQUEST_ADVERSARIAL: 0.005,
        }
        res = decide(dist, loss_matrix=LOSS_ROUTINE)
        assert res.action == Action.EXECUTE
        assert res.expected_losses[Action.EXECUTE] < res.expected_losses[Action.DENY]

    def test_high_adrift_chooses_ask_human(self):
        dist = {
            WorldState.REQUEST_LEGITIMATE: 0.80,
            WorldState.REQUEST_ADRIFT: 0.15,
            WorldState.REQUEST_ADVERSARIAL: 0.05,
        }
        res = decide(dist, loss_matrix=LOSS_ROUTINE)
        assert res.action == Action.ASK_HUMAN

    def test_high_adversarial_chooses_deny(self):
        dist = {
            WorldState.REQUEST_LEGITIMATE: 0.10,
            WorldState.REQUEST_ADRIFT: 0.10,
            WorldState.REQUEST_ADVERSARIAL: 0.80,
        }
        res = decide(dist, loss_matrix=LOSS_ROUTINE)
        assert res.action == Action.DENY
        assert res.expected_losses[Action.DENY] < res.expected_losses[Action.EXECUTE]

    def test_destructive_matrix_penalizes_adversarial_execute(self):
        dist = {
            WorldState.REQUEST_LEGITIMATE: 0.90,
            WorldState.REQUEST_ADRIFT: 0.05,
            WorldState.REQUEST_ADVERSARIAL: 0.05,
        }
        res_routine = decide(dist, loss_matrix=LOSS_ROUTINE)
        res_destruct = decide(dist, loss_matrix=LOSS_DESTRUCTIVE)

        # Destructive loss for EXECUTE is much higher
        loss_exec_routine = res_routine.expected_losses[Action.EXECUTE]
        loss_exec_destruct = res_destruct.expected_losses[Action.EXECUTE]
        assert loss_exec_destruct > loss_exec_routine

    def test_unnormalized_distribution_rejected(self):
        with pytest.raises(ValueError):
            decide({
                WorldState.REQUEST_LEGITIMATE: 0.5,
                WorldState.REQUEST_ADRIFT: 0.1,
                WorldState.REQUEST_ADVERSARIAL: 0.1,
            })


class TestBiometricMetrics:
    def test_eer_computation_and_threshold(self):
        thresholds = [0.30, 0.35]
        fars = [0.12, 0.05]
        frrs = [0.04, 0.10]
        eer_val, t_star = eer(thresholds, fars, frrs)

        # EER is where FAR == FRR
        assert 0.30 < t_star < 0.35
        assert 0.04 < eer_val < 0.10
        assert np.isclose(t_star, 0.330769, atol=1e-4)
        assert np.isclose(eer_val, 0.076923, atol=1e-4)

    def test_monotonicity_of_error_rates(self):
        # As threshold increases, FAR drops and FRR rises
        thresholds = [0.1, 0.3, 0.5, 0.7, 0.9]
        fars = [0.50, 0.25, 0.10, 0.03, 0.001]
        frrs = [0.001, 0.02, 0.10, 0.30, 0.60]
        eer_val, t_star = eer(thresholds, fars, frrs)

        assert np.isclose(eer_val, 0.10, atol=1e-3)
        assert np.isclose(t_star, 0.50, atol=1e-3)


# ============================================================ Extended Tests
from ruka_companion.math.metrics import (
    far_frr, roc_curve, auc, youden_j, cost_optimal_threshold, threshold_report,
)


class TestDecisionTheoryExtended:
    def test_engine_posterior_from_confidence(self):
        eng = ExpectedLossEngine()
        p = eng.posterior_from_confidence(0.9)
        total = sum(p.values())
        assert total == pytest.approx(1.0, abs=1e-6)
        assert p[WorldState.REQUEST_LEGITIMATE] == 0.9

    def test_engine_low_confidence_leans_ask(self):
        eng = ExpectedLossEngine()
        p = eng.posterior_from_confidence(0.5)
        res = eng.decide(p)
        assert res.action in (Action.ASK_HUMAN, Action.DENY)

    def test_engine_very_high_confidence_executes(self):
        eng = ExpectedLossEngine(loss=dict(LOSS_ROUTINE))
        p = eng.posterior_from_confidence(0.99)
        res = eng.decide(p)
        assert res.action == Action.EXECUTE

    def test_all_actions_have_expected_losses(self):
        dist = {
            WorldState.REQUEST_LEGITIMATE: 0.8,
            WorldState.REQUEST_ADRIFT: 0.15,
            WorldState.REQUEST_ADVERSARIAL: 0.05,
        }
        res = decide(dist, loss_matrix=LOSS_ROUTINE)
        assert Action.EXECUTE in res.expected_losses
        assert Action.ASK_HUMAN in res.expected_losses
        assert Action.DENY in res.expected_losses

    def test_rationale_nonempty(self):
        dist = {
            WorldState.REQUEST_LEGITIMATE: 0.90,
            WorldState.REQUEST_ADRIFT: 0.05,
            WorldState.REQUEST_ADVERSARIAL: 0.05,
        }
        res = decide(dist)
        assert len(res.rationale) > 0


class TestBiometricMetricsExtended:
    def _make_scores(self):
        rng = np.random.default_rng(42)
        genuine = rng.normal(loc=3.0, scale=1.0, size=100).tolist()
        impostor = rng.normal(loc=0.0, scale=1.0, size=100).tolist()
        return genuine, impostor

    def test_far_frr_extreme_threshold(self):
        g, i = self._make_scores()
        far_lo, frr_lo = far_frr(g, i, threshold=-100.0)
        assert far_lo == pytest.approx(1.0, abs=0.01)  # all impostor >= -100
        assert frr_lo == pytest.approx(0.0, abs=0.01)   # all genuine >= -100

    def test_roc_curve_shape(self):
        g, i = self._make_scores()
        pts = roc_curve(g, i, n_points=51)
        assert len(pts) == 51
        # FAR should generally decrease as threshold increases
        assert pts[0].far >= pts[-1].far

    def test_auc_bounds(self):
        g, i = self._make_scores()
        a = auc(g, i)
        assert 0.0 <= a <= 1.0

    def test_auc_separated_close_to_one(self):
        g = [10.0, 11.0, 12.0]
        i = [0.0, 1.0, 2.0]
        a = auc(g, i)
        assert a == pytest.approx(1.0, abs=0.01)

    def test_youden_j_range(self):
        g, i = self._make_scores()
        _, j = youden_j(g, i)
        assert -1.0 <= j <= 1.0

    def test_cost_optimal_threshold_exists(self):
        g, i = self._make_scores()
        t = cost_optimal_threshold(g, i)
        assert isinstance(t, float)

    def test_threshold_report_keys(self):
        g, i = self._make_scores()
        rep = threshold_report(g, i)
        expected_keys = {
            "genuine_mean", "genuine_std", "impostor_mean", "impostor_std",
            "eer_threshold", "eer_value", "youden_threshold", "youden_j",
            "auc", "cost_optimal_threshold", "cost_at_optimal",
        }
        assert expected_keys.issubset(set(rep.keys()))

    def test_threshold_report_auc_consistent(self):
        g, i = self._make_scores()
        rep = threshold_report(g, i)
        assert rep["auc"] == pytest.approx(auc(g, i), abs=1e-6)

    def test_eer_two_arg_form(self):
        g, i = self._make_scores()
        t_star, eer_val = eer(g, i)
        assert isinstance(t_star, float)
        assert 0.0 <= eer_val <= 1.0

