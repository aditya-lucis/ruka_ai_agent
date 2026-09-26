from enum import Enum

class PermissionLevel(Enum):
    READ = 1
    SANDBOX_WRITE = 2
    DESTRUCTIVE = 3
    SYSTEM = 4

PERMISSION_MATRIX = {
    "read_text": PermissionLevel.READ,
    "search_text": PermissionLevel.READ,
    "write_text": PermissionLevel.SANDBOX_WRITE,
    "delete_file": PermissionLevel.DESTRUCTIVE,
    "shutdown": PermissionLevel.SYSTEM
}

class PermissionPolicy:
    def check(self, tool_name: str, requested_level: PermissionLevel) -> bool:
        required = PERMISSION_MATRIX.get(tool_name)
        if required is None:
            return False
        return requested_level.value >= required.value
