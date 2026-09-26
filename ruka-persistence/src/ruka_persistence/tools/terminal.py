import re
import subprocess
from dataclasses import dataclass, field
from ruka_persistence.tools.path_jail import ToolError

class CommandPolicy:
    def __init__(self):
        self.denylist = [
            r"^rm\s+-rf\s+/",
            r"^mkfs",
            r"^dd\s+if=",
            r"> /dev/sda",
            # add more as needed
        ]
        self.compiled = [re.compile(p) for p in self.denylist]

    def check(self, cmd: str) -> bool:
        for p in self.compiled:
            if p.search(cmd):
                return False
        return True

class TerminalSession:
    def __init__(self, policy: CommandPolicy):
        self.policy = policy
        self.state = "IDLE"

    def execute(self, cmd: str) -> str:
        if not self.policy.check(cmd):
            raise ToolError("Command blocked by policy")
        
        self.state = "RUNNING"
        try:
            # For safety in tests, we only echo
            if cmd.startswith("echo "):
                result = cmd[5:]
            else:
                result = "Simulated output for " + cmd
            self.state = "IDLE"
            return result
        except Exception as e:
            self.state = "ERROR"
            raise ToolError(str(e))
