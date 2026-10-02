# -*- coding: utf-8 -*-
"""Self-Correction Loop & Manager (Phase 2).
Menangani umpan balik perbaikan kode mandiri saat CodeEvaluator mendeteksi
kegagalan sintaks atau eksekusi terminal, dengan batas maksimum percobaan
dan format instruksi perbaikan yang terstruktur dan deterministik.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from src.agent.evaluator import EvaluationResult

log = logging.getLogger("ruka.agent.self_correction")


@dataclass
class CorrectionAttempt:
    attempt: int
    tool_name: str
    tool_args: dict[str, Any]
    eval_result: EvaluationResult
    instruction: str


class SelfCorrectionManager:
    """Pengelola siklus perbaikan mandiri (Self-Correction Loop)."""

    def __init__(self, max_corrections: int = 3):
        self.max_corrections = max_corrections
        self.history: list[CorrectionAttempt] = []
        self.attempts: int = 0

    def should_correct(self, eval_result: EvaluationResult) -> bool:
        """Menentukan apakah siklus perbaikan mandiri harus dipicu."""
        if eval_result.passed:
            return False
        return self.attempts < self.max_corrections

    def build_correction_prompt(
        self,
        tool_name: str,
        tool_args: dict[str, Any],
        eval_result: EvaluationResult,
    ) -> str:
        """Menyusun prompt arahan perbaikan deterministik untuk model."""
        self.attempts += 1
        attempt_num = self.attempts

        err_lines = "\n".join(f"  • {e}" for e in eval_result.errors) if eval_result.errors else "  • (Tidak ada rincian tambahan)"
        sug_lines = "\n".join(f"  • {s}" for s in eval_result.suggestions) if eval_result.suggestions else ""

        prompt = (
            f"[EVALUASI KODE GAGAL — SIKLUS PERBAIKAN DIRI #{attempt_num}/{self.max_corrections}]\n"
            f"Operasi pada tool '{tool_name}' terdeteksi mengalami masalah integritas:\n"
            f"Pesan: {eval_result.message}\n"
            f"Rincian Error:\n{err_lines}\n"
        )
        if sug_lines:
            prompt += f"Petunjuk Koreksi:\n{sug_lines}\n"

        prompt += (
            "Young Lord menghendaki kode yang presisi dan sempurna. "
            "Segera telaah kembali baris yang bermasalah, gunakan tool yang relevan (seperti read_file lalu edit_file) "
            "untuk memperbaiki kesalahan ini sekarang juga."
        )

        record = CorrectionAttempt(
            attempt=attempt_num,
            tool_name=tool_name,
            tool_args=tool_args,
            eval_result=eval_result,
            instruction=prompt,
        )
        self.history.append(record)
        log.warning(
            "self-correction dipicu: attempt=%d/%d tool=%s",
            attempt_num,
            self.max_corrections,
            tool_name,
        )
        return prompt

    def reset(self) -> None:
        """Mereset hitungan percobaan setelah keberhasilan tercapai."""
        self.attempts = 0

    @property
    def has_exhausted(self) -> bool:
        """Apakah batas perbaikan telah terlampaui."""
        return self.attempts >= self.max_corrections
