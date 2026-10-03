# -*- coding: utf-8 -*-
"""RUKA Gateway — Permissions and Security Enforcement.

Menegakkan Zero-Trust Security, Path Jail, dan konfirmasi persetujuan
sebelum pemanggilan operasi berisiko tinggi di tingkat Gateway.
"""
from __future__ import annotations

import os
import re
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


#: Permissions that change state; skills holding any of them always need human approval.
MUTATING_PERMISSIONS = frozenset(
    {
        Permission.FS_WRITE.value,
        Permission.SHELL_EXECUTE.value,
        Permission.SYSTEM_CONTROL.value,
    }
)


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

    @staticmethod
    def _forbidden_workspace_roots() -> list[Path]:
        """Direktori yang tidak boleh dijadikan workspace (terlalu luas atau sistem)."""
        roots: list[Path] = []
        for env in ("WINDIR", "SystemRoot", "ProgramFiles", "ProgramFiles(x86)", "ProgramData"):
            val = os.environ.get(env)
            if val:
                roots.append(Path(val).resolve())
        for unix_sys in ("/etc", "/bin", "/sbin", "/usr", "/boot", "/sys", "/proc"):
            if os.name != "nt":
                roots.append(Path(unix_sys))
        return roots

    def set_workspace(self, path: str | Path) -> Path:
        """Mengganti workspace PathJail secara aman.

        Menolak: bukan direktori, root drive/filesystem, direktori home itu sendiri,
        serta direktori sistem operasi (beserta turunannya). Jail dibagikan ke seluruh
        skill sehingga perubahan berlaku seragam.
        """
        if not path or not str(path).strip():
            raise PermissionError("Workspace tidak boleh kosong.")
        p_str = str(path).strip().replace("\\", "/")
        if os.name == "nt" and re.match(r"^/[a-zA-Z]/", p_str):
            p_str = re.sub(r"^/([a-zA-Z])/", r"\1:/", p_str)
        target = Path(p_str).expanduser().resolve()
        if not target.exists() or not target.is_dir():
            raise PermissionError(f"Workspace bukan direktori yang valid: {target}")
        if target.parent == target:
            raise PermissionError(f"Workspace tidak boleh berupa root filesystem: {target}")
        if target == Path.home().resolve():
            raise PermissionError(
                "Workspace tidak boleh berupa direktori home itu sendiri; pilih folder proyek."
            )
        for forbidden in self._forbidden_workspace_roots():
            if target == forbidden or forbidden in target.parents:
                raise PermissionError(f"Workspace berada di direktori sistem yang dilarang: {target}")
        self.jail.base = target
        return target

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

    def requires_approval(
        self,
        risk_level: str | RiskLevel,
        explicit_flag: bool = False,
        permissions: Sequence[str] = (),
    ) -> bool:
        """Kebijakan persetujuan Zero-Trust.

        Perlu persetujuan Young Lord bila: risiko high/critical, skill menandai
        ``requires_confirmation``, ATAU skill memegang izin yang mengubah state
        (tulis berkas / shell / kontrol sistem) walau metadatanya mengaku risiko rendah.
        """
        if self.requires_confirmation(risk_level, explicit_flag):
            return True
        return any(str(p) in MUTATING_PERMISSIONS for p in permissions)

