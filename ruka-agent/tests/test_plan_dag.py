# -*- coding: utf-8 -*-
import pytest
from src.agent.planner import (
    PlanRecord,
    PlanStep,
    StepStatus,
    resume,
)


def _plan() -> PlanRecord:
    p = PlanRecord(plan_id="p1", goal="riset laporan")
    p.steps["fetch"] = PlanStep("fetch", "ambil dokumen")
    p.steps["parse"] = PlanStep("parse", "parse pdf", depends_on=["fetch"])
    p.steps["extra"] = PlanStep("extra", "ambil statistik")   # independen
    p.steps["report"] = PlanStep("report", "tulis laporan", depends_on=["parse", "extra"])
    return p


def test_cycle_detected():
    p = _plan()
    p.steps["fetch"].depends_on = ["report"]       # siklus buatan
    with pytest.raises(ValueError, match="siklus"):
        p.validate()


def test_partial_failure_blocks_only_dependents():
    p = _plan()
    p.steps["fetch"].status = StepStatus.DONE
    blocked = p.mark_failed("parse", "ERROR: pdf korup")
    assert blocked == ["report"]
    assert p.steps["extra"].status is StepStatus.PENDING   # hidup
    assert p.steps["report"].status is StepStatus.BLOCKED  # bukan FAILED


def test_ready_steps_respects_dependencies():
    p = _plan()
    assert [s.step_id for s in p.ready_steps()] == ["fetch", "extra"]
    p.steps["fetch"].status = StepStatus.DONE
    p.steps["extra"].status = StepStatus.DONE
    assert [s.step_id for s in p.ready_steps()] == ["parse"]


class FakeExecutor:
    def __init__(self, fail_at: str | None = None, count: dict | None = None):
        self.fail_at, self.count = fail_at, (count if count is not None else {})

    def execute(self, step) -> str:
        self.count[step.step_id] = self.count.get(step.step_id, 0) + 1
        if step.step_id == self.fail_at:
            return "ERROR: sengaja gagal"
        return f"OK: hasil {step.step_id}"


class FakeStore:
    def save(self, plan):
        pass


def test_resume_does_not_redo_done_steps():
    p = _plan()
    p.steps["fetch"].status = StepStatus.DONE
    p.steps["fetch"].result = "OK (proses sebelumnya)"
    count: dict = {}
    resume(p, FakeExecutor(count=count), FakeStore())
    assert count.get("fetch") is None            # TIDAK dieksekusi lagi
    assert p.steps["report"].status is StepStatus.DONE


def test_resume_after_crash_continues_from_checkpoint():
    """Skenario proses mati: fetch selesai persisten; boot ulang."""
    p = _plan()
    p.steps["fetch"].status = StepStatus.DONE      # hasil checkpoint
    count: dict = {}
    resumed = resume(p, FakeExecutor(count=count), FakeStore())
    assert resumed.is_terminal()
    assert count.get("fetch") is None and "parse" in count
