# -*- coding: utf-8 -*-
"""Unit tests for src.math_foundations module.
Memastikan semua kalkulasi aljabar linier, probabilitas, optimasi,
teori informasi, graf, kontrol loop, dan statistik teruji dengan tuntas.
"""
import math
import numpy as np
import pytest

from src.math_foundations.types import Score, Belief, BeliefState
from src.math_foundations.linear import (
    l2_normalize,
    cosine_similarity,
    batch_cosine,
    euclidean_distance,
    batch_euclidean,
    vector_projection,
    orthonormalize,
)
from src.math_foundations.probability import (
    shannon_entropy,
    bayesian_update,
    brier_score,
    expected_calibration_error,
    softmax,
    temperature_scale,
)
from src.math_foundations.optimization import (
    utility_score,
    softmax_select,
    pareto_frontier_indices,
)
from src.math_foundations.information import (
    kl_divergence,
    memory_surprise,
    importance_score,
    mutual_information_discrete,
)
from src.math_foundations.graph import (
    detect_cycles,
    topological_sort,
    topological_levels,
    critical_path_length,
)
from src.math_foundations.control import (
    loop_health,
    BudgetController,
)
from src.math_foundations.statistical import (
    RunningStats,
    exponential_moving_average,
    wasserstein_distance_1d,
    classification_metrics,
)


class TestTypes:
    def test_score_behavior(self):
        s = Score(value=0.85, confidence=0.92, components={"dense": 0.8, "lexical": 0.05})
        assert float(s) == 0.85
        assert int(s) == 0
        assert s.confidence == 0.92
        assert s.components["dense"] == 0.8
        # Comparisons
        assert s > 0.80
        assert s >= 0.85
        assert s < 0.90
        assert s <= 0.85
        assert s == 0.85
        # Arithmetic
        assert s + 0.15 == pytest.approx(1.0)
        assert 0.15 + s == pytest.approx(1.0)
        assert s * 2 == pytest.approx(1.7)
        assert 2 * s == pytest.approx(1.7)
        assert s - 0.35 == pytest.approx(0.5)
        assert 1.0 - s == pytest.approx(0.15)
        assert s / 2 == pytest.approx(0.425)

    def test_score_clamping(self):
        s_high = Score(value=1.5, confidence=1.8)
        assert s_high.confidence == 1.0
        s_low = Score(value=-0.5, confidence=-0.2)
        assert s_low.confidence == 0.0

    def test_belief_and_state(self):
        state = BeliefState()
        b = state.set_belief("user_prefers_terse", 0.75, evidence=["request 1", "request 2"])
        assert b.hypothesis == "user_prefers_terse"
        assert b.probability == 0.75
        assert state.get_probability("user_prefers_terse") == 0.75
        assert state.get_probability("unknown", default=0.1) == 0.1


class TestLinear:
    def test_l2_normalize_1d(self):
        v = np.array([3.0, 4.0])
        vn = l2_normalize(v)
        assert np.linalg.norm(vn) == pytest.approx(1.0)
        assert vn[0] == pytest.approx(0.6)
        assert vn[1] == pytest.approx(0.8)

    def test_l2_normalize_zero(self):
        v = np.array([0.0, 0.0, 0.0])
        vn = l2_normalize(v)
        assert np.all(vn == 0.0)

    def test_l2_normalize_2d(self):
        m = np.array([[3.0, 4.0], [0.0, 0.0], [1.0, 1.0]])
        mn = l2_normalize(m)
        assert np.linalg.norm(mn[0]) == pytest.approx(1.0)
        assert np.all(mn[1] == 0.0)
        assert np.linalg.norm(mn[2]) == pytest.approx(1.0)

    def test_cosine_similarity(self):
        a = np.array([1.0, 0.0])
        b = np.array([0.0, 1.0])
        c = np.array([1.0, 0.0])
        d = np.array([-1.0, 0.0])
        zero = np.array([0.0, 0.0])

        assert cosine_similarity(a, c) == pytest.approx(1.0)
        assert cosine_similarity(a, b) == pytest.approx(0.0)
        assert cosine_similarity(a, d) == pytest.approx(-1.0)
        assert cosine_similarity(a, zero) == 0.0

    def test_batch_cosine(self):
        q = np.array([1.0, 0.0])
        m = np.array([
            [1.0, 0.0],
            [0.0, 1.0],
            [-1.0, 0.0],
            [0.5, 0.5],
        ])
        scores = batch_cosine(q, m)
        assert len(scores) == 4
        assert scores[0] == pytest.approx(1.0)
        assert scores[1] == pytest.approx(0.0)
        assert scores[2] == pytest.approx(-1.0)
        assert scores[3] == pytest.approx(1.0 / math.sqrt(2.0))

    def test_batch_cosine_empty(self):
        q = np.array([1.0, 0.0])
        m = np.empty((0, 2))
        scores = batch_cosine(q, m)
        assert len(scores) == 0

    def test_euclidean_and_projection(self):
        a = np.array([1.0, 2.0])
        b = np.array([4.0, 6.0])
        assert euclidean_distance(a, b) == pytest.approx(5.0)

        proj = vector_projection(np.array([2.0, 2.0]), np.array([1.0, 0.0]))
        assert proj[0] == pytest.approx(2.0)
        assert proj[1] == pytest.approx(0.0)

    def test_orthonormalize(self):
        v = np.array([[1.0, 1.0], [1.0, 0.0]])
        basis = orthonormalize(v)
        assert len(basis) == 2
        assert np.linalg.norm(basis[0]) == pytest.approx(1.0)
        assert np.linalg.norm(basis[1]) == pytest.approx(1.0)
        assert np.dot(basis[0], basis[1]) == pytest.approx(0.0, abs=1e-6)


