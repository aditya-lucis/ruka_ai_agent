import json
import time
from pathlib import Path
import pytest
from ruka_persistence.runtime.supervisor import acquire_lock, InstanceLockError, HEARTBEAT_TIMEOUT_S

def test_acquire_fresh_lock(tmp_path):
    lock_path = tmp_path / "heartbeat.json"
    
    # Instance 1 acquires lock
    lock1 = acquire_lock(lock_path, pid=100)
    assert lock_path.exists()
    
    data = json.loads(lock_path.read_text(encoding="utf-8"))
    assert data["pid"] == 100
    
    # Instance 2 tries to acquire immediately -> fails
    with pytest.raises(InstanceLockError, match="instance lain hidup"):
        acquire_lock(lock_path, pid=200)

def test_acquire_stale_lock(tmp_path):
    lock_path = tmp_path / "heartbeat.json"
    
    # Simulate a stale lock from 20 seconds ago
    now = time.time()
    stale_time = now - 20.0
    lock_path.write_text(json.dumps({"pid": 100, "last_heartbeat": stale_time}))
    
    # Instance 2 tries to acquire -> succeeds
    lock2 = acquire_lock(lock_path, pid=200, now=now)
    data = json.loads(lock_path.read_text(encoding="utf-8"))
    assert data["pid"] == 200
