# -*- coding: utf-8 -*-
"""Test -> Fix -> Verify Loop untuk Ruka Agent (Phase 3).

Menyediakan siklus otomasi cerdas:
1. Menjalankan test suite (Test).
2. Menganalisis kegagalan secara terstruktur (traceback, nama test, file, baris) (Analyze).
3. Merumuskan dan menerapkan perbaikan terarah (Fix).
4. Memverifikasi sintaksis dengan CodeEvaluator dan mengeksekusi ulang test (Verify).
5. Mematuhi PathJail, Zero-Trust, dan audit transparansi Young Lord.
"""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

from src.agent.evaluator import CodeEvaluator, EvaluationResult
from src.gateway.skills.runtime import SkillsRuntime
from src.tools.coding import PathJail

log = logging.getLogger("ruka.agent.test_fix_verify")


@dataclass
class TestFailure:
    """Informasi terstruktur dari satu kegagalan test."""
    __test__ = False
    test_id: str
    file_path: str | None = None
    line_number: int | None = None
    error_type: str = "UnknownError"
    error_message: str = ""
    traceback: str = ""
    related_files: list[str] = field(default_factory=list)


@dataclass
class TestExecutionResult:
    """Hasil normalisasi dari eksekusi test runner (pytest, npm, jest, dll)."""
    __test__ = False
    passed: bool
    exit_code: int
    total_tests: int = 0
    passed_tests: int = 0
    failed_count: int = 0
    failures: list[TestFailure] = field(default_factory=list)
    raw_stdout: str = ""
    raw_stderr: str = ""


@dataclass
class FixAttempt:
    """Catatan satu iterasi upaya perbaikan kode."""
    __test__ = False
    attempt_number: int
    target_failure: TestFailure
    file_edited: str
    description: str
    syntax_passed: bool
    verify_passed: bool
    output_after: str = ""


@dataclass
class TestFixVerifyOutcome:
    """Hasil akhir dari siklus Test -> Fix -> Verify."""
    __test__ = False
    status: str  # "verified_passed" | "already_passing" | "exhausted_retries" | "confirmation_required" | "cannot_infer_fix"
    initial_result: TestExecutionResult
    final_result: TestExecutionResult | None = None
    attempts: list[FixAttempt] = field(default_factory=list)
    summary: str = ""


class TestOutputParser:
    """Parser deterministik untuk berbagai output test runner."""
    __test__ = False

    # Pytest patterns
    PYTEST_FAIL_LINE = re.compile(r"FAILED\s+([^\s:]+)(?:::([^\s\n]+))?(?:\s+-\s+(.*))?", re.IGNORECASE)
    PYTEST_PASSED_COUNT = re.compile(r"(\d+)\s+passed\b", re.IGNORECASE)
    PYTEST_FAILED_COUNT = re.compile(r"(\d+)\s+failed\b", re.IGNORECASE)
    PYTEST_FILE_LINE = re.compile(r"([A-Za-z0-9_./\\-]+\.py):(\d+):", re.IGNORECASE)
    
    # Generic traceback
    TRACEBACK_FILE_LINE = re.compile(r'File "([^"]+)", line (\d+)', re.IGNORECASE)
    EXCEPTION_LINE = re.compile(r"^([A-Za-z0-9_]+(?:Error|Exception)):\s*(.*)$", re.MULTILINE)
    PY_FILES_IN_TRACEBACK = re.compile(r"([A-Za-z0-9_./\\-]+\.py)\b", re.IGNORECASE)

    @classmethod
    def parse(cls, stdout: str, stderr: str, exit_code: int) -> TestExecutionResult:
        combined = f"{stdout}\n{stderr}".strip()
        failures: list[TestFailure] = []

        # Cari semua berkas .py yang muncul dalam output kegagalan
        all_py_files: list[str] = []
        for pf in cls.PY_FILES_IN_TRACEBACK.finditer(combined):
            fname = Path(pf.group(1)).name
            if fname not in all_py_files:
                all_py_files.append(fname)

        # 1. Parse Pytest FAILED lines
        for match in cls.PYTEST_FAIL_LINE.finditer(combined):
            raw_file_part = match.group(1).replace("\\", "/")
            file_part = raw_file_part
            test_name = match.group(2) or Path(file_part).name
            raw_msg = (match.group(3) or "").strip()
            
            err_type = "AssertionError"
            err_msg = raw_msg
            if raw_msg.startswith("assert "):
                err_type = "AssertionError"
            elif ":" in raw_msg:
                parts = raw_msg.split(":", 1)
                if "error" in parts[0].lower() or "exception" in parts[0].lower():
                    err_type = parts[0].strip()
                    err_msg = parts[1].strip()

            # Cari line number terdekat
            line_no = None
            f_match = cls.PYTEST_FILE_LINE.search(combined)
            if f_match:
                try:
                    line_no = int(f_match.group(2))
                except ValueError:
                    line_no = None

            related = [f for f in all_py_files if f != Path(file_part).name and f != file_part]
            failures.append(
                TestFailure(
                    test_id=f"{file_part}::{test_name}" if test_name != file_part else file_part,
                    file_path=file_part,
                    line_number=line_no,
                    error_type=err_type,
                    error_message=err_msg,
                    traceback=combined[:1000],
                    related_files=related,
                )
            )

        # 2. Jika tidak ada pattern pytest spesifik tapi exit code != 0
        if not failures and exit_code != 0:
            tb_matches = list(cls.TRACEBACK_FILE_LINE.finditer(combined))
            exc_match = cls.EXCEPTION_LINE.search(combined)
            err_type = exc_match.group(1) if exc_match else "ExecutionError"
            err_msg = exc_match.group(2) if exc_match else (stderr.strip() or "Test runner failed")

            target_file = None
            line_no = None
            if tb_matches:
                target_file = Path(tb_matches[-1].group(1)).name
                try:
                    line_no = int(tb_matches[-1].group(2))
                except ValueError:
                    line_no = None

            related = [f for f in all_py_files if f != target_file]
            failures.append(
                TestFailure(
                    test_id="cli_execution_failure",
                    file_path=target_file,
                    line_number=line_no,
                    error_type=err_type,
                    error_message=err_msg.strip(),
                    traceback=combined[:1000],
                    related_files=related,
                )
            )

        passed = (exit_code == 0 and len(failures) == 0)
        
        # Summary counts
        p_match = cls.PYTEST_PASSED_COUNT.search(combined)
        f_match = cls.PYTEST_FAILED_COUNT.search(combined)
        total_p = int(p_match.group(1)) if p_match else 0
        total_f = int(f_match.group(1)) if f_match else len(failures)

        return TestExecutionResult(
            passed=passed,
            exit_code=exit_code,
            total_tests=total_p + total_f,
            passed_tests=total_p,
            failed_count=total_f,
            failures=failures,
            raw_stdout=stdout,
            raw_stderr=stderr,
        )


