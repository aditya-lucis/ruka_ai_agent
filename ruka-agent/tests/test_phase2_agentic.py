# -*- coding: utf-8 -*-
"""Unit tests for Phase 2 — Agentic Capability:
CodeEvaluator, Self-Correction Loop, Coding Intent MLP, and Project Memory.
"""
from pathlib import Path
import pytest

from src.agent.evaluator import CodeEvaluator, EvaluationResult
from src.agent.self_correction import SelfCorrectionManager
from src.agent.project_memory import ProjectMemory, ArchitectureDecision
from src.neural.intent import (
    CODING_CLASSES,
    CodingIntentMLP,
    CognitiveMode,
    coding_lexical_features,
    embed_or_fallback,
    route_cognitive_mode,
)
from src.memory.models import MemoryKind


# ============================================================
# 1. CodeEvaluator Tests
# ============================================================
def test_evaluator_python_syntax(tmp_path: Path):
    evaluator = CodeEvaluator()

    # Valid Python code
    good_code = "def add(a: int, b: int) -> int:\n    return a + b\n"
    res_good = evaluator.evaluate_file("good.py", content=good_code)
    assert res_good.passed is True
    assert res_good.severity == "ok"

    # Invalid Python syntax
    bad_code = "def broken(\n    return 42\n"
    res_bad = evaluator.evaluate_file("bad.py", content=bad_code)
    assert res_bad.passed is False
    assert res_bad.severity == "error"
    assert "SyntaxError" in res_bad.message
    assert len(res_bad.suggestions) > 0


def test_evaluator_json_syntax():
    evaluator = CodeEvaluator()

    good_json = '{"name": "ruka", "title": "Marquis", "powers": [1, 2, 3]}'
    assert evaluator.evaluate_file("config.json", content=good_json).passed is True

    bad_json = '{"name": "ruka", "trailing_comma": true,}'
    res_bad = evaluator.evaluate_file("bad.json", content=bad_json)
    assert res_bad.passed is False
    assert "JSONDecodeError" in res_bad.message


def test_evaluator_delimiters():
    evaluator = CodeEvaluator()

    good_ts = "function test() { const arr = [1, 2, (3 + 4)]; }"
    assert evaluator.evaluate_file("app.ts", content=good_ts).passed is True

    bad_ts = "function test() { const arr = [1, 2, (3 + 4); }"
    res_bad = evaluator.evaluate_file("bad.ts", content=bad_ts)
    assert res_bad.passed is False
    assert "Mismatched delimiter" in res_bad.errors[0] or "unclosed" in res_bad.message.lower()


def test_evaluator_terminal_output():
    evaluator = CodeEvaluator()

    # Success terminal
    res_ok = evaluator.evaluate_terminal_output("pytest", 0, "1 passed in 0.05s", "")
    assert res_ok.passed is True

    # Failed terminal with traceback
    traceback_out = """
Traceback (most recent call last):
  File "test.py", line 12, in <module>
    run_calc()
ZeroDivisionError: division by zero
"""
    res_fail = evaluator.evaluate_terminal_output("python test.py", 1, "", traceback_out)
    assert res_fail.passed is False
    assert any("ZeroDivisionError" in err for err in res_fail.errors)
    assert len(res_fail.suggestions) > 0


def test_evaluator_tool_dispatch():
    evaluator = CodeEvaluator()

    # Tool error passthrough
    err_res = evaluator.evaluate_tool("edit_file", {}, {"error": "old_string tidak ditemukan"})
    assert err_res.passed is False
    assert "old_string" in err_res.message


