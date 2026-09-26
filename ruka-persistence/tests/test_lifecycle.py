import pytest
from ruka_persistence.memory.lifecycle import MemoryLifecycle, MemoryState

def test_memory_state_transitions():
    mem = MemoryLifecycle()
    assert mem.state == MemoryState.ACTIVE
    
    mem.transition(MemoryState.ARCHIVED)
    assert mem.state == MemoryState.ARCHIVED
    
    with pytest.raises(ValueError, match="Tidak bisa kembali active"):
        mem.transition(MemoryState.ACTIVE)
        
def test_idempotent_forget():
    mem = MemoryLifecycle()
    assert mem.content != ""
    
    res1 = mem.forget()
    assert res1 is True
    assert mem.state == MemoryState.DELETED
    assert mem.content == ""  # tombstone
    
    res2 = mem.forget()
    assert res2 is True
