# -*- coding: utf-8 -*-
"""Unit tests for Phase 3 — Pengalaman Pengguna & Git Tools:
GitStatusTool, GitDiffTool, GitLogTool, PlanTransparency, and CLI formatting.
"""
from pathlib import Path
import subprocess
import pytest

from src.tools.coding import PathJail
from src.tools.git import GitStatusTool, GitDiffTool, GitLogTool, register_git_tools
from src.tools.registry import ToolRegistry
from src.agent.plan_transparency import PlanTransparency, StepStatus
from src.domain.models import TaskPlan, PlanStep


@pytest.fixture
def git_repo(tmp_path: Path) -> tuple[Path, PathJail]:
    """Menyiapkan repositori git lokal dummy di folder sementara."""
    ws = tmp_path / "repo"
    ws.mkdir()
    subprocess.run(["git", "init"], cwd=str(ws), capture_output=True, check=True)
    subprocess.run(["git", "config", "user.name", "Ruka Tester"], cwd=str(ws), capture_output=True, check=True)
    subprocess.run(["git", "config", "user.email", "ruka@trendamis.local"], cwd=str(ws), capture_output=True, check=True)

    # Initial commit
    init_file = ws / "README.md"
    init_file.write_text("# Ruka Repo\n", encoding="utf-8")
    subprocess.run(["git", "add", "README.md"], cwd=str(ws), capture_output=True, check=True)
    subprocess.run(["git", "commit", "-m", "Initial commit"], cwd=str(ws), capture_output=True, check=True)

    jail = PathJail(base=ws)
    return ws, jail


# ============================================================
# 1. Git Tools Tests
# ============================================================
def test_git_status_tool(git_repo):
    ws, jail = git_repo
    tool = GitStatusTool(jail=jail)

    # Clean working tree
    clean_res = tool.run(tool.args_model())
    assert clean_res["is_clean"] is True
    assert "clean" in clean_res["summary"].lower()

    # Create new file (untracked)
    new_f = ws / "feature.py"
    new_f.write_text("print('hello')\n", encoding="utf-8")

    status_untracked = tool.run(tool.args_model())
    assert status_untracked["is_clean"] is False
    assert "feature.py" in status_untracked["untracked"]

    # Stage the file
    subprocess.run(["git", "add", "feature.py"], cwd=str(ws), capture_output=True, check=True)
    status_staged = tool.run(tool.args_model())
    assert any(s["file"] == "feature.py" for s in status_staged["staged"])


def test_git_diff_tool(git_repo):
    ws, jail = git_repo
    tool = GitDiffTool(jail=jail)

    # Clean diff
    res_clean = tool.run(tool.args_model())
    assert res_clean["diff"] == ""

    # Modify file
    (ws / "README.md").write_text("# Ruka Repo\nAdded new line\n", encoding="utf-8")

    res_modified = tool.run(tool.args_model())
    assert "+Added new line" in res_modified["diff"]
    assert res_modified["files_changed"] >= 1


def test_git_log_tool(git_repo):
    ws, jail = git_repo
    tool = GitLogTool(jail=jail)

    res = tool.run(tool.args_model(max_entries=5))
    assert res["total_fetched"] >= 1
    assert res["commits"][0]["message"] == "Initial commit"
    assert len(res["commits"][0]["hash"]) > 0


def test_register_git_tools(git_repo):
    _, jail = git_repo
    reg = ToolRegistry()
    tools = register_git_tools(reg, jail=jail)
    assert len(tools) == 4

    names = {d["name"] for d in reg.declarations()}
    assert {"git_status", "git_diff", "git_log", "git_commit"}.issubset(names)


# ============================================================
# 2. Plan Transparency Tests
# ============================================================
def test_plan_transparency_announcement():
    plan = TaskPlan(
        goal="Perbaiki race condition di autentikasi",
        steps=[
            PlanStep(step_id=1, description="Analisis berkas auth.py", requires_tool="read_file"),
            PlanStep(step_id=2, description="Sisipkan lock mutex pada token refresh", requires_tool="edit_file"),
            PlanStep(step_id=3, description="Jalankan unit test pengujian", requires_tool="run_terminal"),
        ],
        notes="Gunakan async with self._lock",
    )
    pt = PlanTransparency(plan)

    announcement = pt.format_plan_announcement()
    assert "Young Lord" in announcement
    assert "auth.py" in announcement
    assert "1. Analisis berkas auth.py" in announcement
    assert "2. Sisipkan lock mutex" in announcement
    assert "3. Jalankan unit test" in announcement


def test_plan_transparency_progress_updates():
    plan = TaskPlan(
        goal="Refactor modul database",
        steps=[
            PlanStep(step_id=1, description="Backup sqlite"),
            PlanStep(step_id=2, description="Migrasi schema"),
        ],
    )
    pt = PlanTransparency(plan)

    # Initial states
    assert pt.states[0].status == StepStatus.PENDING
    assert pt.states[1].status == StepStatus.PENDING

    # Mark step 1 running then completed
    pt.mark_step_running(1)
    assert pt.states[0].status == StepStatus.RUNNING

    pt.mark_step_completed(1, summary="Backup sukses 1.2MB", duration_s=0.4)
    assert pt.states[0].status == StepStatus.COMPLETED
    assert pt.states[0].result_summary == "Backup sukses 1.2MB"

    # Mark step 2 failed
    pt.mark_step_failed(2, error="Constraint violation")
    assert pt.states[1].status == StepStatus.FAILED

    # Render progress
    md = pt.render_progress_markdown()
    assert "Status Kemajuan Eksekusi Rencana:" in md
    assert "Backup sukses 1.2MB" in md

    cli_text = pt.render_progress_cli(use_color=False)
    assert "Rencana Kerja Marquis Ruka" in cli_text
    assert "[✓]" in cli_text
    assert "[✕]" in cli_text

    # Final report with failure
    report = pt.format_final_report()
    assert "terdapat kendala pada Langkah 2" in report
