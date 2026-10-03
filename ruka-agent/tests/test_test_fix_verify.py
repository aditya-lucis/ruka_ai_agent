# -*- coding: utf-8 -*-
"""Unit tests for Test -> Fix -> Verify Loop (Fase 3)."""
from pathlib import Path
import sys

import pytest
from src.agent.evaluator import CodeEvaluator
from src.agent.test_fix_verify import (
    FixAttempt,
    TestExecutionResult,
    TestFailure,
    TestFixVerifyLoop,
    TestFixVerifyOutcome,
    TestOutputParser,
)
from src.gateway.permissions import PermissionManager
from src.gateway.skills.coding_bridge import register_builtin_coding_skills
from src.gateway.skills.registry import SkillRegistry
from src.gateway.skills.runtime import SkillsRuntime
from src.tools.coding import PathJail


class TestTestOutputParser:
    def test_parse_pytest_passing(self):
        stdout = "============================= 5 passed in 0.12s ============================="
        res = TestOutputParser.parse(stdout, "", 0)
        assert res.passed is True
        assert res.passed_tests == 5
        assert res.failed_count == 0
        assert len(res.failures) == 0

    def test_parse_pytest_failure(self):
        stdout = (
            "FAILED tests/test_calc.py::test_add - AssertionError: assert 5 == 6\n"
            "tests/test_calc.py:42: in test_add\n"
            "========================= 1 failed, 4 passed in 0.20s ========================="
        )
        res = TestOutputParser.parse(stdout, "", 1)
        assert res.passed is False
        assert res.failed_count == 1
        assert res.passed_tests == 4
        assert len(res.failures) == 1
        f = res.failures[0]
        assert f.test_id == "tests/test_calc.py::test_add"
        assert f.file_path == "tests/test_calc.py"
        assert f.error_type == "AssertionError"
        assert "assert 5 == 6" in f.error_message
        assert f.line_number == 42


class TestTestFixVerifyLoop:
    def _setup_runtime(self, tmp_path: Path) -> SkillsRuntime:
        registry = SkillRegistry()
        jail = PathJail(tmp_path)
        register_builtin_coding_skills(registry, workspace_root=tmp_path, jail=jail)
        perms = PermissionManager(workspace_root=tmp_path)
        return SkillsRuntime(registry=registry, permission_manager=perms)

    def test_already_passing_flow(self, tmp_path: Path):
        runtime = self._setup_runtime(tmp_path)
        
        # Test command yang selalu sukses
        loop = TestFixVerifyLoop(runtime=runtime)
        outcome = loop.run(test_command="python -c \"print('OK')\"", confirm_granted=True)
        assert outcome.status == "already_passing"
        assert "tanpa kegagalan" in outcome.summary

    def test_confirmation_required_flow(self, tmp_path: Path):
        runtime = self._setup_runtime(tmp_path)
        loop = TestFixVerifyLoop(runtime=runtime)
        outcome = loop.run(test_command="pytest", confirm_granted=False)
        assert outcome.status == "confirmation_required"
        assert "konfirmasi" in outcome.summary.lower()

    def test_successful_fix_and_verify(self, tmp_path: Path):
        runtime = self._setup_runtime(tmp_path)

        # Buat file implementasi yang salah (return a - b harusnya a + b)
        calc_file = tmp_path / "calc.py"
        calc_file.write_text("def add(a, b):\n    return a - b\n", encoding="utf-8")

        # Buat file test
        test_file = tmp_path / "test_calc.py"
        test_file.write_text(
            "from calc import add\n"
            "def test_add():\n"
            "    assert add(2, 3) == 5\n",
            encoding="utf-8",
        )

        def simple_fixer(failure: TestFailure, content: str):
            if "return a - b" in content:
                return ("calc.py", "return a - b", "return a + b")
            return None

        evaluator = CodeEvaluator()
        loop = TestFixVerifyLoop(
            runtime=runtime,
            evaluator=evaluator,
            max_retries=2,
            fixer_callback=simple_fixer,
        )

        # Jalankan loop dengan pytest menargetkan test_calc.py di tmp_path
        test_cmd = f'"{sys.executable}" -m pytest {test_file.name} -q -p no:cacheprovider'
        outcome = loop.run(test_command=test_cmd, confirm_granted=True)

        assert outcome.status == "verified_passed"
        assert len(outcome.attempts) == 1
        assert outcome.attempts[0].verify_passed is True
        assert "calc.py" in outcome.summary
        assert "Verified" in outcome.summary or "berhasil diperbaiki" in outcome.summary

        # Pastikan isi file sudah benar-benar diperbaiki di disk
        updated_content = calc_file.read_text(encoding="utf-8")
        assert "return a + b" in updated_content

    def test_syntax_error_in_fix_rejected_by_evaluator(self, tmp_path: Path):
        runtime = self._setup_runtime(tmp_path)

        calc_file = tmp_path / "calc.py"
        calc_file.write_text("def add(a, b):\n    return a - b\n", encoding="utf-8")

        test_file = tmp_path / "test_calc.py"
        test_file.write_text(
            "from calc import add\n"
            "def test_add():\n"
            "    assert add(2, 3) == 5\n",
            encoding="utf-8",
        )

        # Fixer yang menghasilkan sintaks Python tidak valid (missing parenthesis/colon)
        def bad_syntax_fixer(failure: TestFailure, content: str):
            return ("calc.py", "return a - b", "return def bad syntax !!!")

        loop = TestFixVerifyLoop(
            runtime=runtime,
            evaluator=CodeEvaluator(),
            max_retries=1,
            fixer_callback=bad_syntax_fixer,
        )

        test_cmd = f'"{sys.executable}" -m pytest {test_file.name} -q -p no:cacheprovider'
        outcome = loop.run(test_command=test_cmd, confirm_granted=True)

        # Harus ditolak oleh evaluator sintaks, sehingga tidak merusak file di disk
        assert outcome.status == "exhausted_retries"
        assert len(outcome.attempts) == 1
        assert outcome.attempts[0].syntax_passed is False
        assert "sintaks" in outcome.attempts[0].description.lower()
        # File asli tidak boleh rusak
        assert calc_file.read_text(encoding="utf-8") == "def add(a, b):\n    return a - b\n"
