import pytest
from src.state.core import InternalState, utcnow

def test_begin_task_guard():
    st = InternalState()
    st.begin_task("riset pasar")
    with pytest.raises(RuntimeError, match="budget"):
        st.begin_task("task kedua ilegal")

def test_advance_requires_running():
    st = InternalState()
    with pytest.raises(RuntimeError, match="running"):
        st.advance_step("tanpa task")

def test_snapshot_is_flat_and_safe():
    st = InternalState()
    st.begin_task("uji snapshot")
    snap = st.snapshot()
    assert set(snap) == {"task", "emotion", "expression",
                         "confidence", "turn"}
    assert snap["task"]["status"] == "running"

def test_session_scoped_by_default():
    """State segi sembilan TIDAK persisten — hanya identity."""
    st = InternalState()
    st.interaction.turn = 42
    fresh = InternalState()
    assert fresh.interaction.turn == 0
