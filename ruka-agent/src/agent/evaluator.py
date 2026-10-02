# -*- coding: utf-8 -*-
"""CodeEvaluator: Evaluasi sintaks dan eksekusi kode otomatis (Phase 2).
Mendeteksi error sintaksis Python/JSON, delimiter yang tidak seimbang,
serta menganalisis output terminal / traceback secara deterministik.
"""
from __future__ import annotations

import ast
import json
import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

log = logging.getLogger("ruka.agent.evaluator")


@dataclass
class EvaluationResult:
    passed: bool
    severity: str  # "ok" | "warning" | "error"
    message: str
    errors: list[str] = field(default_factory=list)
    suggestions: list[str] = field(default_factory=list)
    details: dict[str, Any] = field(default_factory=dict)


class CodeEvaluator:
    """Evaluator kode sederhana untuk Python, JSON, dan eksekusi terminal."""

    TRACEBACK_PATTERN = re.compile(r"Traceback \(most recent call last\):", re.IGNORECASE)
    EXCEPTION_PATTERN = re.compile(r"([A-Za-z_][A-Za-z0-9_]*Error|[A-Za-z_][A-Za-z0-9_]*Exception):\s*(.*)")
    PYTEST_FAILURE_PATTERN = re.compile(r"FAILED\s+([^\s]+)", re.IGNORECASE)
    SYNTAX_ERROR_PATTERN = re.compile(r"SyntaxError:\s*(.*)", re.IGNORECASE)

    def evaluate_file(self, path: str | Path, content: str | None = None) -> EvaluationResult:
        """Mengevaluasi integritas sintaksis file lokal."""
        p = Path(path)
        if content is None:
            if not p.exists() or not p.is_file():
                return EvaluationResult(
                    passed=False,
                    severity="error",
                    message=f"Berkas tidak ditemukan: {p}",
                    errors=[f"File not found: {p}"],
                    suggestions=["Pastikan path berkas sudah benar."],
                )
            try:
                content = p.read_text(encoding="utf-8", errors="replace")
            except Exception as e:
                return EvaluationResult(
                    passed=False,
                    severity="error",
                    message=f"Gagal membaca berkas {p}: {e}",
                    errors=[str(e)],
                    suggestions=["Periksa izin berkas atau encoding."],
                )

        suffix = p.suffix.lower()

        # 1. Evaluasi Sintaks Python via AST
        if suffix in (".py", ".pyw"):
            return self._evaluate_python_syntax(content, str(p))

        # 2. Evaluasi JSON via json.loads
        elif suffix == ".json":
            return self._evaluate_json_syntax(content, str(p))

        # 3. Evaluasi Keseimbangan Delimiter (JS, TS, CSS, dsb)
        elif suffix in (".js", ".ts", ".jsx", ".tsx", ".css", ".html"):
            return self._evaluate_delimiters(content, str(p))

        return EvaluationResult(
            passed=True,
            severity="ok",
            message=f"Format berkas {suffix} tidak memerlukan evaluasi sintaks khusus.",
        )

    def _evaluate_python_syntax(self, code: str, file_path: str) -> EvaluationResult:
        try:
            ast.parse(code, filename=file_path)
            return EvaluationResult(
                passed=True,
                severity="ok",
                message=f"Sintaks Python pada {file_path} valid.",
            )
        except SyntaxError as e:
            line = e.lineno or 0
            col = e.offset or 0
            error_line = (e.text or "").strip()
            msg = f"SyntaxError pada baris {line}, kolom {col}: {e.msg}"
            errors = [msg]
            if error_line:
                errors.append(f"Baris bermasalah: {error_line}")
            suggestions = [
                f"Periksa penulisan sintaks di sekitar baris {line}.",
                "Pastikan penutupan kurung, indentasi, atau tanda titik dua (:) sudah tepat.",
            ]
            return EvaluationResult(
                passed=False,
                severity="error",
                message=msg,
                errors=errors,
                suggestions=suggestions,
                details={"lineno": line, "offset": col, "error_line": error_line},
            )

    def _evaluate_json_syntax(self, content: str, file_path: str) -> EvaluationResult:
        try:
            json.loads(content)
            return EvaluationResult(
                passed=True,
                severity="ok",
                message=f"Sintaks JSON pada {file_path} valid.",
            )
        except json.JSONDecodeError as e:
            msg = f"JSONDecodeError pada baris {e.lineno}, kolom {e.colno}: {e.msg}"
            return EvaluationResult(
                passed=False,
                severity="error",
                message=msg,
                errors=[msg],
                suggestions=[
                    f"Periksa koma berlebih (trailing comma) atau tanda kutip di baris {e.lineno}."
                ],
                details={"lineno": e.lineno, "colno": e.colno},
            )

    def _evaluate_delimiters(self, content: str, file_path: str) -> EvaluationResult:
        stack: list[tuple[str, int]] = []
        pairs = {")": "(", "]": "[", "}": "{"}
        opens = set(pairs.values())
        closes = set(pairs.keys())

        cleaned = re.sub(r"/\*.*?\*/", "", content, flags=re.DOTALL)
        cleaned = re.sub(r"//.*", "", cleaned)
        cleaned = re.sub(r"\"(?:\\.|[^\"\\])*\"", "\"\"", cleaned)
        cleaned = re.sub(r"'(?:\\.|[^'\\])*'", "''", cleaned)

        for line_num, line in enumerate(cleaned.splitlines(), 1):
            for char in line:
                if char in opens:
                    stack.append((char, line_num))
                elif char in closes:
                    if not stack:
                        return EvaluationResult(
                            passed=False,
                            severity="error",
                            message=f"Karakter penutup '{char}' tanpa pembuka di baris {line_num}",
                            errors=[f"Unmatched closing delimiter '{char}' at line {line_num}"],
                            suggestions=["Periksa kembali keseimbangan tanda kurung kurawal/siku."],
                        )
                    top, open_line = stack.pop()
                    if pairs[char] != top:
                        return EvaluationResult(
                            passed=False,
                            severity="error",
                            message=f"Karakter '{char}' di baris {line_num} tidak cocok dengan '{top}' dari baris {open_line}",
                            errors=[f"Mismatched delimiter '{char}' with '{top}'"],
                            suggestions=["Pastikan tanda kurung ditutup dengan pasangan yang sesuai."],
                        )

        if stack:
            unclosed, open_line = stack[-1]
            return EvaluationResult(
                passed=False,
                severity="error",
                message=f"Terdapat karakter pembuka '{unclosed}' dari baris {open_line} yang belum ditutup.",
                errors=[f"Unclosed delimiter '{unclosed}' opened at line {open_line}"],
                suggestions=["Tutup semua kurung kurawal/siku yang masih terbuka."],
            )

        return EvaluationResult(
            passed=True,
            severity="ok",
            message=f"Keseimbangan delimiter pada {file_path} valid.",
        )

    def evaluate_terminal_output(
        self, command: str, exit_code: int, stdout: str, stderr: str
    ) -> EvaluationResult:
        """Mengevaluasi hasil eksekusi terminal / pengujian."""
        combined = f"{stdout}\n{stderr}"
        errors: list[str] = []
        suggestions: list[str] = []

        if self.TRACEBACK_PATTERN.search(combined):
            exc_match = self.EXCEPTION_PATTERN.findall(combined)
            if exc_match:
                exc_type, exc_detail = exc_match[-1]
                errors.append(f"{exc_type}: {exc_detail.strip()}")
                suggestions.append(f"Periksa penanganan {exc_type} yang muncul pada stack trace.")
            else:
                errors.append("Traceback eksekusi terdeteksi dalam keluaran terminal.")

        pytest_fails = self.PYTEST_FAILURE_PATTERN.findall(combined)
        if pytest_fails:
            errors.append(f"Test gagal: {', '.join(pytest_fails[:5])}")
            suggestions.append("Jalankan kembali test spesifik tersebut untuk menganalisis kegagalan.")

        if exit_code != 0:
            if not errors:
                err_summary = (
                    stderr.strip().splitlines()[-1]
                    if stderr.strip()
                    else f"Process exited with code {exit_code}"
                )
                errors.append(err_summary)
            return EvaluationResult(
                passed=False,
                severity="error",
                message=f"Perintah '{command}' gagal (exit code {exit_code}).",
                errors=errors,
                suggestions=suggestions or ["Periksa argumen perintah terminal atau dependensi yang hilang."],
                details={"exit_code": exit_code, "command": command},
            )

        if errors:
            return EvaluationResult(
                passed=False,
                severity="warning",
                message=f"Perintah '{command}' selesai dengan exit code 0 namun mendeteksi anomali error.",
                errors=errors,
                suggestions=suggestions,
            )

        return EvaluationResult(
            passed=True,
            severity="ok",
            message=f"Eksekusi perintah '{command}' berhasil dengan exit code 0.",
        )

    def evaluate_tool(
        self, tool_name: str, args: dict[str, Any], result: dict[str, Any]
    ) -> EvaluationResult:
        """Mengevaluasi hasil pemanggilan tool secara otomatis."""
        if "error" in result:
            return EvaluationResult(
                passed=False,
                severity="error",
                message=f"Tool {tool_name} melaporkan error: {result['error']}",
                errors=[result["error"]],
                suggestions=["Periksa parameter pemanggilan tool."],
            )

        if tool_name in ("edit_file", "write_file"):
            path = args.get("path")
            if path:
                return self.evaluate_file(path)

        elif tool_name == "run_terminal":
            cmd = args.get("command", "")
            code = result.get("exit_code", 0)
            stdout = result.get("stdout", "")
            stderr = result.get("stderr", "")
            return self.evaluate_terminal_output(cmd, code, stdout, stderr)

        return EvaluationResult(passed=True, severity="ok", message=f"Tool {tool_name} sukses.")
