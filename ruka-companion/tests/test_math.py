import pytest
import numpy as np

from ruka_companion.math.linalg import cosine_similarity, pca, project
from ruka_companion.math.probability import bayes_update_logodds, log_odds_to_prob
from ruka_companion.math.decision import decide, WorldState, Action
from ruka_companion.math.fusion import EvidenceFuser, ModalityEvidence
from ruka_companion.math.metrics import eer
from ruka_companion.math.distributed import compare_version_vectors, VectorRelation, merge_version_vectors
from ruka_companion.math.discrete import DAG, DAGError

def test_linalg():
    x = [1, 2, 2]
    y = [2, 4, 4]
    assert np.isclose(cosine_similarity(x, y), 1.0)
    assert np.isclose(cosine_similarity(x, [-2, -4, -4]), -1.0)
    
    # Proyeksi
    p = project([3, 4], [1, 0])
    assert np.allclose(p, [3, 0])

def test_probability():
    # logit P' = 0 + 2.2 + (-1.3) = 0.9 -> P' ~ 0.7109
    p = log_odds_to_prob(bayes_update_logodds(0.5, 2.2 - 1.3))
    assert np.isclose(p, 0.7109, atol=1e-4)

def test_decision():
    d = decide({
        WorldState.REQUEST_LEGITIMATE: 0.80,
        WorldState.REQUEST_ADRIFT: 0.15,
        WorldState.REQUEST_ADVERSARIAL: 0.05
    })
    assert d.action == Action.ASK_HUMAN
    assert np.isclose(d.expected_losses[Action.ASK_HUMAN], 0.515)

def test_fusion():
    f = EvidenceFuser()
    r = f.fuse(0.5, [
        ModalityEvidence("voice", 2.5, 0.9),
        ModalityEvidence("face", 2.5, 0.9)
    ])
    # independent: logit = 0.9*2.5 + 0.9*2.5 = 4.5 -> P = 0.9890
    assert np.isclose(r.posterior_prob, 0.9890, atol=1e-4)

def test_metrics():
    thresholds = [0.30, 0.35]
    fars = [0.12, 0.05]
    frrs = [0.04, 0.10]
    eer_val, t_star = eer(thresholds, fars, frrs)
    assert np.isclose(t_star, 0.330769, atol=1e-4)
    assert np.isclose(eer_val, 0.076923, atol=1e-4)

def test_distributed():
    v1 = {"local": 2}
    v2 = {"cloud": 1}
    assert compare_version_vectors(v1, v2) == VectorRelation.CONCURRENT
    
    vm = merge_version_vectors(v1, v2)
    assert vm["local"] == 2 and vm["cloud"] == 1

def test_discrete():
    dag = DAG()
    dag.add_edge("A", "B")
    dag.add_edge("B", "C")
    assert dag.topological_sort() == ["A", "B", "C"]
    
    with pytest.raises(DAGError):
        dag.add_edge("C", "A")
