import sys
import os
from pathlib import Path
import pytest

# Tambahkan root repo ke sys.path untuk impor ruka_cli
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import ruka_cli


def test_resolve_workspace_default_uses_cwd(monkeypatch, tmp_path):
    """Tanpa argumen eksplisit, resolve_workspace WAJIB mengembalikan CWD saat ini."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("PWD", raising=False)
    resolved = ruka_cli.resolve_workspace()
    assert resolved == tmp_path.resolve()
    assert "RukaProjects" not in str(resolved)


def test_resolve_workspace_explicit_flag(monkeypatch, tmp_path):
    """Bila argumen eksplisit diberikan, resolve_workspace WAJIB mengembalikan path tersebut."""
    target_dir = tmp_path / "custom_project"
    target_dir.mkdir()
    resolved = ruka_cli.resolve_workspace(str(target_dir))
    assert resolved == target_dir.resolve()


def test_resolve_workspace_auto_creates_missing_directory(tmp_path):
    """Bila direktori eksplisit belum ada, otomatis dibuat tanpa crash."""
    non_existent = tmp_path / "new_empty_folder"
    assert not non_existent.exists()
    resolved = ruka_cli.resolve_workspace(str(non_existent))
    assert resolved.exists()
    assert resolved.is_dir()
    assert resolved == non_existent.resolve()


def test_main_parses_workspace_flag(monkeypatch, tmp_path):
    """Flag -w dan --workspace harus terurai rapi dari sys.argv tanpa bocor ke argumen lain."""
    custom_ws = tmp_path / "sandbox_alpha"
    custom_ws.mkdir()

    captured_ws = {}

    def mock_ensure_brain(workspace=None):
        captured_ws["workspace"] = workspace
        # Return dummy tuple untuk skip loop REPL/Chat
        return None

    monkeypatch.setattr(ruka_cli, "ensure_brain_running", mock_ensure_brain)

    # Test dengan -w
    monkeypatch.setattr(sys, "argv", ["ruka", "-w", str(custom_ws), "review", "test.py"])
    with pytest.raises(SystemExit) as exc:
        ruka_cli.main()
    assert exc.value.code == 1
    assert captured_ws["workspace"] == custom_ws.resolve()

    # Test dengan default CWD
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(sys, "argv", ["ruka", "review", "test.py"])
    with pytest.raises(SystemExit) as exc:
        ruka_cli.main()
    assert exc.value.code == 1
    assert captured_ws["workspace"] == tmp_path.resolve()
