# -*- coding: utf-8 -*-
"""RUKA Skills System — Coding Tools Bridge.

Menghubungkan implementasi tool coding yang sudah teruji (ReadFileTool, EditFileTool,
WriteFileTool, SearchCodeTool, TerminalTool) menjadi Skills resmi di SkillRegistry.
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from src.gateway.skills.models import Skill
from src.gateway.skills.loader import SkillLoader
from src.gateway.skills.registry import SkillRegistry
from src.tools.coding import (
    ReadFileTool,
    WriteFileTool,
    EditFileTool,
    GrepTool,
    ListDirTool,
    RunTerminalTool,
    PathJail,
)
from src.tools.git import (
    GitStatusTool,
    GitDiffTool,
    GitLogTool,
    GitCommitTool,
)
from src.tools.project_map import RepoMapTool

log = logging.getLogger("ruka.gateway.skills.bridge")


def register_builtin_coding_skills(
    registry: SkillRegistry,
    skills_dir: Path | str | None = None,
    workspace_root: Path | str | None = None,
    jail: PathJail | None = None,
) -> None:
    """Mendaftarkan seluruh tool coding dasar sebagai Skills resmi.

    Jika ``jail`` diberikan, instans itu dipakai bersama oleh semua tool sehingga
    perubahan workspace (PermissionManager.set_workspace) berlaku seragam.
    """
    jail = jail or PathJail(workspace_root)
    read_tool = ReadFileTool(jail=jail)
    write_tool = WriteFileTool(jail=jail)
    edit_tool = EditFileTool(jail=jail)
    search_tool = GrepTool(jail=jail)
    terminal_tool = RunTerminalTool(jail=jail)
    list_dir_tool = ListDirTool(jail=jail)

    git_status_tool = GitStatusTool(jail=jail)
    git_diff_tool = GitDiffTool(jail=jail)
    git_log_tool = GitLogTool(jail=jail)
    git_commit_tool = GitCommitTool(jail=jail)
    repo_map_tool = RepoMapTool(jail=jail)

    def _make_handler(tool: Any):
        def _handler(**kwargs: Any) -> Any:
            validated_args = tool.args_model.model_validate(kwargs)
            return tool.run(validated_args)
        return _handler

    tool_handlers = {
        "code_read": _make_handler(read_tool),
        "code_write": _make_handler(write_tool),
        "code_edit": _make_handler(edit_tool),
        "code_search": _make_handler(search_tool),
        "run_terminal": _make_handler(terminal_tool),
        "list_dir": _make_handler(list_dir_tool),
        "git_status": _make_handler(git_status_tool),
        "git_diff": _make_handler(git_diff_tool),
        "git_log": _make_handler(git_log_tool),
        "git_commit": _make_handler(git_commit_tool),
        "repo_map": _make_handler(repo_map_tool),
    }

    # Coba muat metadata dari SKILL.md jika folder skills tersedia
    loader = SkillLoader()
    base_skills_dir = Path(skills_dir).resolve() if skills_dir else None

    for skill_name, handler_fn in tool_handlers.items():
        loaded_skill: Skill | None = None
        if base_skills_dir and (base_skills_dir / skill_name / "SKILL.md").exists():
            try:
                loaded_skill = loader.load_skill_from_path(base_skills_dir / skill_name)
            except Exception as e:
                log.warning("Gagal memuat SKILL.md untuk %s: %s", skill_name, e)

        if loaded_skill is None:
            # Fallback pembuatan skill deklaratif jika folder SKILL.md tidak terbaca
            req_confirm = False
            if skill_name == "run_terminal":
                risk, perms, req_confirm = "high", ["shell:execute"], True
            elif skill_name == "git_commit":
                risk, perms, req_confirm = "high", ["filesystem:write", "shell:execute"], True
            elif skill_name in ("code_read", "code_search", "list_dir", "git_status", "git_diff", "git_log", "repo_map"):
                risk, perms = "low", ["filesystem:read"]
            else:
                risk, perms = "medium", ["filesystem:read", "filesystem:write"]
            loaded_skill = Skill(
                name=skill_name,
                version="1.0.0",
                description=f"Built-in coding skill: {skill_name}",
                risk_level=risk,
                requires_confirmation=req_confirm,
                permissions=perms,
            )

        loaded_skill.handler = handler_fn
        registry.register(loaded_skill)
