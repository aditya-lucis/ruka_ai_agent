# -*- coding: utf-8 -*-
"""Unit tests for RUKA Coding Tools Phase 1 & Path Jail."""
import os
import pytest
from pathlib import Path

from src.tools.base import ToolError
from src.tools.registry import ToolRegistry
from src.tools.coding import (
    PathJail,
    detect_binary,
    ReadFileTool,
    ReadFileArgs,
    ReadFilesTool,
    ReadFilesArgs,
    EditFileTool,
    EditFileArgs,
    WriteFileTool,
    WriteFileArgs,
    RunTerminalTool,
    RunTerminalArgs,
    ListDirTool,
    ListDirArgs,
    GrepTool,
    GrepArgs,
    GlobTool,
    GlobArgs,
    register_coding_tools,
)


@pytest.fixture
def workspace(tmp_path: Path) -> Path:
    ws = tmp_path / "workspace"
    ws.mkdir()
    return ws


@pytest.fixture
def jail(workspace: Path) -> PathJail:
    return PathJail(base=workspace)


# ============================================================
# 1. PathJail Tests
# ============================================================
def test_path_jail_confinement(workspace: Path, jail: PathJail):
    # Valid relative path
    subfile = workspace / "sub" / "file.txt"
    subfile.parent.mkdir()
    subfile.write_text("hello", encoding="utf-8")

    assert jail.confine("sub/file.txt") == subfile.resolve()
    assert jail.confine("sub\\file.txt") == subfile.resolve()
    assert jail.confine(str(subfile)) == subfile.resolve()

    # Traversal escape rejected
    with pytest.raises(ToolError, match="di luar kurung kerja"):
        jail.confine("../outside.txt")

    with pytest.raises(ToolError, match="di luar kurung kerja"):
        jail.confine("..\\outside.txt")

    # Empty path rejected
    with pytest.raises(ToolError, match="tidak boleh kosong"):
        jail.confine("")


def test_path_jail_absolute_outside(jail: PathJail):
    outside = "C:\\Windows\\System32" if os.name == "nt" else "/etc/passwd"
    with pytest.raises(ToolError, match="di luar kurung kerja"):
        jail.confine(outside)


# ============================================================
# 2. ReadFileTool Tests
# ============================================================
def test_read_file_tool(workspace: Path, jail: PathJail):
    tool = ReadFileTool(jail=jail)
    target = workspace / "doc.txt"
    target.write_text("Line 1\nLine 2\nLine 3\nLine 4\nLine 5\n", encoding="utf-8")

    # Full read
    res = tool.run(ReadFileArgs(path="doc.txt"))
    assert "Line 1" in res["content"]
    assert res["total_lines"] == 5

    # Partial slice (lines 2 to 4)
    slice_res = tool.run(ReadFileArgs(path="doc.txt", start_line=2, end_line=4))
    assert slice_res["content"] == "Line 2\nLine 3\nLine 4\n"

    # Non-existent file
    with pytest.raises(ToolError, match="tidak ditemukan"):
        tool.run(ReadFileArgs(path="missing.txt"))

    # Directory instead of file
    with pytest.raises(ToolError, match="Bukan file"):
        tool.run(ReadFileArgs(path="."))


def test_read_file_binary_detected(workspace: Path, jail: PathJail):
    tool = ReadFileTool(jail=jail)
    bin_file = workspace / "test.bin"
    bin_file.write_bytes(b"\x00\x01\x02\x03\x04")

    assert detect_binary(bin_file) is True
    with pytest.raises(ToolError, match="File biner terdeteksi"):
        tool.run(ReadFileArgs(path="test.bin"))


# ============================================================
# 3. ReadFilesTool Tests
# ============================================================
def test_read_files_tool(workspace: Path, jail: PathJail):
    tool = ReadFilesTool(jail=jail)
    f1 = workspace / "a.txt"
    f2 = workspace / "b.txt"
    f1.write_text("AAAA", encoding="utf-8")
    f2.write_text("BBBB", encoding="utf-8")

    res = tool.run(ReadFilesArgs(paths=["a.txt", "b.txt", "nonexistent.txt"]))
    assert len(res["files"]) == 3
    assert res["files"][0]["content"] == "AAAA"
    assert res["files"][1]["content"] == "BBBB"
    assert "error" in res["files"][2]
    assert res["total_chars"] == 8

    # Truncation test
    res_trunc = tool.run(ReadFilesArgs(paths=["a.txt", "b.txt"], max_total_chars=6))
    assert res_trunc["total_chars"] == 6
    assert res_trunc["files"][1]["truncated"] is True
    assert res_trunc["files"][1]["content"] == "BB"


# ============================================================
# 4. EditFileTool Tests
# ============================================================
def test_edit_file_tool(workspace: Path, jail: PathJail):
    tool = EditFileTool(jail=jail)
    f = workspace / "code.py"
    f.write_text("def hello():\n    return 'old'\n", encoding="utf-8")

    # Success single replace
    res = tool.run(EditFileArgs(path="code.py", old_string="'old'", new_string="'new'"))
    assert res["status"] == "ok"
    assert res["replacements"] == 1
    assert "return 'new'" in f.read_text(encoding="utf-8")

    # Missing string error
    with pytest.raises(ToolError, match="old_string tidak ditemukan"):
        tool.run(EditFileArgs(path="code.py", old_string="missing_str", new_string="x"))

    # Multiple occurrences error without replace_all
    f.write_text("foo bar foo baz", encoding="utf-8")
    with pytest.raises(ToolError, match="kemunculan old_string"):
        tool.run(EditFileArgs(path="code.py", old_string="foo", new_string="qux", replace_all=False))

    # Multiple occurrences with replace_all=True
    res_all = tool.run(EditFileArgs(path="code.py", old_string="foo", new_string="qux", replace_all=True))
    assert res_all["replacements"] == 2
    assert f.read_text(encoding="utf-8") == "qux bar qux baz"


