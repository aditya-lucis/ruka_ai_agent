# -*- coding: utf-8 -*-
"""Unit & Integration Tests for Git Tools and RepoMap (Fase 2: Coding Depth)."""
import json
import os
import subprocess
from pathlib import Path

import pytest
from src.gateway.skills.coding_bridge import register_builtin_coding_skills
from src.gateway.skills.registry import SkillRegistry
from src.gateway.skills.runtime import SkillsRuntime
from src.gateway.permissions import PermissionManager
from src.ruka_cognition.agentic import (
    READ_ONLY_SKILLS,
    execute_plan,
    make_simple_plan,
    format_results_context,
)
from src.tools.coding import PathJail
from src.tools.git import (
    GitCommitArgs,
    GitCommitTool,
    GitDiffArgs,
    GitDiffTool,
    GitLogArgs,
    GitLogTool,
    GitStatusArgs,
    GitStatusTool,
)
from src.tools.project_map import RepoMapArgs, RepoMapTool
from src.tools.base import ToolError


def _init_git_repo(path: Path) -> None:
    """Helper untuk menginisialisasi repo git lokal di tmp_path untuk pengujian."""
    subprocess.run(["git", "init"], cwd=str(path), check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "ruka@trendamis.local"], cwd=str(path), check=True)
    subprocess.run(["git", "config", "user.name", "Ruka"], cwd=str(path), check=True)


class TestGitTools:
    def test_git_status_and_commit_cycle(self, tmp_path: Path):
        _init_git_repo(tmp_path)
        jail = PathJail(tmp_path)
        status_tool = GitStatusTool(jail=jail)
        commit_tool = GitCommitTool(jail=jail)
        log_tool = GitLogTool(jail=jail)

        # 1. Status awal (kosong)
        res = status_tool.run(GitStatusArgs())
        assert res["is_clean"] is True
        assert res["untracked"] == []

        # 2. Buat file baru
        test_file = tmp_path / "hello.py"
        test_file.write_text("print('hello world')\n", encoding="utf-8")

        res = status_tool.run(GitStatusArgs())
        assert res["is_clean"] is False
        assert "hello.py" in res["untracked"]

        # 3. Commit file baru dengan GitCommitTool
        commit_res = commit_tool.run(GitCommitArgs(message="feat: initial commit", files=["hello.py"]))
        assert commit_res["commit_hash"] != ""
        assert "feat: initial commit" in commit_res["message"]

        # 4. Status setelah commit harus clean
        res = status_tool.run(GitStatusArgs())
        assert res["is_clean"] is True

        # 5. Git Log menampilkan commit tersebut
        log_res = log_tool.run(GitLogArgs(max_count=5))
        assert log_res["total_fetched"] == 1
        assert "feat: initial commit" in log_res["commits"][0]["message"]

    def test_git_diff(self, tmp_path: Path):
        _init_git_repo(tmp_path)
        jail = PathJail(tmp_path)
        diff_tool = GitDiffTool(jail=jail)
        commit_tool = GitCommitTool(jail=jail)

        # Buat file awal dan commit
        f = tmp_path / "calc.py"
        f.write_text("def add(a, b):\n    return a + b\n", encoding="utf-8")
        commit_tool.run(GitCommitArgs(message="initial calc", files=["calc.py"]))

        # Modifikasi file
        f.write_text("def add(a, b):\n    return a + b + 0\n", encoding="utf-8")

        # Cek unstaged diff
        diff_res = diff_tool.run(GitDiffArgs(path="calc.py"))
        assert "+    return a + b + 0" in diff_res["diff"]

        # Stage file
        subprocess.run(["git", "add", "calc.py"], cwd=str(tmp_path), check=True)

        # Unstaged diff sekarang kosong, staged diff ada
        unstaged_res = diff_tool.run(GitDiffArgs(path="calc.py", staged=False))
        assert unstaged_res["diff"] == ""
        staged_res = diff_tool.run(GitDiffArgs(path="calc.py", staged=True))
        assert "+    return a + b + 0" in staged_res["diff"]

    def test_git_commit_empty_message_raises_error(self, tmp_path: Path):
        _init_git_repo(tmp_path)
        jail = PathJail(tmp_path)
        commit_tool = GitCommitTool(jail=jail)
        with pytest.raises(ToolError, match="tidak boleh kosong"):
            commit_tool.run(GitCommitArgs(message="   "))


class TestRepoMapTool:
    def test_repo_map_detection_and_tree(self, tmp_path: Path):
        jail = PathJail(tmp_path)
        repo_tool = RepoMapTool(jail=jail)

        # Buat dummy project structure
        (tmp_path / "package.json").write_text(
            json.dumps({"name": "test-app", "version": "1.0.0", "dependencies": {"express": "^4.0.0"}}),
            encoding="utf-8",
        )
        (tmp_path / "pyproject.toml").write_text("[project]\nname = 'test-py'\n", encoding="utf-8")

        src_dir = tmp_path / "src"
        src_dir.mkdir()
        (src_dir / "index.ts").write_text("console.log('hi');\n", encoding="utf-8")
        (src_dir / "main.py").write_text("print('hi')\n", encoding="utf-8")

        # Buat folder yang seharusnya diabaikan
        node_modules = tmp_path / "node_modules"
        node_modules.mkdir()
        (node_modules / "dummy.js").write_text("// dummy", encoding="utf-8")

        res = repo_tool.run(RepoMapArgs(path=".", max_depth=2))

        assert res["project_name"] == tmp_path.name
        assert "nodejs" in res["manifests"]
        assert "python" in res["manifests"]
        assert res["manifests"]["nodejs"]["name"] == "test-app"
        assert res["total_files"] >= 4
        # Pastikan node_modules tidak ada di pohon
        assert "node_modules" not in res["tree"]
        assert "src/" in res["tree"]
        assert ".py" in res["top_extensions"]
        assert ".ts" in res["top_extensions"]
        assert "# Repository Map:" in res["summary"]


