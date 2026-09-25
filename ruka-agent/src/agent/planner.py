# -*- coding: utf-8 -*-
"""Planning 2.0 – DAG, kegagalan parsial, checkpoint, resume.
Evolusi dari planner Vol I: list langkah -> graf dependensi;
plan_runner lama tetap hidup untuk rencana linear (back compat).
"""
from __future__ import annotations
import json
import logging
import sqlite3
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

# Back-compat imports from Vol I
from src.llm.gemini_client import GeminiClient
from src.llm.structured import ask_structured
from src.domain.models import TaskPlan, PlanStep as LinearPlanStep

log = logging.getLogger("ruka.planner")


# ============================================================================
# Planning 2.0: DAG, Partial Failure, Checkpoint & Resume (Volume II)
# ============================================================================

class StepStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    DONE = "done"
    FAILED = "failed"
    BLOCKED = "blocked"      # dependensi gagal – bukan salahnya


@dataclass
class PlanStep:
    step_id: str
    description: str
    depends_on: list[str] = field(default_factory=list)
    allowed_tools: list[str] | None = None      # least privilege per langkah
    status: StepStatus = StepStatus.PENDING
    result: str | None = None
    attempts: int = 0


@dataclass
class PlanRecord:
    plan_id: str
    goal: str
    steps: dict[str, PlanStep] = field(default_factory=dict)

    # -- validasi DAG --
    def validate(self) -> None:
        for sid, step in self.steps.items():
            for dep in step.depends_on:
                if dep not in self.steps:
                    raise ValueError(f"{sid} bergantung pada {dep} yang tak ada")
        # deteksi siklus: DFS warna
        WHITE, GRAY, BLACK = 0, 1, 2
        color = {sid: WHITE for sid in self.steps}

        def visit(n: str) -> None:
            if color[n] == GRAY:
                raise ValueError(f"siklus terdeteksi di {n}")
            if color[n] == BLACK:
                return
            color[n] = GRAY
            for dep in self.steps[n].depends_on:
                visit(dep)
            color[n] = BLACK

        for sid in self.steps:
            if color[sid] == WHITE:
                visit(sid)

    def ready_steps(self) -> list[PlanStep]:
        """Langkah yang seluruh dependensinya DONE."""
        out = []
        for step in self.steps.values():
            if step.status is not StepStatus.PENDING:
                continue
            deps = [self.steps[d] for d in step.depends_on]
            if all(d.status is StepStatus.DONE for d in deps):
                out.append(step)
        return out

    def mark_failed(self, step_id: str, reason: str) -> list[str]:
        """Gagal satu langkah -> BLOCK dependen secara transitif.
        Kembalikan daftar yang ikut terblok."""
        step = self.steps[step_id]
        step.status = StepStatus.FAILED
        step.result = reason
        blocked: list[str] = []
        changed = True
        while changed:                          # propagasi transitif
            changed = False
            for s in self.steps.values():
                if s.status is not StepStatus.PENDING:
                    continue
                if any(self.steps[d].status in (StepStatus.FAILED, StepStatus.BLOCKED)
                       for d in s.depends_on):
                    s.status = StepStatus.BLOCKED
                    blocked.append(s.step_id)
                    changed = True
        return blocked

    def is_terminal(self) -> bool:
        return all(s.status in (StepStatus.DONE, StepStatus.FAILED, StepStatus.BLOCKED)
                   for s in self.steps.values())

    # -- persistensi: checkpoint per node --
    def to_json(self) -> str:
        return json.dumps({
            "plan_id": self.plan_id,
            "goal": self.goal,
            "steps": {
                k: {
                    "step_id": v.step_id,
                    "description": v.description,
                    "depends_on": v.depends_on,
                    "allowed_tools": v.allowed_tools,
                    "status": v.status.value,
                    "result": v.result,
                    "attempts": v.attempts,
                }
                for k, v in self.steps.items()
            }
        }, indent=2)

    @classmethod
    def from_json(cls, raw: str) -> "PlanRecord":
        data = json.loads(raw)
        plan = cls(plan_id=data["plan_id"], goal=data["goal"])
        for sid, s in data["steps"].items():
            plan.steps[sid] = PlanStep(
                step_id=s["step_id"],
                description=s["description"],
                depends_on=s["depends_on"],
                allowed_tools=s.get("allowed_tools"),
                status=StepStatus(s["status"]),
                result=s.get("result"),
                attempts=s.get("attempts", 0),
            )
        return plan


