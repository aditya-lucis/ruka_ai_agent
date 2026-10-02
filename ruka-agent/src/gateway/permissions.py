# -*- coding: utf-8 -*-
"""RUKA Gateway — Permissions and Security Enforcement.

Menegakkan Zero-Trust Security, Path Jail, dan konfirmasi persetujuan
sebelum pemanggilan operasi berisiko tinggi di tingkat Gateway.
"""
from __future__ import annotations

import os
from enum import Enum
from pathlib import Path
from typing import Any, Sequence

from src.tools.coding import PathJail


class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class Permission(str, Enum):
    FS_READ = "filesystem:read"
    FS_WRITE = "filesystem:write"
    SHELL_EXECUTE = "shell:execute"
    NETWORK_FETCH = "network:fetch"
    SYSTEM_CONTROL = "system:control"


class PermissionError(RuntimeError):
    """Galat ketika izin operasi ditolak oleh Gateway."""
    pass


class PermissionManager:
    """Manajer hak akses dan kurung keamanan (Path Jail) di Gateway."""

    def __init__(self, workspace_root: str | Path | None = None) -> None:
        self.jail = PathJail(workspace_root)
        self._granted_permissions: set[str] = {
            Permission.FS_READ.value,
            Permission.FS_WRITE.value,
            Permission.SHELL_EXECUTE.value,
            Permission.NETWORK_FETCH.value,
        }

    def verify_path(self, target_path: str | Path) -> Path:
        """Memvalidasi dan mengurung jalur berkas agar tidak keluar dari workspace."""
        return self.jail.confine(target_path)

    def check_permissions(self, required_permissions: Sequence[str]) -> bool:
        """Memeriksa apakah seluruh izin yang diminta telah dikabulkan."""
        for perm in required_permissions:
            if perm not in self._granted_permissions:
                return False
        return True

    def requires_confirmation(self, risk_level: str | RiskLevel, explicit_flag: bool = False) -> bool:
        """Menentukan apakah aksi membutuhkan persetujuan langsung dari Young Lord."""
        if explicit_flag:
            return True
        val = risk_level.value if isinstance(risk_level, RiskLevel) else str(risk_level)
        r = val.strip().lower()
        return r in (RiskLevel.HIGH.value, RiskLevel.CRITICAL.value)

