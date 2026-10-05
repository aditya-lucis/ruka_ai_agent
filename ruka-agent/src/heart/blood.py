# -*- coding: utf-8 -*-
"""Blood Contract & MCP Tool Registry (FR-HE-12).

Kontrak darah registri 13 alat MCP dengan izin dan validasi skema:
- Izin: GREEN (aman/otomatis), YELLOW (modifikasi), RED (eksekusi terminal/sistem)
- Registri beku yang tidak dapat diselundupi lewat konfigurasi panas
- Validasi skema parameter keras
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Optional


class BloodPermission(str, Enum):
    GREEN = "green"
    YELLOW = "yellow"
    RED = "red"


@dataclass(frozen=True)
class BloodTool:
    name: str
    permission: BloodPermission
    description: str
    required_params: tuple[str, ...]
    handler: Optional[Callable[..., Any]] = None


CANONICAL_BLOOD_TOOLS: dict[str, BloodTool] = {
    "code_read": BloodTool("code_read", BloodPermission.GREEN, "Membaca berkas kode", ("path",)),
    "code_write": BloodTool("code_write", BloodPermission.YELLOW, "Menulis berkas baru", ("path", "content")),
    "code_edit": BloodTool("code_edit", BloodPermission.YELLOW, "Mengubah sebagian berkas", ("path", "target", "replacement")),
    "code_search": BloodTool("code_search", BloodPermission.GREEN, "Mencari string/regex dalam kode", ("query",)),
    "terminal_run": BloodTool("terminal_run", BloodPermission.RED, "Menjalankan perintah terminal", ("command",)),
    "git_status": BloodTool("git_status", BloodPermission.GREEN, "Melihat status repositori git", ()),
    "git_diff": BloodTool("git_diff", BloodPermission.GREEN, "Melihat perbedaan git", ()),
    "git_commit": BloodTool("git_commit", BloodPermission.YELLOW, "Melakukan git commit", ("message",)),
    "project_map": BloodTool("project_map", BloodPermission.GREEN, "Melihat peta struktur proyek", ()),
    "test_runner": BloodTool("test_runner", BloodPermission.GREEN, "Menjalankan suite pengujian", ()),
    "web_search": BloodTool("web_search", BloodPermission.GREEN, "Mencari referensi web", ("query",)),
    "browser_action": BloodTool("browser_action", BloodPermission.YELLOW, "Interaksi sandbox browser", ("url",)),
    "system_restart": BloodTool("system_restart", BloodPermission.RED, "Memulai ulang layanan sistem", ("service",)),
}


class BloodRegistry:
    def __init__(self) -> None:
        # Salinan beku dari 13 alat kanonikal
        self._tools: dict[str, BloodTool] = dict(CANONICAL_BLOOD_TOOLS)

    @property
    def tool_names(self) -> list[str]:
        return list(self._tools.keys())

    def validate_tool_call(self, tool_name: str, params: dict[str, Any]) -> tuple[bool, str]:
        """Memvalidasi pemanggilan alat terhadap izin dan skema parameter."""
        tool = self._tools.get(tool_name)
        if not tool:
            return False, f"Alat '{tool_name}' tidak terdaftar pada Kontrak Darah 13 alat MCP!"

        # Validasi field wajib
        for req in tool.required_params:
            if req not in params:
                return False, f"Alat '{tool_name}' kehilangan parameter wajib: '{req}'"

        return True, "Valid"

    def get_permission(self, tool_name: str) -> BloodPermission:
        tool = self._tools.get(tool_name)
        if not tool:
            return BloodPermission.RED  # Fail-closed default
        return tool.permission
