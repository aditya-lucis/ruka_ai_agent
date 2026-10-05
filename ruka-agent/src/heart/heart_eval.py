# -*- coding: utf-8 -*-
"""Boss 6 Crimson Heart Evaluation Harness — heart_eval (FR-HE, SAD 5.2).

Mengevaluasi 20 tugas rekayasa perangkat lunak mandiri:
- Lantai kelulusan minimal: 85% (17 dari 20 tugas harus lulus)
- Exit code keras: 0 jika lulus, 1 jika gagal
- Menilai: Rencana DAG, 13 Kontrak Darah, Reviewer 4-Segel, Checkpointer SQLite,
  Budget Circuit Breaker, Heart Doctor, dan Matriks Eskalasi.
"""
from __future__ import annotations

import sys
import tempfile
import traceback
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from src.heart.blood import (
    BloodPermission,
    CANONICAL_BLOOD_TOOLS,
    create_canonical_blood_registry,
)
from src.heart.budget import HeartBudget, HeartBudgetExceeded
from src.heart.checkpoint import HeartCheckpointer
from src.heart.doctor import HeartDoctor
from src.heart.matrix import EscalationMatrix
from src.heart.models import (
    DAGPlan,
    EditProposal,
    PlanStep,
    ReviewVerdict,
    SealStatus,
    VentricleRole,
)
from src.heart.supervisor import SupervisorGraph
from src.heart.ventricles import (
    CoderVentricle,
    PlannerVentricle,
    ResearcherVentricle,
    ReviewerVentricle,
)
from src.tools.coding import PathJail, ToolError


@dataclass
class EvalTaskResult:
    task_id: int
    name: str
    passed: bool
    details: str