class TestFixVerifyLoop:
    """Mesin eksekusi otonom Test -> Fix -> Verify."""
    __test__ = False

    def __init__(
        self,
        runtime: SkillsRuntime,
        evaluator: CodeEvaluator | None = None,
        max_retries: int = 3,
        fixer_callback: Callable[[TestFailure, str], tuple[str, str, str] | None] | None = None,
    ) -> None:
        self.runtime = runtime
        self.evaluator = evaluator or CodeEvaluator()
        self.max_retries = max_retries
        self.fixer_callback = fixer_callback

    def _execute_test(
        self, test_cmd: str, confirm_granted: bool, session_id: str
    ) -> tuple[TestExecutionResult, bool]:
        """Jalankan perintah test melalui skill run_terminal."""
        res = self.runtime.execute(
            skill_name="run_terminal",
            args={"command": test_cmd},
            session_id=session_id,
            confirm_granted=confirm_granted,
        )
        if not res.success:
            if "konfirmasi" in (res.error or "").lower():
                # Memerlukan izin
                return TestExecutionResult(passed=False, exit_code=1, failures=[]), True
            return TestExecutionResult(
                passed=False,
                exit_code=1,
                failures=[TestFailure(test_id="run_terminal_error", error_message=res.error or "Error")],
                raw_stderr=res.error or "",
            ), False

        data = res.data or {}
        stdout = data.get("stdout", "")
        stderr = data.get("stderr", "")
        code = data.get("exit_code", 0)
        return TestOutputParser.parse(stdout, stderr, code), False

    def _read_file_content(self, path: str, session_id: str) -> str | None:
        """Baca berkas menggunakan skill code_read."""
        res = self.runtime.execute(
            skill_name="code_read",
            args={"path": path},
            session_id=session_id,
            confirm_granted=True,  # read-only
        )
        if res.success and isinstance(res.data, dict) and "content" in res.data:
            return res.data["content"]
        return None

    def _apply_file_edit(
        self, path: str, old_str: str, new_str: str, session_id: str
    ) -> bool:
        """Edit berkas menggunakan skill code_edit."""
        res = self.runtime.execute(
            skill_name="code_edit",
            args={"path": path, "old_string": old_str, "new_string": new_str},
            session_id=session_id,
            confirm_granted=True,
        )
        return bool(res.success)

    def run(
        self,
        test_command: str = "pytest",
        confirm_granted: bool = False,
        session_id: str = "test-fix-verify",
    ) -> TestFixVerifyOutcome:
        """Menjalankan loop Test -> Fix -> Verify."""
        # 1. TEST PERTAMA
        init_res, needs_confirm = self._execute_test(test_command, confirm_granted, session_id)
        if needs_confirm:
            return TestFixVerifyOutcome(
                status="confirmation_required",
                initial_result=init_res,
                summary="Eksekusi test command membutuhkan konfirmasi tiket dari Young Lord.",
            )

        if init_res.passed:
            return TestFixVerifyOutcome(
                status="already_passing",
                initial_result=init_res,
                summary=f"Semua test ({init_res.passed_tests} test) telah lulus tanpa kegagalan.",
            )

        attempts: list[FixAttempt] = []
        current_res = init_res

        # 2. SIKLUS PERBAIKAN (FIX -> VERIFY)
        for attempt_idx in range(1, self.max_retries + 1):
            if not current_res.failures:
                break

            primary_failure = current_res.failures[0]
            candidate_files: list[str] = []
            if primary_failure.file_path:
                candidate_files.append(primary_failure.file_path)
                bname = Path(primary_failure.file_path).name
                if bname not in candidate_files:
                    candidate_files.append(bname)
            for rf in primary_failure.related_files:
                if rf not in candidate_files:
                    candidate_files.append(rf)

            # Jika file pertama adalah file test, periksa module yang di-import
            if primary_failure.file_path:
                first_content = self._read_file_content(primary_failure.file_path, session_id)
                if first_content:
                    for imp in re.finditer(r"(?:from\s+([A-Za-z0-9_]+)\s+import|import\s+([A-Za-z0-9_]+))", first_content):
                        mod_name = imp.group(1) or imp.group(2)
                        py_name = f"{mod_name}.py"
                        if py_name not in candidate_files:
                            candidate_files.append(py_name)

            if not candidate_files:
                return TestFixVerifyOutcome(
                    status="cannot_infer_fix",
                    initial_result=init_res,
                    final_result=current_res,
                    attempts=attempts,
                    summary=f"Tidak dapat menentukan berkas target dari kegagalan: {primary_failure.error_message}",
                )

            # Cari perbaikan di antara seluruh berkas kandidat
            fix_spec = None
            content = None
            target_path = None
            for c_path in candidate_files:
                c_content = self._read_file_content(c_path, session_id)
                if c_content is not None and self.fixer_callback:
                    spec = self.fixer_callback(primary_failure, c_content)
                    if spec:
                        f_edit, old_c, new_c = spec
                        if old_c in c_content:
                            fix_spec = spec
                            content = c_content
                            target_path = f_edit
                            break
                        # Atau jika fixer callback menghasilkan usulan yang tidak valid secara sintaksis
                        # untuk diuji penolakannya oleh CodeEvaluator
                        elif not self.evaluator.evaluate_file(f_edit, content=c_content.replace(old_c, new_c, 1)).passed:
                            fix_spec = spec
                            content = c_content
                            target_path = f_edit
                            break

            if not fix_spec or not content or not target_path:
                return TestFixVerifyOutcome(
                    status="cannot_infer_fix",
                    initial_result=init_res,
                    final_result=current_res,
                    attempts=attempts,
                    summary=f"Tidak ada hipotesis perbaikan otomatis yang cocok untuk {primary_failure.test_id}.",
                )

            file_to_edit, old_chunk, new_chunk = fix_spec
            
            # Evaluasi sintaks pra-simpan jika memungkinkan
            proposed_content = content.replace(old_chunk, new_chunk, 1)
            eval_res = self.evaluator.evaluate_file(file_to_edit, content=proposed_content)
            if not eval_res.passed:
                attempts.append(
                    FixAttempt(
                        attempt_number=attempt_idx,
                        target_failure=primary_failure,
                        file_edited=file_to_edit,
                        description=f"Hipotesis ditolak karena kesalahan sintaks: {eval_res.message}",
                        syntax_passed=False,
                        verify_passed=False,
                    )
                )
                continue

            # Terapkan perbaikan
            edit_ok = self._apply_file_edit(file_to_edit, old_chunk, new_chunk, session_id)
            if not edit_ok:
                attempts.append(
                    FixAttempt(
                        attempt_number=attempt_idx,
                        target_failure=primary_failure,
                        file_edited=file_to_edit,
                        description="Gagal menerapkan perubahan berkas melalui code_edit.",
                        syntax_passed=True,
                        verify_passed=False,
                    )
                )
                continue

            # 3. VERIFIKASI (VERIFY RE-RUN)
            verify_res, _ = self._execute_test(test_command, confirm_granted=True, session_id=session_id)
            is_verified = verify_res.passed
            attempts.append(
                FixAttempt(
                    attempt_number=attempt_idx,
                    target_failure=primary_failure,
                    file_edited=file_to_edit,
                    description=f"Mengganti '{old_chunk.strip()}' menjadi '{new_chunk.strip()}' di {file_to_edit}",
                    syntax_passed=True,
                    verify_passed=is_verified,
                    output_after=verify_res.raw_stdout[:400],
                )
            )

            current_res = verify_res
            if is_verified:
                summary = (
                    f"Test berhasil diperbaiki dan diverifikasi pada percobaan #{attempt_idx}!\n"
                    f"- Berkas diperbaiki: `{file_to_edit}`\n"
                    f"- Target kegagalan: `{primary_failure.test_id}` ({primary_failure.error_type})\n"
                    f"- Status akhir: Seluruh test lulus (exit code 0)."
                )
                return TestFixVerifyOutcome(
                    status="verified_passed",
                    initial_result=init_res,
                    final_result=verify_res,
                    attempts=attempts,
                    summary=summary,
                )

        # Jika kehabisan batas percobaan
        return TestFixVerifyOutcome(
            status="exhausted_retries",
            initial_result=init_res,
            final_result=current_res,
            attempts=attempts,
            summary=f"Batas percobaan ({self.max_retries}) habis. Masih terdapat {current_res.failed_count} test yang gagal.",
        )