# ============================================================
# 2. SelfCorrectionManager Tests
# ============================================================
def test_self_correction_lifecycle():
    manager = SelfCorrectionManager(max_corrections=3)
    assert manager.attempts == 0
    assert manager.has_exhausted is False

    eval_fail = EvaluationResult(
        passed=False,
        severity="error",
        message="SyntaxError pada baris 5",
        errors=["SyntaxError: invalid syntax"],
        suggestions=["Tutup kurung di baris 5"],
    )

    # First attempt
    assert manager.should_correct(eval_fail) is True
    prompt1 = manager.build_correction_prompt("edit_file", {"path": "main.py"}, eval_fail)
    assert "SIKLUS PERBAIKAN DIRI #1/3" in prompt1
    assert "SyntaxError: invalid syntax" in prompt1
    assert manager.attempts == 1

    # Second attempt
    assert manager.should_correct(eval_fail) is True
    prompt2 = manager.build_correction_prompt("edit_file", {"path": "main.py"}, eval_fail)
    assert "#2/3" in prompt2
    assert manager.attempts == 2

    # Third attempt
    assert manager.should_correct(eval_fail) is True
    prompt3 = manager.build_correction_prompt("edit_file", {"path": "main.py"}, eval_fail)
    assert "#3/3" in prompt3
    assert manager.attempts == 3
    assert manager.has_exhausted is True

    # Fourth attempt should be rejected (exhausted)
    assert manager.should_correct(eval_fail) is False

    # Reset
    manager.reset()
    assert manager.attempts == 0
    assert manager.has_exhausted is False


# ============================================================
# 3. Coding Intent MLP & Routing Tests
# ============================================================
def test_coding_intent_mlp():
    m = CodingIntentMLP(seed=42)
    assert len(m.classes) == 9
    assert m.classes == CODING_CLASSES

    def extract_coding_feats(text: str) -> list[float]:
        return embed_or_fallback(text) + coding_lexical_features(text)

    features = extract_coding_feats("tolong refactor kode di auth.py agar bersih")
    assert len(features) == 64 + 12

    label, prob = m.predict(features)
    assert label in CODING_CLASSES
    assert 0.0 <= prob <= 1.0


def test_cognitive_mode_routing():
    assert route_cognitive_mode("coding_implement") == CognitiveMode.CODING
    assert route_cognitive_mode("coding_debug") == CognitiveMode.CODING
    assert route_cognitive_mode("coding_refactor") == CognitiveMode.CODING
    assert route_cognitive_mode("greeting") == CognitiveMode.COMPANION
    assert route_cognitive_mode("smalltalk") == CognitiveMode.COMPANION
    assert route_cognitive_mode("question") == CognitiveMode.HYBRID
    assert route_cognitive_mode("task_request") == CognitiveMode.HYBRID


def test_coding_lexical_features():
    feats = coding_lexical_features("def test_function(): return 42")
    # Base 6 features + 6 coding features
    assert len(feats) == 12
    # has_code_syntax (index 6) should be 1.0
    assert feats[6] == 1.0


# ============================================================
# 4. ProjectMemory Tests
# ============================================================
def test_project_memory_lifecycle(tmp_path: Path):
    pm = ProjectMemory(project_root=tmp_path)
    pm.add_convention("Gunakan Python 3.10+ type hints")
    pm.add_coding_style("Indentasi 4 spasi, fungsi modular tanpa magic number")
    pm.add_constraint("Jangan pernah mematikan PathJail sandbox")
    pm.add_architecture_decision("Storage", "Gunakan SQLite dengan WAL mode")

    ctx = pm.format_prompt_context()
    assert "=== INGATAN PROYEK (PROJECT MEMORY) ===" in ctx
    assert "Gunakan Python 3.10+ type hints" in ctx
    assert "[DILARANG] Jangan pernah mematikan PathJail" in ctx
    assert "[Storage]: Gunakan SQLite dengan WAL mode" in ctx

    # Test saving to workspace
    saved_file = pm.save_to_workspace(tmp_path)
    assert saved_file.exists()

    # Test loading from workspace
    pm_loaded = ProjectMemory.load_from_workspace(tmp_path)
    assert len(pm_loaded.conventions) == 1
    assert pm_loaded.conventions[0] == "Gunakan Python 3.10+ type hints"
    assert len(pm_loaded.constraints) == 1
    assert len(pm_loaded.architecture_decisions) == 1
    assert pm_loaded.architecture_decisions[0].title == "Storage"

    # Test exporting to MemoryRecord
    records = pm.export_to_memory_records()
    assert len(records) == 2
    assert all(r.kind == MemoryKind.PROJECT for r in records)
