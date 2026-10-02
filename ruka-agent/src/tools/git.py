# -*- coding: utf-8 -*-
"""Git Tools: Git Status, Git Diff, & Git Log untuk Ruka Coding Agent (Phase 3).
Semua tool mematuhi Path Jail, keamanan sandbox, dan kontrak BaseTool.
"""
from __future__ import annotations

import logging
import re
import subprocess
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field
from src.tools.base import BaseTool, ToolError
from src.tools.coding import PathJail, get_default_jail
from src.tools.registry import ToolRegistry

log = logging.getLogger("ruka.tools.git")


# ============================================================
# 1. git_status
# ============================================================
class GitStatusArgs(BaseModel):
    path: str = Field(default=".", description="Direktori target git status (default: workspace root)")


class GitStatusTool(BaseTool):
    model_config = ConfigDict(arbitrary_types_allowed=True)
    name: str = "git_status"
    description: str = (
        "Memeriksa status git working tree: berkas yang diubah (unstaged), "
        "sudah ditambahkan (staged), dan belum terlacak (untracked)."
    )
    args_model: type[BaseModel] = GitStatusArgs
    timeout_s: float = 10.0
    jail: PathJail | None = None

    def _get_jail(self) -> PathJail:
        return self.jail or get_default_jail()

    def run(self, args: GitStatusArgs) -> dict[str, Any]:
        jail = self._get_jail()
        cwd = jail.confine(args.path)
        if not cwd.is_dir():
            cwd = cwd.parent

        # 1. Dapatkan nama branch
        branch_proc = subprocess.run(
            ["git", "branch", "--show-current"],
            cwd=str(cwd),
            capture_output=True,
            text=True,
        )
        branch = branch_proc.stdout.strip() or "HEAD (detached)"

        # 2. Status porcelain
        proc = subprocess.run(
            ["git", "status", "--porcelain=v1", "-uall"],
            cwd=str(cwd),
            capture_output=True,
            text=True,
        )
        if proc.returncode != 0:
            raise ToolError(f"Gagal menjalankan git status: {proc.stderr.strip() or 'Bukan repositori git'}")

        staged: list[dict[str, str]] = []
        unstaged: list[dict[str, str]] = []
        untracked: list[str] = []

        lines = proc.stdout.splitlines()
        for line in lines:
            if len(line) < 3:
                continue
            x = line[0]
            y = line[1]
            file_name = line[3:].strip()

            if x == "?" and y == "?":
                untracked.append(file_name)
            else:
                if x in ("M", "A", "D", "R", "C"):
                    staged.append({"file": file_name, "status": x})
                if y in ("M", "D"):
                    unstaged.append({"file": file_name, "status": y})

        is_clean = len(staged) == 0 and len(unstaged) == 0 and len(untracked) == 0

        summary = (
            f"Branch: {branch} | "
            f"Staged: {len(staged)}, Unstaged: {len(unstaged)}, Untracked: {len(untracked)}"
        )
        if is_clean:
            summary += " (Working tree clean)"

        return {
            "branch": branch,
            "staged": staged,
            "unstaged": unstaged,
            "untracked": untracked,
            "is_clean": is_clean,
            "summary": summary,
        }


# ============================================================
# 2. git_diff
# ============================================================
class GitDiffArgs(BaseModel):
    path: str | None = Field(default=None, description="Path berkas spesifik untuk melihat diff")
    staged: bool = Field(default=False, description="Set True untuk melihat diff dari perubahan yang telah di-stage")
    commit: str | None = Field(default=None, description="Hash commit atau range (misal HEAD~1) untuk dibandingkan")


