import asyncio
import pytest
from src.state.machine import ExpressionFSM, InvalidTransition, Phase

def test_illegal_jump_rejected_loudly():
    fsm = ExpressionFSM()
    with pytest.raises(InvalidTransition, match="tidak sah"):
        fsm.transition(Phase.TOOL_EXECUTING)   # idle -> tool: ilegal

def test_full_turn_cycle_is_valid():
    fsm = ExpressionFSM()
    for dst, cause in [(Phase.LISTENING, "input"),
                       (Phase.THINKING, "parsed"),
                       (Phase.TOOL_EXECUTING, "call"),
                       (Phase.THINKING, "result"),
                       (Phase.RESPONDING, "answer"),
                       (Phase.IDLE, "done")]:
        fsm.transition(dst, cause)
    assert fsm.history[-1]["to"] == "idle"

def test_busy_means_thinking_or_tool():
    fsm = ExpressionFSM()
    fsm.transition(Phase.LISTENING, "input")
    fsm.transition(Phase.THINKING, "parsed")
    assert fsm.is_busy() is True

def test_concurrent_transitions_cannot_interleave():
    """Dua transisi async bersamaan: satu menang, satu ditolak keras."""
    async def race():
        fsm = ExpressionFSM()
        fsm.transition(Phase.LISTENING, "input")
        results = await asyncio.gather(
            fsm.transition_async(Phase.THINKING, "a"),
            fsm.transition_async(Phase.THINKING, "b"),
            return_exceptions=True,
        )
        return results

    results = asyncio.run(race())
    assert any(isinstance(r, InvalidTransition) for r in results)
    assert Phase.THINKING in results

def test_reset_records_cause():
    fsm = ExpressionFSM()
    fsm.transition(Phase.LISTENING, "input")
    fsm.reset(cause="user_interrupt")
    assert fsm.phase is Phase.IDLE
    assert fsm.history[-1]["cause"] == "user_interrupt"
