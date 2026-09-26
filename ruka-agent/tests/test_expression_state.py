"""Unit tests for ExpressionState — Ruka Volume IV Listing 12.4."""

import numpy as np
import pytest

from ruka_perception.expression.state import ExpressionState, STATE_DIMS


def test_state_dims_contract():
    """Kontrak urutan STATE_DIMS tidak berubah — lima dimensi tetap."""
    assert STATE_DIMS == ["calm", "curiosity", "concern", "playfulness", "confidence"]
    assert len(STATE_DIMS) == 5


def test_initial_state_equals_baseline():
    """State awal harus identik dengan baseline."""
    es = ExpressionState()
    np.testing.assert_array_equal(es.s, es.baseline)


def test_parameter_validation():
    """alpha, beta, gamma harus di [0,1]; max_delta di (0,1]."""
    with pytest.raises(ValueError, match="alpha, beta, gamma"):
        ExpressionState(alpha=1.5)
    with pytest.raises(ValueError, match="alpha, beta, gamma"):
        ExpressionState(beta=-0.1)
    with pytest.raises(ValueError, match="max_delta"):
        ExpressionState(max_delta=0.0)
    with pytest.raises(ValueError, match="max_delta"):
        ExpressionState(max_delta=1.5)


def test_baseline_shape_validation():
    """Baseline harus (5,)."""
    with pytest.raises(ValueError, match="baseline harus"):
        ExpressionState(baseline=np.array([0.5, 0.5]))


def test_step_returns_clamped_values():
    """State setelah step harus dalam [0.0, 1.0]."""
    es = ExpressionState()
    # Event ekstrem
    big_event = np.array([0.0, 0.0, 2.0, 0.0, 0.0])
    for _ in range(10):
        s = es.step(event=big_event)
    assert np.all(s >= 0.0)
    assert np.all(s <= 1.0)


def test_single_event_limited_by_max_delta():
    """Invarian buku: satu event tidak melompati max_delta."""
    max_d = 0.25
    es = ExpressionState(max_delta=max_d)
    s_before = es.s.copy()
    concern_event = np.zeros(5)
    concern_event[2] = 1.0  # concern spike
    es.step(event=concern_event)
    jump = float(np.max(np.abs(es.s - s_before)))
    assert jump <= max_d + 1e-6, f"lompatan {jump:.4f} melebihi max_delta {max_d}"


def test_decay_returns_to_baseline_after_quiet():
    """Invarian buku: setelah 40 langkah tenang, state mendekati baseline."""
    es = ExpressionState(alpha=0.88, gamma=0.35, max_delta=0.18)
    concern_event = np.array([0, 0, 0.7, 0, -0.3])
    # Dorong concern naik
    for _ in range(5):
        es.step(event=concern_event)
    # Langkah tenang tanpa event
    for _ in range(40):
        es.step()
    dist = float(np.linalg.norm(es.s - es.baseline))
    assert dist < 0.15, f"tidak pulih ke baseline, jarak = {dist:.4f}"


def test_persistent_signal_accumulates():
    """Sinyal konteks persisten selama 20 langkah harus terakumulasi (concern > 0.5)."""
    es = ExpressionState(alpha=0.88, gamma=0.35, max_delta=0.18, update_gain=1.0)
    concern_event = np.array([0, 0, 0.7, 0, 0])
    for _ in range(20):
        es.step(event=concern_event)
    concern_idx = STATE_DIMS.index("concern")
    assert es.s[concern_idx] >= 0.5, f"akumulasi gagal: concern = {es.s[concern_idx]:.4f}"


def test_alternating_events_produce_oscillation():
    """Event bolak-balik menghasilkan osc_rate > 0.4."""
    es = ExpressionState(alpha=0.95, gamma=0.8, max_delta=0.5)
    up = np.array([0, 0, 0.9, 0, 0])
    down = np.array([0, 0, -0.9, 0, 0])
    for _ in range(12):
        es.step(event=up)
        es.step(event=down)
    report = es.stability_report(window=16)
    assert report["osc_rate"] > 0.4, f"osc_rate = {report['osc_rate']:.4f}"


def test_stable_config_lower_jump():
    """Model stabil (kecil max_delta=0.18) harus memiliki mean_jump lebih kecil daripada reaktif."""
    events = [np.array([0, 0.6, 0.1, 0.0, 0.3]) * ((-1) ** i) for i in range(12)]

    es_reactive = ExpressionState(alpha=1.0, gamma=1.0, max_delta=1.0)
    for ev in events:
        es_reactive.step(event=ev)
    report_r = es_reactive.stability_report()

    es_stable = ExpressionState(alpha=0.88, gamma=0.35, max_delta=0.18)
    for ev in events:
        es_stable.step(event=ev)
    report_s = es_stable.stability_report()

    assert report_s["mean_jump"] < report_r["mean_jump"]


def test_dominant_and_avatar_label():
    """dominant() dan to_avatar_label() harus konsisten."""
    es = ExpressionState()
    # Push curiosity tinggi
    curious_event = np.array([0, 1.0, 0, 0, 0])
    for _ in range(8):
        es.step(event=curious_event)
    dom = es.dominant()
    assert dom in STATE_DIMS

    label = es.to_avatar_label()
    assert label in {"neutral", "calm", "curious", "concerned", "playful", "proud"}


def test_history_grows_each_step():
    """Riwayat state harus tumbuh +1 per langkah."""
    es = ExpressionState()
    assert len(es.history) == 1  # initial
    es.step()
    assert len(es.history) == 2
    es.step()
    assert len(es.history) == 3


def test_stability_report_settled():
    """State di baseline harus dilaporkan sebagai settled."""
    es = ExpressionState()
    report = es.stability_report()
    assert report["settled"] is True