class HeartEvaluator:
    def __init__(self, workspace_dir: Path | None = None) -> None:
        self.workspace_dir = workspace_dir or Path(tempfile.mkdtemp(prefix="ruka_heart_eval_"))
        self.jail = PathJail(self.workspace_dir)
        self.registry = create_canonical_blood_registry(jail=self.jail)

    def run_all(self) -> list[EvalTaskResult]:
        tasks: list[tuple[str, Callable[[], None]]] = [
            ("Task 01: Read file within PathJail", self._task_01_read_file),
            ("Task 02: Write file within PathJail", self._task_02_write_file),
            ("Task 03: Edit file with anchor replacement", self._task_03_edit_file),
            ("Task 04: Search code regex in files", self._task_04_search_code),
            ("Task 05: Fail-closed PathJail traversal blocked", self._task_05_jail_traversal_blocked),
            ("Task 06: DAG Plan generation acyclic", self._task_06_dag_plan_generation),
            ("Task 07: DAG Plan cyclic dependency rejection", self._task_07_dag_cycle_rejection),
            ("Task 08: Reviewer 4 seals pass", self._task_08_reviewer_4_seals_pass),
            ("Task 09: Reviewer veto on failed tests", self._task_09_reviewer_veto_untested),
            ("Task 10: Reviewer veto on low coverage (<85%)", self._task_10_reviewer_veto_low_coverage),
            ("Task 11: Reviewer veto on OWASP violation", self._task_11_reviewer_veto_security),
            ("Task 12: Checkpoint persistence to SQLite", self._task_12_checkpoint_persistence),
            ("Task 13: Crash recovery and resume from step", self._task_13_crash_recovery_resume),
            ("Task 14: Token budget consumption tracking", self._task_14_token_budget_tracking),
            ("Task 15: Heart budget circuit breaker trip", self._task_15_circuit_breaker_trip),
            ("Task 16: Heart Doctor deadlock detection", self._task_16_doctor_deadlock),
            ("Task 17: Escalation matrix RED requires confirmation", self._task_17_escalation_matrix_red),
            ("Task 18: Escalation matrix GREEN auto-proceeds", self._task_18_escalation_matrix_green),
            ("Task 19: Researcher Iron Rule citation required", self._task_19_researcher_iron_rule),
            ("Task 20: Blood contract rejects unknown tools", self._task_20_blood_contract_rejection),
        ]

        results: list[EvalTaskResult] = []
        for i, (name, fn) in enumerate(tasks, start=1):
            try:
                fn()
                results.append(EvalTaskResult(task_id=i, name=name, passed=True, details="OK"))
            except Exception as e:
                tb = traceback.format_exc()
                results.append(EvalTaskResult(task_id=i, name=name, passed=False, details=f"{e}\n{tb}"))

        return results

    # =========================================================================
    # Task Implementations
    # =========================================================================

    def _task_01_read_file(self) -> None:
        p = self.workspace_dir / "test_read.txt"
        p.write_text("Hello Noctis", encoding="utf-8")
        out = self.registry.execute_tool("code_read", {"path": "test_read.txt"})
        assert "Hello Noctis" in str(out)

    def _task_02_write_file(self) -> None:
        out = self.registry.execute_tool("code_write", {"path": "written.txt", "content": "Crimson Heart"})
        p = self.workspace_dir / "written.txt"
        assert p.exists()
        assert p.read_text(encoding="utf-8") == "Crimson Heart"

    def _task_03_edit_file(self) -> None:
        p = self.workspace_dir / "to_edit.txt"
        p.write_text("Alpha\nBeta\nGamma\n", encoding="utf-8")
        self.registry.execute_tool("code_edit", {
            "path": "to_edit.txt",
            "target": "Beta",
            "replacement": "Delta",
        })
        assert "Delta" in p.read_text(encoding="utf-8")
        assert "Beta" not in p.read_text(encoding="utf-8")

    def _task_04_search_code(self) -> None:
        p = self.workspace_dir / "target.py"
        p.write_text("def find_me_secret_function(): pass\n", encoding="utf-8")
        res = self.registry.execute_tool("code_search", {"query": "find_me_secret"})
        assert "find_me_secret_function" in str(res)

    def _task_05_jail_traversal_blocked(self) -> None:
        try:
            self.registry.execute_tool("code_read", {"path": "../../outside_secret.txt"})
            raise AssertionError("Path traversal harusnya diblokir!")
        except (ToolError, ValueError):
            pass  # Berhasil diblokir

    def _task_06_dag_plan_generation(self) -> None:
        planner = PlannerVentricle()
        plan = planner.create_plan(
            task_id="eval_dag",
            objective="Build Feature",
            steps_data=[
                {"step_id": "s1", "ventricle": "planner", "description": "Analisis"},
                {"step_id": "s2", "ventricle": "coder", "description": "Implementasi", "dependencies": ["s1"]},
                {"step_id": "s3", "ventricle": "reviewer", "description": "Review", "dependencies": ["s2"]},
            ],
        )
        assert len(plan.steps) == 3

    def _task_07_dag_cycle_rejection(self) -> None:
        try:
            DAGPlan(
                task_id="t_cycle",
                objective="Cyclic task",
                steps=(
                    PlanStep("s1", VentricleRole.CODER, "Step 1", dependencies=("s2",)),
                    PlanStep("s2", VentricleRole.REVIEWER, "Step 2", dependencies=("s1",)),
                ),
            )
            raise AssertionError("Siklus harus ditolak!")
        except ValueError:
            pass  # Lulus penolakan

    def _task_08_reviewer_4_seals_pass(self) -> None:
        rev = ReviewerVentricle()
        verdict = rev.review(test_passed=True, coverage_percent=92.0, style_clean=True, security_clean=True)
        assert verdict.passed is True
        assert verdict.seal_status == SealStatus.SEALED

    def _task_09_reviewer_veto_untested(self) -> None:
        rev = ReviewerVentricle()
        verdict = rev.review(test_passed=False, coverage_percent=90.0, style_clean=True, security_clean=True)
        assert verdict.passed is False
        assert verdict.seal_status == SealStatus.VETOED

    def _task_10_reviewer_veto_low_coverage(self) -> None:
        rev = ReviewerVentricle()
        verdict = rev.review(test_passed=True, coverage_percent=78.5, style_clean=True, security_clean=True)
        assert verdict.passed is False
        assert verdict.seal_status == SealStatus.VETOED

    def _task_11_reviewer_veto_security(self) -> None:
        rev = ReviewerVentricle()
        verdict = rev.review(test_passed=True, coverage_percent=95.0, style_clean=True, security_clean=False)
        assert verdict.passed is False
        assert verdict.seal_status == SealStatus.VETOED

    def _task_12_checkpoint_persistence(self) -> None:
        checkpointer = HeartCheckpointer(db_path=":memory:")
        checkpointer.save_checkpoint("t1", "s1", {"status": "done"})
        cp = checkpointer.load_completed_steps("t1")
        assert "s1" in cp
        assert cp["s1"]["status"] == "done"

    def _task_13_crash_recovery_resume(self) -> None:
        checkpointer = HeartCheckpointer(db_path=":memory:")
        budget = HeartBudget()
        supervisor = SupervisorGraph(checkpointer=checkpointer, budget=budget)
        plan = DAGPlan(
            task_id="t_resume",
            objective="Resume Test",
            steps=(
                PlanStep("s1", VentricleRole.PLANNER, "Step 1"),
                PlanStep("s2", VentricleRole.CODER, "Step 2", dependencies=("s1",)),
            ),
        )
        executed = []

        def exec_fn(s: PlanStep):
            executed.append(s.step_id)
            return {"ok": True}

        # Simulasikan crash di s1
        try:
            supervisor.execute_plan(plan, {"s1": exec_fn, "s2": exec_fn}, simulated_crash_after_step="s1")
        except RuntimeError:
            pass

        assert executed == ["s1"]
        executed.clear()

        # Resume: s1 tidak dijalankan lagi, hanya s2!
        res = supervisor.execute_plan(plan, {"s1": exec_fn, "s2": exec_fn})
        assert res["status"] == "success"
        assert executed == ["s2"]

    def _task_14_token_budget_tracking(self) -> None:
        budget = HeartBudget(max_tokens=2000)
        budget.consume(800)
        assert budget.remaining_tokens == 1200

    def _task_15_circuit_breaker_trip(self) -> None:
        budget = HeartBudget(max_tokens=500, overflow_threshold_ratio=1.0)
        for _ in range(3):
            try:
                budget.consume(600)
            except HeartBudgetExceeded:
                pass
        assert budget.circuit_tripped is True

    def _task_16_doctor_deadlock(self) -> None:
        doc = HeartDoctor(max_deadlock_steps=6)
        # 7 langkah mandek dengan proposal yang sama memicu deadlock
        stuck = False
        for _ in range(7):
            deadlock = doc.record_step_execution(step_id="step_same")
            if deadlock:
                stuck = True
                break
        assert stuck is True

    def _task_17_escalation_matrix_red(self) -> None:
        matrix = EscalationMatrix(default_autonomy_level=5)
        dec = matrix.evaluate(BloodPermission.RED)
        from src.heart.matrix import EscalationDecision
        assert dec == EscalationDecision.ASK_USER

    def _task_18_escalation_matrix_green(self) -> None:
        matrix = EscalationMatrix(default_autonomy_level=2)
        dec = matrix.evaluate(BloodPermission.GREEN)
        from src.heart.matrix import EscalationDecision
        assert dec == EscalationDecision.EXECUTE_AUTO

    def _task_19_researcher_iron_rule(self) -> None:
        researcher = ResearcherVentricle()
        try:
            researcher.conduct_research("Noctis", citations=())
            raise AssertionError("Penelitian tanpa sitasi harus ditolak!")
        except ValueError:
            pass

    def _task_20_blood_contract_rejection(self) -> None:
        valid, msg = self.registry.validate_tool_call("hack_mainframe", {})
        assert valid is False
        assert "tidak terdaftar" in msg


def main() -> int:
    print("=" * 60)
    print("BOSS 6 — CRIMSON HEART EVALUATION HARNESS (heart_eval)")
    print("Target Kelulusan: >= 85.0% (Lantai Keras)")
    print("=" * 60)

    evaluator = HeartEvaluator()
    results = evaluator.run_all()

    passed_count = sum(1 for r in results if r.passed)
    total_count = len(results)
    percentage = (passed_count / total_count) * 100.0

    for r in results:
        status_sym = "[OK]" if r.passed else "[FAIL]"
        print(f"{status_sym} #{r.task_id:02d}: {r.name}")
        if not r.passed:
            print(f"      Details: {r.details}")

    print("-" * 60)
    print(f"Hasil Akhir: {passed_count}/{total_count} tugas lulus ({percentage:.1f}%)")

    if percentage >= 85.0:
        print("STATUS: LULUS BOSS 6 CRIMSON HEART EVALUATION")
        return 0
    else:
        print("STATUS: GAGAL BOSS 6 (Di bawah lantai 85%)")
        return 1


if __name__ == "__main__":
    sys.exit(main())
