# -*- coding: utf-8 -*-
"""Project / Repository Mapping Tool untuk Ruka Coding Agent (Phase 2).
Menghasilkan pemetaan struktur proyek, deteksi manifest teknologi,
distribusi ekstensi file, dan ringkasan ringkas yang ramah token.
Mematuhi PathJail dan kontrak BaseTool.
"""
from __future__ import annotations

import json
import logging
import os
import subprocess
from collections import Counter
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field
from src.tools.base import BaseTool, ToolError
from src.tools.coding import PathJail, get_default_jail
from src.tools.registry import ToolRegistry

log = logging.getLogger("ruka.tools.project_map")

IGNORED_DIRS = {
    ".git",
    "node_modules",
    "__pycache__",
    ".venv",
    "venv",
    "env",
    ".tox",
    "dist",
    "build",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    ".next",
    ".nuxt",
    "target",
    "bin",
    "obj",
    ".idea",
    ".vscode",
    ".antigravity",
    ".gemini",
}

IGNORED_FILES = {
    ".DS_Store",
    "Thumbs.db",
    "package-lock.json",
    "pnpm-lock.yaml",
    "yarn.lock",
    "poetry.lock",
    "Pipfile.lock",
}


class RepoMapArgs(BaseModel):
    path: str = Field(default=".", description="Direktori target yang akan dipetakan (default: workspace root)")
    max_depth: int = Field(default=2, ge=1, le=5, description="Kedalaman maksimal pohon direktori (1-5, default: 2)")
    include_stats: bool = Field(default=True, description="Sertakan statistik ekstensi berkas dan ringkasan manifest")


