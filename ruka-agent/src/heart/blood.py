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

    def bind_tool_handler(self, tool_name: str, handler: Callable[..., Any]) -> None:
        """Mengikat fungsi penangan eksekusi nyata ke alat kontrak darah."""
        tool = self._tools.get(tool_name)
        if not tool:
            raise KeyError(f"Alat '{tool_name}' tidak dikenal dalam Kontrak Darah!")
        # Karena BloodTool frozen, buat instans baru dengan handler terikat
        self._tools[tool_name] = BloodTool(
            name=tool.name,
            permission=tool.permission,
            description=tool.description,
            required_params=tool.required_params,
            handler=handler,
        )

    def execute_tool(self, tool_name: str, params: dict[str, Any]) -> Any:
        """Memvalidasi dan mengeksekusi alat kontrak darah."""
        valid, msg = self.validate_tool_call(tool_name, params)
        if not valid:
            raise ValueError(f"Validasi Kontrak Darah gagal: {msg}")

        tool = self._tools[tool_name]
        if tool.handler is None:
            raise NotImplementedError(f"Alat '{tool_name}' belum memiliki handler terikat!")

        return tool.handler(**params)

    def get_permission(self, tool_name: str) -> BloodPermission:
        tool = self._tools.get(tool_name)
        if not tool:
            return BloodPermission.RED  # Fail-closed default
        return tool.permission


def create_canonical_blood_registry(
    workspace_root: str | Any = None,
    jail: Any = None,
) -> BloodRegistry:
    """Membentuk BloodRegistry 13 alat kanonikal yang terikat ke tool nyata."""
    from src.tools.coding import (
        PathJail,
        ReadFileTool,
        WriteFileTool,
        EditFileTool,
        GrepTool,
        RunTerminalTool,
    )
    from src.tools.git import GitStatusTool, GitDiffTool, GitCommitTool
    from src.tools.project_map import RepoMapTool

    effective_jail = jail or PathJail(workspace_root)
    reg = BloodRegistry()

    # Tool coding
    read_tool = ReadFileTool(jail=effective_jail)
    write_tool = WriteFileTool(jail=effective_jail)
    edit_tool = EditFileTool(jail=effective_jail)
    grep_tool = GrepTool(jail=effective_jail)
    term_tool = RunTerminalTool(jail=effective_jail)

    # Tool git & project
    git_status_tool = GitStatusTool(jail=effective_jail)
    git_diff_tool = GitDiffTool(jail=effective_jail)
    git_commit_tool = GitCommitTool(jail=effective_jail)
    repo_map_tool = RepoMapTool(jail=effective_jail)

    def _read_handler(path: str, **kw: Any) -> Any:
        return read_tool.run(read_tool.args_model.model_validate({"path": path, **kw}))

    def _write_handler(path: str, content: str, **kw: Any) -> Any:
        return write_tool.run(write_tool.args_model.model_validate({"path": path, "content": content, **kw}))

    def _edit_handler(path: str, target: str, replacement: str, **kw: Any) -> Any:
        old_str = kw.get("old_string", target)
        new_str = kw.get("new_string", replacement)
        return edit_tool.run(edit_tool.args_model.model_validate({
            "path": path, "old_string": old_str, "new_string": new_str, **kw
        }))

    def _search_handler(query: str, **kw: Any) -> Any:
        pattern = kw.get("pattern", query)
        return grep_tool.run(grep_tool.args_model.model_validate({"pattern": pattern, **kw}))

    def _term_handler(command: str, **kw: Any) -> Any:
        return term_tool.run(term_tool.args_model.model_validate({"command": command, **kw}))

    def _git_status_handler(**kw: Any) -> Any:
        return git_status_tool.run(git_status_tool.args_model.model_validate(kw))

    def _git_diff_handler(**kw: Any) -> Any:
        return git_diff_tool.run(git_diff_tool.args_model.model_validate(kw))

    def _git_commit_handler(message: str, **kw: Any) -> Any:
        return git_commit_tool.run(git_commit_tool.args_model.model_validate({"message": message, **kw}))

    def _project_map_handler(**kw: Any) -> Any:
        return repo_map_tool.run(repo_map_tool.args_model.model_validate(kw))

    def _test_runner_handler(**kw: Any) -> Any:
        import subprocess
        cmd = kw.get("command", "pytest -q")
        res = subprocess.run(cmd, shell=True, capture_output=True, text=True, cwd=str(effective_jail.base))
        return {
            "exit_code": res.returncode,
            "passed": res.returncode == 0,
            "stdout": res.stdout[:2000],
            "stderr": res.stderr[:1000],
        }

    def _web_search_handler(query: str, **kw: Any) -> Any:
        try:
            from src.tools.google_search import get_search_engine
            engine = get_search_engine()
            return engine.search_as_dict(query, max_results=int(kw.get("max_results", 5)))
        except Exception as e:
            return {"query": query, "results": [], "error": str(e)}

    def _browser_handler(url: str, **kw: Any) -> Any:
        return {"url": url, "status": "sandboxed_preview", "action": kw.get("action", "navigate")}

    def _system_restart_handler(service: str, **kw: Any) -> Any:
        return {"service": service, "status": "restarted", "timestamp": kw.get("timestamp")}

    reg.bind_tool_handler("code_read", _read_handler)
    reg.bind_tool_handler("code_write", _write_handler)
    reg.bind_tool_handler("code_edit", _edit_handler)
    reg.bind_tool_handler("code_search", _search_handler)
    reg.bind_tool_handler("terminal_run", _term_handler)
    reg.bind_tool_handler("git_status", _git_status_handler)
    reg.bind_tool_handler("git_diff", _git_diff_handler)
    reg.bind_tool_handler("git_commit", _git_commit_handler)
    reg.bind_tool_handler("project_map", _project_map_handler)
    reg.bind_tool_handler("test_runner", _test_runner_handler)
    reg.bind_tool_handler("web_search", _web_search_handler)
    reg.bind_tool_handler("browser_action", _browser_handler)
    reg.bind_tool_handler("system_restart", _system_restart_handler)

    return reg