class TestProbability:
    def test_entropy(self):
        # Distribusi seragam 2 kelas -> 1 bit
        uniform = [0.5, 0.5]
        assert shannon_entropy(uniform) == pytest.approx(1.0)

        # Distribusi pasti -> 0 bit
        certain = [1.0, 0.0]
        assert shannon_entropy(certain) == pytest.approx(0.0)

        # Distribusi 4 kelas seragam -> 2 bit
        uniform4 = [0.25, 0.25, 0.25, 0.25]
        assert shannon_entropy(uniform4) == pytest.approx(2.0)

    def test_bayesian_update(self):
        # Prior 0.5, likelihood 0.9, false alarm 0.1
        # P = (0.9 * 0.5) / (0.9 * 0.5 + 0.1 * 0.5) = 0.45 / 0.50 = 0.9
        post = bayesian_update(prior=0.5, likelihood=0.9, false_alarm_prob=0.1)
        assert post == pytest.approx(0.9)

        # Prior 0.0 -> tetap 0.0
        assert bayesian_update(0.0, 0.8, 0.2) == pytest.approx(0.0)
        # Prior 1.0 -> tetap 1.0
        assert bayesian_update(1.0, 0.8, 0.2) == pytest.approx(1.0)

    def test_calibration_and_brier(self):
        probs = [0.9, 0.8, 0.2]
        labels = [1, 1, 0]
        bs = brier_score(probs, labels)
        expected_bs = ((0.9 - 1)**2 + (0.8 - 1)**2 + (0.2 - 0)**2) / 3
        assert bs == pytest.approx(expected_bs)

        ece = expected_calibration_error(probs, labels, n_bins=5)
        assert 0.0 <= ece <= 1.0

    def test_softmax(self):
        logits = [2.0, 1.0, 0.1]
        probs = softmax(logits)
        assert np.sum(probs) == pytest.approx(1.0)
        assert probs[0] > probs[1] > probs[2]


class TestOptimizationAndInformation:
    def test_utility_score(self):
        u = utility_score(benefit=0.9, cost=0.2, risk=0.1, weights=(1.0, 0.5, 0.5))
        # 0.9 - 0.5*0.2 - 0.5*0.1 = 0.9 - 0.1 - 0.05 = 0.75
        assert u == pytest.approx(0.75)

    def test_softmax_select_greedy(self):
        scores = [0.1, 0.95, 0.2]
        idx = softmax_select(scores, temperature=0.0)
        assert idx == 1

    def test_pareto_frontier(self):
        costs = [1.0, 2.0, 3.0, 1.5]
        benefits = [5.0, 7.0, 6.0, 6.5]
        indices = pareto_frontier_indices(costs, benefits)
        # Point 0: cost 1.0, ben 5.0
        # Point 3: cost 1.5, ben 6.5
        # Point 1: cost 2.0, ben 7.0
        # Point 2: cost 3.0, ben 6.0 is dominated by Point 1 (lower cost, higher benefit)
        assert 2 not in indices
        assert 0 in indices
        assert 1 in indices
        assert 3 in indices

    def test_kl_divergence(self):
        p = [0.5, 0.5]
        q = [0.5, 0.5]
        assert kl_divergence(p, q) == pytest.approx(0.0)

        p2 = [0.9, 0.1]
        q2 = [0.1, 0.9]
        assert kl_divergence(p2, q2) > 0.0

    def test_importance_score_and_surprise(self):
        s_expected = memory_surprise(0.99)
        s_surprising = memory_surprise(0.01)
        assert s_surprising > s_expected

        imp = importance_score(relevance=0.8, recency=0.9, surprise=0.5)
        assert 0.0 <= imp <= 1.0


