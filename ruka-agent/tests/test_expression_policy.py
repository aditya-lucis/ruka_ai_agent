"""Unit tests for ExpressionPolicy and HonestyGuard — Ruka Volume IV Listing 12.2 & 12.3."""

import numpy as np
import pytest

from ruka_perception.expression.policy import ExpressionPolicy, HonestyGuard
from ruka_perception.expression.state import ExpressionState, STATE_DIMS


def _state_with_concern(concern_val: float = 0.8) -> ExpressionState:
    """Helper: buat state dengan concern tinggi."""
    es = ExpressionState(max_delta=1.0)
    event = np.zeros(5)
    event[STATE_DIMS.index("concern")] = concern_val
    es.step(event=event)
    return es


def test_honesty_guard_protected_kinds():
    """Pesan dengan kind terlindungi harus mengembalikan False (tidak boleh dimask)."""
    guard = HonestyGuard()
    for kind in ["error_disclosure", "capability_limit", "uncertainty", "security_warning"]:
        assert guard.check({"kind": kind}) is False


def test_honesty_guard_unprotected_kinds():
    """Pesan biasa harus bisa dimask."""
    guard = HonestyGuard()
    assert guard.check({"kind": "smalltalk"}) is True
    assert guard.check({"kind": "compliment"}) is True
    assert guard.check({}) is True


def test_express_error_verbatim():
    """Invarian buku: pesan error HARUS disampaikan verbatim (tidak dimask)."""
    policy = ExpressionPolicy()
    es = _state_with_concern(0.9)
    result = policy.express(es, {"kind": "error_disclosure", "text": "Module crashed."})
    assert result["verbatim"] is True


def test_express_smalltalk_not_verbatim():
    """Smalltalk boleh dimask oleh persona."""
    policy = ExpressionPolicy()
    es = ExpressionState()
    result = policy.express(es, {"kind": "smalltalk", "text": "Hello!"})
    assert result["verbatim"] is False


def test_text_style_concern_softened():
    """Invarian buku: concern_shown < concern_actual karena PERSONA_SOFTENING=0.6."""
    policy = ExpressionPolicy()
    es = _state_with_concern(0.9)
    style = policy.text_style(es)
    concern_actual = style["masked_cue"]["concern_actual"]
    concern_shown = style["masked_cue"]["concern_shown"]
    assert concern_shown < concern_actual, (
        f"concern tidak disoftening: actual={concern_actual:.3f}, shown={concern_shown:.3f}"
    )


def test_text_style_contains_masked_cue():
    """text_style harus selalu menyertakan masked_cue untuk audit."""
    policy = ExpressionPolicy()
    es = ExpressionState()
    style = policy.text_style(es)
    assert "masked_cue" in style
    assert "concern_actual" in style["masked_cue"]
    assert "concern_shown" in style["masked_cue"]


def test_voice_style_concern_tag():
    """Concern > 0.6 harus menghasilkan audio tag [hesitant]."""
    policy = ExpressionPolicy()
    es = ExpressionState(max_delta=1.0)
    event = np.zeros(5)
    event[STATE_DIMS.index("concern")] = 1.0
    # 3 langkah event concern untuk mendorong > 0.6
    for _ in range(3):
        es.step(event=event)
    vstyle = policy.voice_style(es)
    assert vstyle["concern_level"] > 0.6
    assert vstyle["audio_tag"] == "[hesitant]"


def test_avatar_style_label_neutral_at_baseline():
    """State di baseline harus menghasilkan label avatar 'neutral'."""
    policy = ExpressionPolicy()
    es = ExpressionState()
    astyle = policy.avatar_style(es)
    assert astyle["label"] == "neutral"


def test_express_result_keys():
    """Hasil express harus mengandung semua kunci output yang diharapkan."""
    policy = ExpressionPolicy()
    es = ExpressionState()
    result = policy.express(es, {"kind": "greeting"})
    assert "verbatim" in result
    assert "text_style" in result
    assert "voice_style" in result
    assert "avatar_style" in result
