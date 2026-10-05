# -*- coding: utf-8 -*-
"""Crimson Heart V3 Models & Dataclasses (FR-HE).

Kontrak dataclass beku untuk orkestrasi Crimson Heart V3:
- 7 Ventrikel peran
- EditProposal 5-field (file_path, anchor_signature, new_content, reason, test_cmd)
- ReviewVerdict 4 segel veto (test_passed, coverage_ge_85, style_clean, security_clean)
- DAGPlan & PlanStep (2-6 langkah asiklik)
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Tuple, Optional


class VentricleRole(str, Enum):
    PLANNER = "planner"
    RESEARCHER = "researcher"
    CODER = "coder"
    REVIEWER = "reviewer"
    DEVOPS = "devops"
    ERP = "erp"
    BROWSER = "browser"


class SealStatus(str, Enum):
    SEALED = "sealed"
    VETOED = "vetoed"


@dataclass(frozen=True)
class PlanStep:
    step_id: str
    ventricle: VentricleRole
    description: str
    dependencies: tuple[str, ...] = field(default_factory=tuple)
    estimated_tokens: int = 1000
    status: str = "pending"  # pending, running, completed, failed


@dataclass(frozen=True)
class DAGPlan:
    task_id: str
    objective: str
    steps: tuple[PlanStep, ...]

    def __post_init__(self) -> None:
        if len(self.steps) < 2 or len(self.steps) > 6:
            raise ValueError(f"Rencana tugas DAG harus berisi 2 sampai 6 langkah, menerima {len(self.steps)}")
        # Cek dependensi valid
        step_ids = {s.step_id for s in self.steps}
        for s in self.steps:
            for dep in s.dependencies:
                if dep not in step_ids:
                    raise ValueError(f"Dependensi '{dep}' tidak ditemukan di dalam langkah DAG")

        # Deteksi siklus penuh (DFS cycle detection)
        adj: dict[str, list[str]] = {s.step_id: list(s.dependencies) for s in self.steps}
        # State: 0 = unvisited, 1 = visiting, 2 = visited
        state: dict[str, int] = {s.step_id: 0 for s in self.steps}

        def has_cycle(u: str) -> bool:
            state[u] = 1
            for v in adj.get(u, []):
                if state[v] == 1:
                    return True
                if state[v] == 0 and has_cycle(v):
                    return True
            state[u] = 2
            return False

        for s in self.steps:
            if state[s.step_id] == 0:
                if has_cycle(s.step_id):
                    raise ValueError(f"Siklus terdeteksi pada dependensi langkah '{s.step_id}'!")


@dataclass(frozen=True)
class EditProposal:
    """Proposal modifikasi kode ber-anchor (FR-HE-05)."""
    file_path: str
    anchor_signature: str
    new_content: str
    reason: str
    test_cmd: str


@dataclass(frozen=True)
class ReviewVerdict:
    """Hasil peninjauan kode 4 segel veto (FR-HE-06)."""
    test_passed: bool
    coverage_percent: float
    style_clean: bool
    security_clean: bool
    feedback: str = ""

    @property
    def passed(self) -> bool:
        return (
            self.test_passed
            and (self.coverage_percent >= 85.0)
            and self.style_clean
            and self.security_clean
        )

    @property
    def seal_status(self) -> SealStatus:
        return SealStatus.SEALED if self.passed else SealStatus.VETOED
