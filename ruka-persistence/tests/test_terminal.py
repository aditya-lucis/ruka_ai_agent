import pytest
from ruka_persistence.tools.terminal import CommandPolicy, TerminalSession, ToolError

def test_command_policy():
    policy = CommandPolicy()
    assert policy.check("ls -la") is True
    assert policy.check("rm -rf /") is False
    assert policy.check("mkfs.ext4 /dev/sda1") is False

def test_terminal_session():
    policy = CommandPolicy()
    session = TerminalSession(policy)
    
    assert session.execute("echo hello") == "hello"
    
    with pytest.raises(ToolError, match="Command blocked"):
        session.execute("rm -rf /")
