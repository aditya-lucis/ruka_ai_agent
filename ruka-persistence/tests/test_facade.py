import pytest
import time
from pathlib import Path
from ruka_persistence.facade import RukaPersistentMind
from ruka_persistence.selfmodel.self import PersistentSelf
from ruka_persistence.runtime.statemachine import RuntimeStatus

def test_facade_boot_success(tmp_path):
    base_dir = tmp_path / "ruka_home"
    base_dir.mkdir()
    
    # Create identity
    identity_path = base_dir / "identity.json"
    p = PersistentSelf("Ruka", time.time())
    p.save(identity_path)
    
    mind = RukaPersistentMind(base_dir)
    report = mind.boot(identity_path)
    
    assert report.final_state == RuntimeStatus.READY.value
    assert report.failed_gate == ""
    
    status = mind.get_status()
    assert status["fsm"]["state"] == RuntimeStatus.READY.value
    assert status["health"]["liveness"] is True

def test_facade_boot_identity_fail(tmp_path):
    base_dir = tmp_path / "ruka_home2"
    base_dir.mkdir()
    
    # Create corrupted identity
    identity_path = base_dir / "identity.json"
    identity_path.write_text("corrupted json data")
    
    mind = RukaPersistentMind(base_dir)
    report = mind.boot(identity_path)
    
    assert report.final_state == RuntimeStatus.DEGRADED.value
    
def test_facade_shutdown(tmp_path):
    base_dir = tmp_path / "ruka_home3"
    base_dir.mkdir()
    
    identity_path = base_dir / "identity.json"
    p = PersistentSelf("Ruka", time.time())
    p.save(identity_path)
    
    mind = RukaPersistentMind(base_dir)
    mind.boot(identity_path)
    
    report = mind.shutdown()
    assert report.outcome == "graceful"
    
    status = mind.get_status()
    assert status["fsm"]["state"] == RuntimeStatus.OFFLINE.value
