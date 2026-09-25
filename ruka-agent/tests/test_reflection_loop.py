# -*- coding: utf-8 -*-
from src.reflection.loop import (
    CheckKind,
    CheckVerdict,
    CorrectionPlan,
    ReflectionBudget,
    ReflectionLoop,
    Severity,
)


def make_checker(script: dict[tuple[int, str], CheckVerdict], counter: dict):
    """checker terprogram: (putaran ke-, kind) -> verdict."""
    def checker(draft: str, kind: CheckKind) -> CheckVerdict:
        counter["rounds"] = counter.get("rounds", 0)
        key = (counter["rounds"], kind.value)
        return script.get(key, CheckVerdict(kind=kind, severity=Severity.PASS))
    return checker


def bump_rounds_after(corrector):
    """corrector yang menaikkan penghitung putaran (emulasi loop)."""
    def wrapped(draft, problems):
        return CorrectionPlan(
            revised_answer=draft + " [fixed]",
            applied_fixes=[p.kind.value for p in problems],
        )
    return wrapped


class RoundBumper:
    def __init__(self, inner, counter):
        self.inner, self.counter = inner, counter
        self._seen_validation = False

    def __call__(self, draft, kind):
        if kind is CheckKind.VALIDATION:
            if self._seen_validation:
                self.counter["rounds"] = self.counter.get("rounds", 0) + 1
            else:
                self._seen_validation = True
                self.counter["rounds"] = self.counter.get("rounds", 0)
        return self.inner(draft, kind)


def test_clean_draft_passes_without_correction():
    counter = {}
    loop = ReflectionLoop(
        make_checker({}, counter),
        lambda d, p: CorrectionPlan(revised_answer=d),
    )
    report = loop.run("jawaban bersih")
    assert report.corrections_used == 0
    assert report.stopped_reason == "complete"
    assert report.stages_run == [k.value for k in ReflectionLoop.STAGES]


def test_major_found_then_fixed_then_clean():
    script = {
        (0, "evidence"): CheckVerdict(
            kind=CheckKind.EVIDENCE,
            severity=Severity.MAJOR,
            problem="klaim tanpa bukti",
            fix_hint="kutip sumber",
        )
    }
    counter = {}
    checker = RoundBumper(make_checker(script, counter), counter)
    loop = ReflectionLoop(
        checker,
        lambda d, p: CorrectionPlan(revised_answer=d + " + kutipan"),
    )
    report = loop.run("draft")
    assert report.corrections_used == 1
    assert "kutipan" in report.final_answer
    assert report.stopped_reason == "complete"


def test_budget_stops_infinite_criticism():
    """SPEC: anti infinite self-criticism – kegagalan menetap berhenti."""
    always_major = lambda draft, kind: CheckVerdict(   # noqa: E731
        kind=kind, severity=Severity.MAJOR, problem="selalu salah")
    counter = {"rounds": 0}

    class RoundInc:
        def __init__(self, c):
            self.c = c

        def __call__(self, draft, kind):
            if kind is CheckKind.VALIDATION:
                self.c["rounds"] += 1
            return always_major(draft, kind)

    loop = ReflectionLoop(
        RoundInc(counter),
        lambda d, p: CorrectionPlan(revised_answer=d + "!"),
    )
    report = loop.run("draft")
    assert report.corrections_used <= ReflectionBudget().max_corrections
    assert report.stopped_reason in ("budget_stage", "budget_corrections")
    assert len(report.stages_run) <= 3 * len(ReflectionLoop.STAGES)


def test_fatal_exhausted_produces_honest_refusal():
    script = {
        (0, "evidence"): CheckVerdict(
            kind=CheckKind.EVIDENCE,
            severity=Severity.FATAL,
            problem="klaim berbahaya tanpa bukti",
        )
    }
    counter = {}
    checker = RoundBumper(make_checker(script, counter), counter)
    budget = ReflectionBudget(max_corrections=0)
    loop = ReflectionLoop(checker, lambda d, p: CorrectionPlan(revised_answer=d), budget)
    report = loop.run("draft berbahaya")
    assert "tidak dapat menghasilkan" in report.final_answer
    assert report.stopped_reason == "budget_corrections"
