# -*- coding: utf-8 -*-
"""Crimson Reflection – self-evaluation 2.0 beranggaran.
Pipeline 6 tahap; verdict ter-typed; koreksi menyusut; hentian
selalu ber-laporan (trace PART 23).
"""
from __future__ import annotations
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Callable, Any
from pydantic import BaseModel, Field


class CheckKind(str, Enum):
    VALIDATION = "validation"
    EVIDENCE = "evidence"
    TOOL_RESULT = "tool_result"
    CONSTRAINT = "constraint"
    QUALITY = "quality"


class Severity(str, Enum):
    PASS = "pass"
    MINOR = "minor"                 # koreksi ringan; tidak wajib
    MAJOR = "major"                 # wajib dikoreksi jika anggaran ada
    FATAL = "fatal"                 # jawaban tidak boleh dikirim


class CheckVerdict(BaseModel):
    kind: CheckKind
    severity: Severity
    problem: str = ""
    fix_hint: str = ""              # arahan koreksi eksplisit


class CorrectionPlan(BaseModel):
    revised_answer: str = Field(description="draft yang diperbaiki")
    applied_fixes: list[str] = Field(default_factory=list)


@dataclass
class ReflectionBudget:
    max_revalidation: int = 2
    max_corrections: int = 2
    seconds: float = 12.0
    corrections_by_kind: dict[str, int] = field(default_factory=dict)


@dataclass
class ReflectionReport:
    final_answer: str
    corrections_used: int
    stages_run: list[str]
    problems_found: list[CheckVerdict]
    stopped_reason: str = "complete"    # complete | budget_corrections | budget_time | budget_stage


class ReflectionLoop:
    """checker: fungsi (draft, kind) -> CheckVerdict;
    corrector: fungsi (draft, problems) -> CorrectionPlan."""
    STAGES = [
        CheckKind.VALIDATION,
        CheckKind.EVIDENCE,
        CheckKind.TOOL_RESULT,
        CheckKind.CONSTRAINT,
        CheckKind.QUALITY,
    ]

    def __init__(self, checker: Any, corrector: Any,
                 budget: ReflectionBudget | None = None) -> None:
        self._checker = checker
        self._corrector = corrector
        self._budget = budget or ReflectionBudget()

    def run(self, draft: str) -> ReflectionReport:
        t0 = time.monotonic()
        corrections = 0
        revalidations = 0
        stages_run: list[str] = []
        problems: list[CheckVerdict] = []
        current = draft
        stopped = "complete"

        while True:
            fatal = None
            stage_problems: list[CheckVerdict] = []
            for kind in self.STAGES:
                if time.monotonic() - t0 > self._budget.seconds:
                    stopped = "budget_time"
                    break
                stages_run.append(kind.value)
                verdict = self._checker(current, kind)
                problems.append(verdict)
                if verdict.severity is Severity.PASS:
                    continue
                stage_problems.append(verdict)
                if verdict.severity is Severity.FATAL:
                    fatal = verdict
                    break

            if stopped == "budget_time":
                break

            if fatal is not None:
                # fatal tanpa anggaran koreksi -> jawaban penolakan jujur
                if corrections >= self._budget.max_corrections:
                    current = ("Saya tidak dapat menghasilkan jawaban yang "
                               "lulus pemeriksaan: " + fatal.problem)
                    stopped = "budget_corrections"
                    break

            if not stage_problems:
                break                                # bersih – selesai

            majorn = [p for p in stage_problems
                      if p.severity in (Severity.MAJOR, Severity.FATAL)]
            only_minor = not majorn
            if only_minor:
                break                                # minor: kirim apa adanya

            if corrections >= self._budget.max_corrections:
                stopped = "budget_corrections"
                break

            kind_key = majorn[0].kind.value
            if self._budget.corrections_by_kind.get(kind_key, 0) >= 1:
                stopped = "budget_stage"            # kegagalan sama kedua kali
                break

            if revalidations >= self._budget.max_revalidation:
                stopped = "budget_corrections"
                break

            plan = self._corrector(current, majorn)
            current = plan.revised_answer
            corrections += 1
            revalidations += 1
            self._budget.corrections_by_kind[kind_key] = (
                self._budget.corrections_by_kind.get(kind_key, 0) + 1)

        return ReflectionReport(
            final_answer=current,
            corrections_used=corrections,
            stages_run=stages_run,
            problems_found=problems,
            stopped_reason=stopped,
        )


def build_reflection_prompt(kind: CheckKind, draft: str, context: str) -> str:
    """Prompt checker terstruktur – verdict Pydantic via response_format."""
    focus = {
        CheckKind.VALIDATION: ("apakah draft memenuhi format dan kontrak "
                              "permintaan?"),
        CheckKind.EVIDENCE: ("apakah tiap klaim faktual didukung kutipan "
                             "bukti yang diberikan?"),
        CheckKind.TOOL_RESULT: ("apakah angka/nama dari tool di draft cocok "
                                "dengan hasil tool pada konteks?"),
        CheckKind.CONSTRAINT: "apakah batasan user (format/bahasa/scope) terpenuhi?",
        CheckKind.QUALITY: "apakah draft jernih, lengkap, dan tidak melantur?",
    }[kind]
    return (f"PERIKSA DRAFT berikut. Fokus: {focus}\n"
            f"Kembalikan verdict JSON: kind, severity "
            f"(pass|minor|major|fatal), problem, fix_hint.\n\n"
            f"DRAFT:\n{draft}\n\nKONTEKS BUKTI:\n{context[:4000]}")
