from datetime import datetime, timedelta, timezone
import pytest
from src.state.core import EmotionalSimState
from src.emotion.appraisal import (AppraisalEngine, EventKind,
                                   EmotionalSignal, classify)

T0 = datetime(2026, 9, 7, 12, 0, tzinfo=timezone.utc)

def test_tool_error_moves_negative_and_focus():
    st = EmotionalSimState()
    out = AppraisalEngine(st).appraise(EventKind.TOOL_ERROR, now=T0)
    assert out["v"] < 0 and out["a"] > 0.5
    assert out["signal"] in {"focused", "serious"}

def test_name_call_yields_focused():
    st = EmotionalSimState()
    eng = AppraisalEngine(st)
    eng.appraise(EventKind.USER_CALLED_NAME, now=T0)
    assert classify(st.valence, st.arousal, st.dominance) == EmotionalSignal.FOCUSED

def test_decay_returns_toward_neutral():
    st = EmotionalSimState(valence=-0.8, arousal=0.9)
    st.updated_at = T0
    eng = AppraisalEngine(st)
    eng._decay_to_now(T0 + timedelta(minutes=10))
    assert st.valence > -0.8  # menuju 0
    assert st.arousal < 0.9   # menuju 0

def test_unknown_event_fails_loud():
    st = EmotionalSimState()
    with pytest.raises(KeyError):
        # AppraisalEngine(st).appraise("event_tak_ada")  
        # Note: the implementation expects a string or Enum, raising ValueError or KeyError if not found.
        # We need to ensure it raises KeyError specifically for the test. Let's adapt the test to match the implementation.
        # Wait, the code I wrote says: kind = EventKind(kind) which raises ValueError. Let me fix the appraise method in my next thought.
        # I'll just use KeyError here and I will fix the appraisal engine to raise KeyError.
        AppraisalEngine(st).appraise("event_tak_ada")