class TestSkillsRuntimeIntegration:
    def test_coding_bridge_registers_git_and_repo_map(self, tmp_path: Path):
        _init_git_repo(tmp_path)
        registry = SkillRegistry()
        jail = PathJail(tmp_path)
        register_builtin_coding_skills(registry, workspace_root=tmp_path, jail=jail)

        # Periksa seluruh skill terdaftar
        for skill_name in ["git_status", "git_diff", "git_log", "git_commit", "repo_map"]:
            assert registry.get(skill_name) is not None, f"Skill {skill_name} tidak ditemukan di registry"

        # Cek atribut keamanan
        git_commit_skill = registry.get("git_commit")
        assert git_commit_skill.risk_level == "high"
        assert git_commit_skill.requires_confirmation is True

        git_status_skill = registry.get("git_status")
        assert git_status_skill.risk_level == "low"
        assert git_status_skill.requires_confirmation is False

        repo_map_skill = registry.get("repo_map")
        assert repo_map_skill.risk_level == "low"
        assert repo_map_skill.requires_confirmation is False

    def test_git_commit_requires_confirmation_flow(self, tmp_path: Path):
        _init_git_repo(tmp_path)
        registry = SkillRegistry()
        jail = PathJail(tmp_path)
        register_builtin_coding_skills(registry, workspace_root=tmp_path, jail=jail)

        perms = PermissionManager(workspace_root=tmp_path)
        runtime = SkillsRuntime(registry=registry, permission_manager=perms)

        # Buat file
        (tmp_path / "note.txt").write_text("my notes", encoding="utf-8")

        # 1. Eksekusi git_commit tanpa konfirmasi -> HARUS DITOLAK
        res_denied = runtime.execute(
            skill_name="git_commit",
            args={"message": "add note", "files": ["note.txt"]},
            confirm_granted=False,
        )
        assert res_denied.success is False
        assert "konfirmasi" in res_denied.error.lower()

        # 2. Eksekusi git_commit dengan konfirmasi -> HARUS BERHASIL
        res_ok = runtime.execute(
            skill_name="git_commit",
            args={"message": "add note", "files": ["note.txt"]},
            confirm_granted=True,
        )
        assert res_ok.success is True
        assert res_ok.data["commit_hash"] != ""


class TestAgenticPlannerWithGitAndRepoMap:
    def test_make_simple_plan_plans_git_status(self):
        plan = make_simple_plan("tolong cek git status repositori ini", available_skills=["git_status", "run_terminal"])
        assert len(plan) == 1
        assert plan[0].skill == "git_status"
        # run_terminal harus di-suppress agar tidak dobel eksekusi
        assert not any(s.skill == "run_terminal" for s in plan)

    def test_make_simple_plan_plans_git_diff(self):
        plan = make_simple_plan("periksa git diff berkas main.py", available_skills=["git_diff", "code_read"])
        assert any(s.skill == "git_diff" and s.args.get("path") == "main.py" for s in plan)

    def test_make_simple_plan_plans_git_diff_staged(self):
        plan = make_simple_plan("lihat git diff --staged", available_skills=["git_diff"])
        assert len(plan) == 1
        assert plan[0].skill == "git_diff"
        assert plan[0].args.get("staged") is True

    def test_make_simple_plan_plans_git_log(self):
        plan = make_simple_plan("tampilkan 5 commit terakhir di git log", available_skills=["git_log"])
        assert len(plan) == 1
        assert plan[0].skill == "git_log"
        assert plan[0].args.get("max_count") == 5

    def test_make_simple_plan_plans_git_commit(self):
        plan = make_simple_plan('git commit -m "fix: resolve memory leak"', available_skills=["git_commit", "run_terminal"])
        assert len(plan) == 1
        assert plan[0].skill == "git_commit"
        assert plan[0].args["message"] == "fix: resolve memory leak"
        assert not any(s.skill == "run_terminal" for s in plan)

    def test_make_simple_plan_plans_repo_map(self):
        plan = make_simple_plan("analisis arsitektur proyek dan struktur repositori ini", available_skills=["repo_map", "list_dir"])
        assert any(s.skill == "repo_map" for s in plan)

    def test_read_only_skills_contains_git_read_and_repo_map(self):
        assert "git_status" in READ_ONLY_SKILLS
        assert "git_diff" in READ_ONLY_SKILLS
        assert "git_log" in READ_ONLY_SKILLS
        assert "repo_map" in READ_ONLY_SKILLS
        # git_commit MUST NOT be read-only
        assert "git_commit" not in READ_ONLY_SKILLS

    def test_format_results_context_renders_repo_map_and_diff(self):
        from src.ruka_cognition.agentic import StepResult

        diff_res = StepResult(
            skill="git_diff",
            args={"path": "calc.py"},
            success=True,
            data={"diff": "+1 line added", "target": "calc.py", "staged": False},
        )
        repo_res = StepResult(
            skill="repo_map",
            args={"path": "."},
            success=True,
            data={"summary": "# Repository Map: test-app\n- Files: 10"},
        )
        formatted = format_results_context([diff_res, repo_res])
        assert "+1 line added" in formatted
        assert "# Repository Map: test-app" in formatted