class PlanStore:
    """Checkpoint persisten – rencana hidup lintas proses."""
    def __init__(self, db_path: Path | str) -> None:
        self._conn = sqlite3.connect(str(db_path))
        self._conn.execute(
            "CREATE TABLE IF NOT EXISTS plans ("
            "plan_id TEXT PRIMARY KEY, goal TEXT, plan_json TEXT, "
            "updated_at TEXT DEFAULT CURRENT_TIMESTAMP)"
        )
        self._conn.commit()

    def save(self, plan: PlanRecord) -> None:
        self._conn.execute(
            "INSERT OR REPLACE INTO plans (plan_id, goal, plan_json) "
            "VALUES (?, ?, ?)",
            (plan.plan_id, plan.goal, plan.to_json())
        )
        self._conn.commit()

    def load(self, plan_id: str) -> PlanRecord | None:
        row = self._conn.execute(
            "SELECT plan_json FROM plans WHERE plan_id = ?",
            (plan_id,)
        ).fetchone()
        return PlanRecord.from_json(row[0]) if row else None

    def latest_unfinished(self) -> PlanRecord | None:
        row = self._conn.execute(
            "SELECT plan_json FROM plans ORDER BY updated_at DESC"
        ).fetchone()
        if not row:
            return None
        plan = PlanRecord.from_json(row[0])
        return None if plan.is_terminal() else plan


def resume(plan: PlanRecord, executor: Any, store: Any) -> PlanRecord:
    """Lanjutkan dari titik terakhir – DONE tidak diulang."""
    while not plan.is_terminal():
        ready = plan.ready_steps()
        if not ready:
            break                      # terminal atau macet
        for step in ready:
            step.status = StepStatus.RUNNING
            step.attempts += 1
            store.save(plan)           # checkpoint SEBELUM eksekusi
            outcome = executor.execute(step)
            step.result = outcome
            step.status = (StepStatus.DONE if outcome and not
                           outcome.startswith("ERROR")
                           else StepStatus.FAILED)
            if step.status is StepStatus.FAILED:
                plan.mark_failed(step.step_id, outcome)
            store.save(plan)           # checkpoint SETELAH eksekusi
    return plan


# ============================================================================
# Volume I: Linear PlannerAgent (Backward Compatibility)
# ============================================================================

class PlannerAgent:
    """Dekomposisi tugas menjadi plan terstruktur yang dapat dieksekusi."""
    def __init__(self, client: GeminiClient, *, max_replans: int = 2):
        self.client = client
        self.max_replans = max_replans

    def plan(self, goal: str, *, context: str = "",
             available_tools: list[str] | None = None) -> TaskPlan:
        tools = available_tools or []
        prompt = (
            f"Tujuan: {goal}\n"
            f"{f'Konteks: {context}' if context else ''}\n"
            "Susun rencana langkah demi langkah. Gunakan hanya "
            f"tool ini: {', '.join(tools) or '(tanpa tool)'}. "
            "Setiap langkah satu aksi konkret."
        )
        
        plan = ask_structured(
            self.client, prompt, TaskPlan,
            system_instruction="Anda perencana tugas yang pragmatis "
                               "dan hemat langkah.",
        )
        log.info("plan: %d langkah untuk '%s'", len(plan.steps), goal)
        return self._validate(plan, available_tools=tools)

    def replan(self, plan: TaskPlan, failed_step: LinearPlanStep,
               observation: str) -> TaskPlan:
        """Revisi sisa rencana setelah kegagalan — bukan mulai nol."""
        remaining = [s for s in plan.steps if s.step_id > failed_step.step_id]
        prompt = (
            f"Rencana awal: {plan.goal}\n"
            f"Langkah {failed_step.step_id} GAGAL: {failed_step.description}\n"
            f"Observasi: {observation}\n"
            f"Sisa langkah: {remaining}\n"
            "Susun rencana BARU untuk sisa tujuan, menangani "
            "penyebab kegagalan."
        )
        return ask_structured(self.client, prompt, TaskPlan)

    def _validate(self, plan: TaskPlan, *, available_tools) -> TaskPlan:
        """Domain rules: tool yang dipakai harus terdaftar."""
        if available_tools:
            for s in plan.steps:
                if s.requires_tool and s.requires_tool not in available_tools:
                    s.requires_tool = None  # netralkan tool karangan
        return plan
