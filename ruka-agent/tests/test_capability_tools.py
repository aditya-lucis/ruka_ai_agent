import pytest
from src.capability.registry import (CapabilityRegistry,
                                     Permission, ToolIdentity)

def _ident(name: str, perm: Permission) -> ToolIdentity:
    return ToolIdentity(name=name, description=f"tool {name}",
                        permission=perm,
                        parameters={"type": "object", "properties": {}})

def test_register_and_statement_grouped_by_permission():
    reg = CapabilityRegistry()
    reg.register(_ident("read_file", Permission.READ), handler=lambda a: a)
    reg.register(_ident("run_python", Permission.EXECUTE), handler=lambda a: a)
    st = reg.capability_statement()
    assert st == {"read": ["read_file"], "execute": ["run_python"]}

def test_duplicate_registration_rejected():
    reg = CapabilityRegistry()
    reg.register(_ident("read_file", Permission.READ), handler=lambda a: a)
    with pytest.raises(ValueError, match="duplikat"):
        reg.register(_ident("read_file", Permission.READ), handler=lambda a: a)

def test_schemas_for_llm_shape_matches_interactions_api():
    reg = CapabilityRegistry()
    reg.register(_ident("get_time", Permission.READ), handler=lambda a: a)
    schema = reg.schemas_for_llm()[0]
    assert schema["type"] == "function" and schema["name"] == "get_time"
    assert "parameters" in schema and "description" in schema

def test_audit_ring_buffer_capped():
    reg = CapabilityRegistry()
    reg.register(_ident("get_time", Permission.READ), handler=lambda a: a)
    rec = reg.get("get_time")
    for i in range(300):
        rec.log_call({}, "ok" if i % 2 else "failure", ms=1.0)
    assert len(rec.audit) == 200              # capped, bukan tumbuh
    assert rec.call_count == 300               # statistik tak terpotong

def test_unknown_tool_fails_loud():
    with pytest.raises(KeyError, match="tak terdaftar"):
        CapabilityRegistry().get("hack_tool")