class GitDiffTool(BaseTool):
    model_config = ConfigDict(arbitrary_types_allowed=True)
    name: str = "git_diff"
    description: str = (
        "Melihat perbedaan perubahan kode (git diff). "
        "Bisa melihat perubahan working directory, perubahan staged, atau komparasi commit."
    )
    args_model: type[BaseModel] = GitDiffArgs
    timeout_s: float = 15.0
    jail: PathJail | None = None

    def _get_jail(self) -> PathJail:
        return self.jail or get_default_jail()

    def run(self, args: GitDiffArgs) -> dict[str, Any]:
        jail = self._get_jail()
        cmd = ["git", "diff"]

        if args.staged:
            cmd.append("--staged")

        if args.commit:
            # Sanitasi commit arg
            if not re.match(r"^[a-zA-Z0-9_\-\.\^~]+$", args.commit):
                raise ToolError(f"Identifier commit tidak valid: {args.commit}")
            cmd.append(args.commit)

        target_file = None
        if args.path:
            p = jail.confine(args.path)
            cmd.extend(["--", str(p)])
            target_file = str(p)

        proc = subprocess.run(
            cmd,
            cwd=str(jail.base),
            capture_output=True,
            text=True,
        )
        if proc.returncode != 0:
            raise ToolError(f"Gagal menjalankan git diff: {proc.stderr.strip()}")

        diff_text = proc.stdout
        max_chars = 15000
        truncated = False
        if len(diff_text) > max_chars:
            diff_text = diff_text[:max_chars] + f"\n\n... [Diff terpotong karena melebihi {max_chars} karakter] ..."
            truncated = True

        files_changed = len(re.findall(r"^diff --git ", proc.stdout, re.MULTILINE))

        return {
            "diff": diff_text,
            "files_changed": files_changed,
            "truncated": truncated,
            "target": target_file or "workspace",
        }


# ============================================================
# 3. git_log
# ============================================================
class GitLogArgs(BaseModel):
    max_entries: int = Field(default=10, ge=1, le=50, description="Jumlah commit terakhir yang ingin dilihat")
    path: str | None = Field(default=None, description="Filter log untuk berkas atau direktori tertentu")
    oneline: bool = Field(default=True, description="Format satu baris ringkas per commit")


class GitLogTool(BaseTool):
    model_config = ConfigDict(arbitrary_types_allowed=True)
    name: str = "git_log"
    description: str = "Melihat riwayat commit terakhir pada repositori git."
    args_model: type[BaseModel] = GitLogArgs
    timeout_s: float = 10.0
    jail: PathJail | None = None

    def _get_jail(self) -> PathJail:
        return self.jail or get_default_jail()

    def run(self, args: GitLogArgs) -> dict[str, Any]:
        jail = self._get_jail()
        fmt = "%h|%an|%ad|%s"
        cmd = ["git", "log", f"-n{args.max_entries}", f"--date=short", f"--pretty=format:{fmt}"]

        if args.path:
            p = jail.confine(args.path)
            cmd.extend(["--", str(p)])

        proc = subprocess.run(
            cmd,
            cwd=str(jail.base),
            capture_output=True,
            text=True,
        )
        if proc.returncode != 0:
            raise ToolError(f"Gagal membaca git log: {proc.stderr.strip() or 'Belum ada commit'}")

        commits: list[dict[str, str]] = []
        for line in proc.stdout.splitlines():
            parts = line.split("|", 3)
            if len(parts) == 4:
                commits.append({
                    "hash": parts[0],
                    "author": parts[1],
                    "date": parts[2],
                    "message": parts[3],
                })

        return {
            "commits": commits,
            "total_fetched": len(commits),
        }


# ============================================================
# Registrasi Tool Git
# ============================================================
def register_git_tools(registry: ToolRegistry, jail: PathJail | None = None) -> list[BaseTool]:
    """Mendaftarkan seluruh tool git Phase 3 ke dalam ToolRegistry."""
    tools: list[BaseTool] = [
        GitStatusTool(jail=jail),
        GitDiffTool(jail=jail),
        GitLogTool(jail=jail),
    ]
    for t in tools:
        registry.register(t)
    return tools
