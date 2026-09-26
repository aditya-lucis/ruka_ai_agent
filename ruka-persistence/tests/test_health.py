import pytest
from ruka_persistence.runtime.health import RuntimeHealth, ComponentStatus
from ruka_persistence.runtime.statemachine import RuntimeStateMachine, RuntimeStatus

def test_runtime_health_evaluation():
    health = RuntimeHealth()
    fsm = RuntimeStateMachine()
    
    # Init: OFFLINE state, heartbeat fresh, but no components yet
    health.evaluate(fsm, heartbeat_fresh=True)
    assert health.liveness is True
    assert health.readiness is False # Not operational
    
    # State READY, but component DEGRADED
    fsm._state = RuntimeStatus.READY  # bypass transition for test
    health.set("memory", ComponentStatus.DEGRADED)
    health.evaluate(fsm, heartbeat_fresh=True)
    assert health.liveness is True
    assert health.readiness is False  # not all OK
    
    # State READY, all components OK
    health.set("memory", ComponentStatus.OK)
    health.evaluate(fsm, heartbeat_fresh=True)
    assert health.liveness is True
    assert health.readiness is True
    
    # Heartbeat stale
    health.evaluate(fsm, heartbeat_fresh=False)
    assert health.liveness is False
    # Readiness is independent of liveness (it just checks state and component OK)
    assert health.readiness is True