# ============================================================
# 5. WriteFileTool Tests
# ============================================================
def test_write_file_tool(workspace: Path, jail: PathJail):
    tool = WriteFileTool(jail=jail)

    # Write new file with subdirectories
    res = tool.run(WriteFileArgs(path="nested/dir/new.txt", content="created by ruka"))
    assert res["status"] == "written"
    assert (workspace / "nested" / "dir" / "new.txt").read_text(encoding="utf-8") == "created by ruka"

    # create_if_not_exists=False on missing file
    with pytest.raises(ToolError, match="create_if_not_exists=False"):
        tool.run(WriteFileArgs(path="not_exists.txt", content="x", create_if_not_exists=False))


# ============================================================
# 6. RunTerminalTool Tests
# ============================================================
def test_run_terminal_tool(workspace: Path, jail: PathJail):
    tool = RunTerminalTool(jail=jail)

    # Simple echo
    res = tool.run(RunTerminalArgs(command="echo Marquis Ruka", working_directory=None))
    assert res["exit_code"] == 0
    assert "Marquis Ruka" in res["stdout"]

    # Dangerous command blocked without confirmation
    with pytest.raises(ToolError, match="Perintah berbahaya"):
        tool.run(RunTerminalArgs(command="rm -rf /some/dir", require_confirmation=False))

    with pytest.raises(ToolError, match="Perintah berbahaya"):
        tool.run(RunTerminalArgs(command="git push origin main --force", require_confirmation=False))

    with pytest.raises(ToolError, match="Perintah berbahaya"):
        tool.run(RunTerminalArgs(command="del /f /q *.*", require_confirmation=False))

    # Dangerous command passes safety check if confirmed
    # (echo simulates safe test of confirmed flow)
    res_conf = tool.run(RunTerminalArgs(command="echo dangerous --force", require_confirmation=True))
    assert res_conf["exit_code"] == 0

    # Outside working directory blocked by PathJail
    with pytest.raises(ToolError, match="di luar kurung kerja"):
        tool.run(RunTerminalArgs(command="echo test", working_directory="../outside"))


# ============================================================
# 7. ListDirTool Tests
# ============================================================
def test_list_dir_tool(workspace: Path, jail: PathJail):
    tool = ListDirTool(jail=jail)
    (workspace / "dir_a").mkdir()
    (workspace / "file_1.txt").write_text("123", encoding="utf-8")
    (workspace / "file_2.py").write_text("print()", encoding="utf-8")

    res = tool.run(ListDirArgs(path="."))
    names = [e["name"] for e in res["entries"]]
    assert "dir_a" in names
    assert "file_1.txt" in names
    assert "file_2.py" in names


# ============================================================
# 8. GrepTool Tests
# ============================================================
def test_grep_tool(workspace: Path, jail: PathJail):
    tool = GrepTool(jail=jail)
    (workspace / "src").mkdir()
    (workspace / "src" / "alpha.py").write_text("def ruka_vampire():\n    return 'nobility'\n", encoding="utf-8")
    (workspace / "src" / "beta.txt").write_text("Ruka Vampire Marquis\n", encoding="utf-8")

    # Case-insensitive grep
    res = tool.run(GrepArgs(pattern="ruka_vampire", path="src"))
    assert len(res["matches"]) == 1
    assert res["matches"][0]["line"] == 1
    assert "ruka_vampire" in res["matches"][0]["content"]

    # Filter with glob
    res_glob = tool.run(GrepArgs(pattern="Vampire", path="src", glob="*.txt"))
    assert len(res_glob["matches"]) == 1
    assert res_glob["matches"][0]["file"].endswith("beta.txt")


# ============================================================
# 9. GlobTool Tests
# ============================================================
def test_glob_tool(workspace: Path, jail: PathJail):
    tool = GlobTool(jail=jail)
    (workspace / "pkg").mkdir()
    (workspace / "pkg" / "mod1.py").write_text("x = 1", encoding="utf-8")
    (workspace / "pkg" / "mod2.py").write_text("y = 2", encoding="utf-8")
    (workspace / "pkg" / "readme.md").write_text("# Doc", encoding="utf-8")

    res = tool.run(GlobArgs(pattern="**/*.py", path="."))
    assert res["total_matches"] == 2
    assert any("mod1.py" in m for m in res["matches"])
    assert any("mod2.py" in m for m in res["matches"])


# ============================================================
# 10. ToolRegistry Integration Tests
# ============================================================
def test_register_coding_tools_and_execute(workspace: Path, jail: PathJail):
    registry = ToolRegistry()
    registered = register_coding_tools(registry, jail=jail)

    assert len(registered) == 8
    declarations = registry.declarations()
    assert len(declarations) == 8
    tool_names = {d["name"] for d in declarations}
    expected = {
        "read_file", "read_files", "edit_file", "write_file",
        "run_terminal", "list_dir", "grep", "glob"
    }
    assert expected.issubset(tool_names)

    # Test execution through registry with write_file
    res = registry.execute("write_file", {"path": "created.txt", "content": "Ruka Registry Test"}, granted=set())
    assert "result" in res
    assert res["result"]["status"] == "written"

    # Test permission check on run_terminal
    # without permission
    denied = registry.execute("run_terminal", {"command": "echo test"}, granted=set())
    assert "error" in denied
    assert "butuh izin" in denied["error"]

    # with permission
    allowed = registry.execute("run_terminal", {"command": "echo success"}, granted={"run_terminal"})
    assert "result" in allowed
    assert allowed["result"]["exit_code"] == 0