class RepoMapTool(BaseTool):
    model_config = ConfigDict(arbitrary_types_allowed=True)
    name: str = "repo_map"
    description: str = (
        "Memetakan arsitektur dan struktur repositori/proyek: deteksi teknologi (manifest), "
        "hierarki folder hingga kedalaman tertentu, statistik ekstensi berkas, dan status git."
    )
    args_model: type[BaseModel] = RepoMapArgs
    timeout_s: float = 10.0
    jail: PathJail | None = None

    def _get_jail(self) -> PathJail:
        return self.jail or get_default_jail()

    def _detect_manifests(self, root: Path) -> dict[str, Any]:
        """Deteksi ekosistem proyek dari berkas konfigurasi/manifest standar."""
        manifests: dict[str, Any] = {}

        # 1. Node.js
        pkg_json = root / "package.json"
        if pkg_json.is_file():
            try:
                data = json.loads(pkg_json.read_text(encoding="utf-8", errors="replace"))
                manifests["nodejs"] = {
                    "name": data.get("name", ""),
                    "version": data.get("version", ""),
                    "scripts": list((data.get("scripts") or {}).keys()),
                    "dependencies_count": len(data.get("dependencies") or {}),
                    "devDependencies_count": len(data.get("devDependencies") or {}),
                }
            except Exception:
                manifests["nodejs"] = {"name": "invalid-json"}

        # 2. Python
        pyproject = root / "pyproject.toml"
        requirements = root / "requirements.txt"
        setup_py = root / "setup.py"
        if pyproject.is_file() or requirements.is_file() or setup_py.is_file():
            py_info: dict[str, Any] = {"found": []}
            if pyproject.is_file():
                py_info["found"].append("pyproject.toml")
            if requirements.is_file():
                py_info["found"].append("requirements.txt")
            if setup_py.is_file():
                py_info["found"].append("setup.py")
            manifests["python"] = py_info

        # 3. Rust
        cargo = root / "Cargo.toml"
        if cargo.is_file():
            manifests["rust"] = {"found": ["Cargo.toml"]}

        # 4. Go
        gomod = root / "go.mod"
        if gomod.is_file():
            manifests["go"] = {"found": ["go.mod"]}

        # 5. Java / Kotlin
        pom = root / "pom.xml"
        gradle = root / "build.gradle"
        gradle_kts = root / "build.gradle.kts"
        if pom.is_file() or gradle.is_file() or gradle_kts.is_file():
            manifests["jvm"] = {"found": [f.name for f in [pom, gradle, gradle_kts] if f.is_file()]}

        return manifests

    def _get_git_info(self, root: Path) -> tuple[str | None, bool | None]:
        """Ambil branch dan status clean/dirty git jika direktori di bawah git repo."""
        try:
            branch_proc = subprocess.run(
                ["git", "branch", "--show-current"],
                cwd=str(root),
                capture_output=True,
                text=True,
                timeout=3.0,
            )
            if branch_proc.returncode != 0:
                return None, None
            branch = branch_proc.stdout.strip() or "HEAD (detached)"

            status_proc = subprocess.run(
                ["git", "status", "--porcelain=v1"],
                cwd=str(root),
                capture_output=True,
                text=True,
                timeout=3.0,
            )
            is_clean = len(status_proc.stdout.strip()) == 0
            return branch, is_clean
        except Exception:
            return None, None

    def _build_tree_and_stats(
        self, root: Path, max_depth: int
    ) -> tuple[str, Counter[str], int, int]:
        """Bangun visualisasi pohon direktori ringkas dan hitung statistik ekstensi berkas."""
        ext_counter: Counter[str] = Counter()
        total_files = 0
        total_dirs = 0
        tree_lines: list[str] = [f"{root.name}/"]

        def _traverse(current_dir: Path, prefix: str, depth: int) -> None:
            nonlocal total_files, total_dirs
            if depth > max_depth:
                return

            try:
                entries = sorted(os.scandir(current_dir), key=lambda e: (not e.is_dir(), e.name.lower()))
            except PermissionError:
                return

            # Filter entries
            filtered = [
                e for e in entries
                if e.name not in IGNORED_DIRS and e.name not in IGNORED_FILES
            ]

            total_entries = len(filtered)
            for i, entry in enumerate(filtered):
                is_last = (i == total_entries - 1)
                connector = "└── " if is_last else "├── "
                sub_prefix = "    " if is_last else "│   "

                if entry.is_dir(follow_symlinks=False):
                    total_dirs += 1
                    tree_lines.append(f"{prefix}{connector}{entry.name}/")
                    _traverse(Path(entry.path), prefix + sub_prefix, depth + 1)
                else:
                    total_files += 1
                    ext = Path(entry.name).suffix.lower() or "(no-ext)"
                    ext_counter[ext] += 1
                    if depth <= max_depth:
                        tree_lines.append(f"{prefix}{connector}{entry.name}")

        _traverse(root, "", 1)
        return "\n".join(tree_lines), ext_counter, total_files, total_dirs

    def run(self, args: RepoMapArgs) -> dict[str, Any]:
        jail = self._get_jail()
        root = jail.confine(args.path)

        if not root.exists():
            raise ToolError(f"Path '{args.path}' tidak ditemukan")
        if not root.is_dir():
            raise ToolError(f"Path '{args.path}' bukan sebuah direktori")

        manifests = self._detect_manifests(root)
        branch, is_clean = self._get_git_info(root)
        tree, ext_counter, total_files, total_dirs = self._build_tree_and_stats(root, args.max_depth)

        # Ringkasan terformat
        summary_lines = [
            f"# Repository Map: `{root.name}`",
            f"- Path: `{root}`",
        ]
        if branch is not None:
            status_text = "Clean" if is_clean else "Modified / Dirty"
            summary_lines.append(f"- Git Branch: `{branch}` ({status_text})")
        
        techs = list(manifests.keys())
        if techs:
            summary_lines.append(f"- Detected Ecosystem: {', '.join(t.capitalize() for t in techs)}")
        
        if args.include_stats:
            summary_lines.append(f"- Total Files: {total_files}, Folders: {total_dirs}")
            top_exts = [f"`{ext}`: {count}" for ext, count in ext_counter.most_common(6)]
            if top_exts:
                summary_lines.append(f"- Top Extensions: {', '.join(top_exts)}")

        summary_lines.append("\n```text\n" + tree + "\n```")
        summary_str = "\n".join(summary_lines)

        return {
            "root": str(root),
            "project_name": root.name,
            "branch": branch,
            "is_clean": is_clean,
            "manifests": manifests,
            "total_files": total_files,
            "total_dirs": total_dirs,
            "top_extensions": dict(ext_counter.most_common(10)),
            "tree": tree,
            "summary": summary_str,
        }


def register_project_map_tools(registry: ToolRegistry, jail: PathJail | None = None) -> None:
    """Registrasi tool repo_map ke registry."""
    registry.register(RepoMapTool(jail=jail))