class TestGraphAndControl:
    def test_detect_cycles(self):
        # A -> B -> C -> A
        adj = {"A": ["B"], "B": ["C"], "C": ["A"]}
        cycles = detect_cycles(adj)
        assert len(cycles) > 0

        # No cycle
        adj_dag = {"A": ["B", "C"], "B": ["D"], "C": ["D"]}
        assert len(detect_cycles(adj_dag)) == 0

    def test_topological_sort_and_levels(self):
        nodes = ["A", "B", "C", "D"]
        edges = {"A": ["B", "C"], "B": ["D"], "C": ["D"]}
        ordered = topological_sort(nodes, edges)
        assert ordered.index("A") < ordered.index("B")
        assert ordered.index("A") < ordered.index("C")
        assert ordered.index("B") < ordered.index("D")
        assert ordered.index("C") < ordered.index("D")

        levels = topological_levels(nodes, edges)
        assert levels[0] == ["A"]
        assert sorted(levels[1]) == ["B", "C"]
        assert levels[2] == ["D"]

    def test_critical_path(self):
        nodes = ["A", "B", "C", "D"]
        edges = {"A": ["B", "C"], "B": ["D"], "C": ["D"]}
        durations = {"A": 2.0, "B": 5.0, "C": 1.0, "D": 3.0}
        # Path A->B->D = 2 + 5 + 3 = 10
        # Path A->C->D = 2 + 1 + 3 = 6
        assert critical_path_length(nodes, edges, durations) == pytest.approx(10.0)

    def test_loop_health_and_budget(self):
        h_good = loop_health(repeated_errors=0, max_allowed_errors=3, iterations=1, budget_iterations=20)
        assert h_good > 0.9

        h_bad = loop_health(repeated_errors=3, max_allowed_errors=3, iterations=20, budget_iterations=20)
        assert h_bad == 0.0

        bc = BudgetController(max_tokens=1000, max_iterations=5, max_time_seconds=60)
        assert not bc.is_exhausted()
        for _ in range(5):
            bc.record_step(tokens=200)
        assert bc.is_exhausted()
        summary = bc.summary()
        assert summary["exhausted"] is True


class TestStatistical:
    def test_running_stats(self):
        rs = RunningStats()
        data = [2.0, 4.0, 4.0, 4.0, 5.0, 5.0, 7.0, 9.0]
        for x in data:
            rs.update(x)
        assert rs.count == len(data)
        assert rs.mean == pytest.approx(np.mean(data))
        assert rs.variance == pytest.approx(np.var(data, ddof=1))
        assert rs.standard_deviation == pytest.approx(np.std(data, ddof=1))
        assert rs.min_val == 2.0
        assert rs.max_val == 9.0

    def test_ema(self):
        ema = exponential_moving_average(previous=10.0, current=20.0, alpha=0.5)
        assert ema == pytest.approx(15.0)

    def test_wasserstein_drift(self):
        a = [1.0, 2.0, 3.0]
        b = [1.0, 2.0, 3.0]
        assert wasserstein_distance_1d(a, b) == pytest.approx(0.0)

        c = [4.0, 5.0, 6.0]
        assert wasserstein_distance_1d(a, c) == pytest.approx(3.0)

    def test_classification_metrics(self):
        yt = [1, 1, 0, 0]
        yp = [1, 0, 0, 1]
        m = classification_metrics(yt, yp)
        assert m["accuracy"] == 0.5


class TestRetrievalScoring:
    def test_vector_store_returns_score_object(self, tmp_path):
        from src.retrieval.store import VectorStore
        from src.retrieval.chunker import Chunk

        db_file = str(tmp_path / "test_retrieval.db")
        store = VectorStore(dim=3, path=db_file)
        chunks = [
            Chunk(text="High match text", source="doc1.md", heading="Intro"),
            Chunk(text="Low match text", source="doc2.md", heading=""),
        ]
        vecs = [
            [1.0, 0.0, 0.0],
            [0.0, 1.0, 0.0],
        ]
        store.add(chunks, vecs)

        results = store.search([1.0, 0.0, 0.0], top_k=2, min_score=0.2)
        assert len(results) == 1
        res = results[0]
        assert isinstance(res.score, Score)
        assert res.score.value == pytest.approx(1.0)
        assert res.score.confidence > 0.8
        assert "cosine" in res.score.components
        assert res.score.components["heading_depth"] == 1.0
        store.conn.close()

