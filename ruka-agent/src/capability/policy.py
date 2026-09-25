"""Policy layer — keputusan izin sebelum eksekusi.
Fusion registry (P14) + lingkungan (P2) + konteks task (P13).
Keputusan SELALU dicatat; tolakan selalu bawa alasan.
"""
from __future__ import annotations
from dataclasses import dataclass
from src.capability.registry import Permission
from src.config import Settings

@dataclass(frozen=True)
class Decision:
    allowed: bool
    reason: str
    requires_user_confirm: bool = False

class ToolPolicy:
    """Ambang izin per lingkungan — production lebih ketat."""
    ALLOWED_IN_ENV: dict[str, set[Permission]] = {
        "development": {Permission.READ, Permission.WRITE,
                         Permission.EXECUTE, Permission.NETWORK,
                         Permission.DESTRUCTIVE},
        "staging": {Permission.READ, Permission.WRITE,
                    Permission.EXECUTE, Permission.NETWORK},
        "production": {Permission.READ, Permission.WRITE,
                       Permission.NETWORK},
    }

    def __init__(self, settings: Settings) -> None:
        self._env = settings.environment

    def decide(self, permission: Permission,
               confirmed_by_user: bool = False) -> Decision:
        if permission is Permission.DESTRUCTIVE and not confirmed_by_user:
            return Decision(False,
                            "tool DESTRUCTIVE butuh konfirmasi user "
                            "untuk panggilan ini",
                            requires_user_confirm=True)
        allowed_here = self.ALLOWED_IN_ENV.get(self._env, set())
        if permission not in allowed_here:
            return Decision(False,
                            f"permission {permission.value} diblok "
                            f"di lingkungan {self._env}")
        return Decision(True, f"permission {permission.value} ok di {self._env}")
