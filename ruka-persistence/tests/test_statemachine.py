import pytest
from ruka_persistence.runtime.statemachine import (
    RuntimeStateMachine, RuntimeStatus, IllegalTransition, boot_sequence
)

def test_statemachine_legal_transition():
    fsm = RuntimeStateMachine()
    assert fsm.state == RuntimeStatus.OFFLINE
    
    fsm.transition(RuntimeStatus.STARTING, "boot")
    assert fsm.state == RuntimeStatus.STARTING
    assert fsm.is_operational() is False

def test_statemachine_illegal_transition():
    fsm = RuntimeStateMachine()
    
    with pytest.raises(IllegalTransition, match="transisi ilegal"):
        # OFFLINE to READY is illegal
        fsm.transition(RuntimeStatus.READY)
        
    assert fsm.rejections == 1

def test_boot_sequence_success():
    fsm = RuntimeStateMachine()
    state = boot_sequence(fsm)
    assert state == RuntimeStatus.READY
    assert fsm.is_operational() is True

def test_boot_sequence_identity_failure():
    fsm = RuntimeStateMachine()
    state = boot_sequence(fsm, identity_ok=False)
    assert state == RuntimeStatus.DEGRADED
    assert fsm.is_operational() is False
    assert fsm.events[-1].detail == "hash identitas tidak cocok / dokumen rusak"
