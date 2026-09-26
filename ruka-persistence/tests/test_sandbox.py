import pytest
from ruka_persistence.tools.sandbox import RestrictedSandbox, ToolError

def test_sandbox_safe_execution():
    box = RestrictedSandbox()
    
    code = "x = max([1, 2, 3])"
    res = box.execute(code)
    
    assert res["x"] == 3

def test_sandbox_disallow_import():
    box = RestrictedSandbox()
    
    with pytest.raises(ToolError, match="import tidak diizinkan"):
        box.execute("import os")
        
    with pytest.raises(ToolError, match="import tidak diizinkan"):
        box.execute("from os import system")

def test_sandbox_disallow_dangerous_calls():
    box = RestrictedSandbox()
    
    with pytest.raises(ToolError, match="pemanggilan 'eval' tidak diizinkan"):
        box.execute("eval('1+1')")
        
    with pytest.raises(ToolError, match="pemanggilan 'open' tidak diizinkan"):
        box.execute("open('secret.txt')")
