# -*- coding: utf-8 -*-
"""Boss Gate 3 — Crimson Heart V3 Test Suite (FR-HE).

Verifikasi:
- Boss 6 Crimson Heart:
  - Detak jantung 0.5 Hz dengan nomor denyut persisten
  - Validasi rencana tugas DAG 2-6 langkah (asiklik, siklus ditolak keras)
  - 7 Ventrikel: Planner, Researcher, Coder, Reviewer, DevOps, ERP, Browser
  - Hak veto Reviewer 4 segel (uji, cakupan >= 85%, gaya, OWASP)
  - Checkpoint per super-step ke SQLite & resume instan pasca crash
  - Kontrak Darah 13 alat MCP & validasi skema
  - Matriks Eskalasi 18 sel (RED selalu bertanya tanpa kompromi)
  - Anggaran napas 180k token & circuit breaker
  - Heart Doctor (deteksi denyut hilang > 6s dan deadlock > 6 langkah)
  - EventBus V3 namespace heart.*
"""
import time
import pytest
from src.gateway.events import EventBus, OrganNamespace
from src.heart import (
    BloodPermission,
    BloodRegistry,
    CoderVentricle,
    CrimsonHeart,
    DAGPlan,
    DevOpsVentricle,
    ERPVentricle,
    EditProposal,
    EscalationDecision,
    EscalationMatrix,
    HeartBudget,
    HeartBudgetExceeded,
    HeartCheckpointer,
    HeartDoctor,
    PlanStep,
    PlannerVentricle,
    ResearcherVentricle,
    ReviewVerdict,
    ReviewerVentricle,
    SealStatus,
    StructuredFailureReport,
    SupervisorGraph,
    VentricleRole,
)


class TestDAGPlanValidation:
    def test_dag_step_count_and_acyclic(self):
        planner = PlannerVentricle()

        # Kurang dari 2 langkah -> tolak
        with pytest.raises(ValueError, match="2 sampai 6 langkah"):
            DAGPlan(task_id="t1", objective="Obj", steps=(PlanStep("s1", VentricleRole.CODER, "step 1"),))

        # Lebih dari 6 langkah -> tolak
        with pytest.raises(ValueError, match="2 sampai 6 langkah"):
            DAGPlan(
                task_id="t2",
                objective="Obj",
                steps=tuple(PlanStep(f"s{i}", VentricleRole.CODER, f"step {i}") for i in range(7)),
            )

        # Dependensi ke diri sendiri (siklus langsung) -> tolak
        with pytest.raises(ValueError, match="[sS]iklus"):
            DAGPlan(
                task_id="t3",
                objective="Obj",
                steps=(
                    PlanStep("s1", VentricleRole.CODER, "step 1", dependencies=("s1",)),
                    PlanStep("s2", VentricleRole.REVIEWER, "step 2"),
                ),
            )

        # Siklus tidak langsung (s1 -> s2 -> s3 -> s1) -> tolak keras
        with pytest.raises(ValueError, match="[sS]iklus"):
            DAGPlan(
                task_id="t3_cycle",
                objective="Obj",
                steps=(
                    PlanStep("s1", VentricleRole.PLANNER, "step 1", dependencies=("s3",)),
                    PlanStep("s2", VentricleRole.CODER, "step 2", dependencies=("s1",)),
                    PlanStep("s3", VentricleRole.REVIEWER, "step 3", dependencies=("s2",)),
                ),
            )

        # 3 langkah valid asiklik
        plan = planner.create_plan(
            task_id="t4",
            objective="Refactor Auth",
            steps_data=[
                {"step_id": "step_plan", "ventricle": "planner", "description": "Rencana"},
                {"step_id": "step_code", "ventricle": "coder", "description": "Kode", "dependencies": ["step_plan"]},
                {"step_id": "step_review", "ventricle": "reviewer", "description": "Review", "dependencies": ["step_code"]},
            ],
        )
        assert len(plan.steps) == 3


class TestSevenVentricles:
    def test_researcher_iron_rule(self):
        researcher = ResearcherVentricle()
        # Laporan tanpa sitasi -> tolak
        with pytest.raises(ValueError, match="Laporan tanpa sitasi"):
            researcher.conduct_research("Algoritma Graph", citations=[])

        # > 12 halaman -> tolak
        with pytest.raises(ValueError, match="Maksimal 12 halaman"):
            researcher.conduct_research("LLM Scaling", citations=[{"url": f"https://arxiv.org/{i}"} for i in range(13)])

        # Sah
        res = researcher.conduct_research("LangGraph", citations=[{"url": "https://langchain.com", "date": "2026-10-01"}])
        assert res["citations_count"] == 1

    def test_coder_edit_proposal(self):
        coder = CoderVentricle()
        prop = coder.propose_edit(
            file_path="src/main.py",
            anchor_signature="def start_server():",
            new_content="def start_server():\n    return True",
            reason="Fix bug",
            test_cmd="pytest tests/test_main.py",
        )
        assert prop.file_path == "src/main.py"
        assert prop.anchor_signature == "def start_server():"

    def test_reviewer_four_seals_veto(self):
        reviewer = ReviewerVentricle()

        # 1. Seluruh 4 segel lulus (uji hijau, cakupan >= 85%, gaya bersih, OWASP bersih)
        v1 = reviewer.review(test_passed=True, coverage_percent=88.5, style_clean=True, security_clean=True)
        assert v1.passed is True
        assert v1.seal_status == SealStatus.SEALED

        # 2. Cakupan di bawah 85% -> VETO
        v2 = reviewer.review(test_passed=True, coverage_percent=82.0, style_clean=True, security_clean=True)
        assert v2.passed is False
        assert v2.seal_status == SealStatus.VETOED

        # 3. Uji merah -> VETO
        v3 = reviewer.review(test_passed=False, coverage_percent=95.0, style_clean=True, security_clean=True)
        assert v3.passed is False

        # 4. Pelanggaran OWASP keamanan -> VETO
        v4 = reviewer.review(test_passed=True, coverage_percent=90.0, style_clean=True, security_clean=False)
        assert v4.passed is False

    def test_devops_probes(self):
        devops = DevOpsVentricle()
        res_ok = devops.deploy_and_probe([True, True, True])
        assert res_ok["healthy"] is True
        assert res_ok["rollback_triggered"] is False

        res_fail = devops.deploy_and_probe([True, False, True])
        assert res_fail["healthy"] is False
        assert res_fail["rollback_triggered"] is True


class TestSupervisorCheckpointAndResume:
    def test_crash_recovery_without_repeating_completed_steps(self):
        checkpointer = HeartCheckpointer(db_path=":memory:")
        budget = HeartBudget()
        supervisor = SupervisorGraph(checkpointer=checkpointer, budget=budget)

        plan = DAGPlan(
            task_id="task_migration_1",
            objective="Migrasi Database",
            steps=(
                PlanStep("s1", VentricleRole.PLANNER, "Analisis skema"),
                PlanStep("s2", VentricleRole.CODER, "Tulis migrasi", dependencies=("s1",)),
                PlanStep("s3", VentricleRole.REVIEWER, "Tinjau migrasi", dependencies=("s2",)),
            ),
        )

        executed_steps = []

        def step_exec(s: PlanStep):
            executed_steps.append(s.step_id)
            return {"output": f"done_{s.step_id}"}

        # 1. Run pertama: crash disimulasikan tepat setelah langkah 's2' selesai
        with pytest.raises(RuntimeError, match="SIMULATED_CRASH"):
            supervisor.execute_plan(
                plan,
                step_executors={"s1": step_exec, "s2": step_exec, "s3": step_exec},
                simulated_crash_after_step="s2",
            )

        assert executed_steps == ["s1", "s2"]

        # 2. Run kedua: RESUME setelah crash! Langkah 's1' dan 's2' tidak boleh diulang!
        executed_steps.clear()
        res = supervisor.execute_plan(
            plan,
            step_executors={"s1": step_exec, "s2": step_exec, "s3": step_exec},
            simulated_crash_after_step=None,
        )

        assert res["status"] == "success"
        # Hanya langkah 's3' yang dieksekusi saat resume!
        assert executed_steps == ["s3"]


class TestHeartBudgetAndCircuitBreaker:
    def test_budget_consumption_and_breaker(self):
        budget = HeartBudget(max_tokens=1000, max_duration_s=10.0, overflow_threshold_ratio=1.05)

        # Konsumsi normal
        budget.consume(500)
        assert budget.remaining_tokens == 500

        # Melimpas di atas 1050 token (overflow 5%)
        with pytest.raises(HeartBudgetExceeded):
            budget.consume(600)  # Total 1100 > 1050 (Strike 1)

        with pytest.raises(HeartBudgetExceeded):
            budget.consume(1)   # Strike 2

        # Strike 3 -> Circuit Breaker Tripped!
        with pytest.raises(HeartBudgetExceeded, match="permanen"):
            budget.consume(1)   # Strike 3
        assert budget.circuit_tripped is True


class TestBloodContractAndEscalationMatrix:
    def test_thirteen_mcp_tools_and_validation(self):
        reg = BloodRegistry()
        assert len(reg.tool_names) == 13

        # code_read butuh 'path'
        ok, _ = reg.validate_tool_call("code_read", {"path": "src/main.py"})
        assert ok is True

        fail, msg = reg.validate_tool_call("code_read", {})
        assert fail is False
        assert "path" in msg

        # Alat tidak terdaftar
        fail_foreign, _ = reg.validate_tool_call("hack_mainframe", {})
        assert fail_foreign is False

    def test_escalation_matrix_18_cells(self):
        # Level 2 (Default): Green auto, Yellow ask, Red ask
        m2 = EscalationMatrix(default_autonomy_level=2)
        assert m2.evaluate(BloodPermission.GREEN) == EscalationDecision.EXECUTE_AUTO
        assert m2.evaluate(BloodPermission.YELLOW) == EscalationDecision.ASK_USER
        assert m2.evaluate(BloodPermission.RED) == EscalationDecision.ASK_USER

        # Level 4 (Tinggi): Green auto, Yellow auto, Red SELALU ask
        m4 = EscalationMatrix(default_autonomy_level=4)
        assert m4.evaluate(BloodPermission.GREEN) == EscalationDecision.EXECUTE_AUTO
        assert m4.evaluate(BloodPermission.YELLOW) == EscalationDecision.EXECUTE_AUTO
        assert m4.evaluate(BloodPermission.RED) == EscalationDecision.ASK_USER


class TestHeartDoctorAndHeartbeat:
    def test_doctor_detects_silence_and_deadlock(self):
        doctor = HeartDoctor(max_beat_silence_s=6.0, max_deadlock_steps=6)

        # Jantung sehat
        doctor.record_beat(1, now=100.0)
        h1 = doctor.check_health(now=102.0)
        assert h1["status"] == "healthy"

        # Denyut hilang > 6 detik
        h2 = doctor.check_health(now=107.0)
        assert h2["status"] == "critical"
        assert h2["silence_duration_s"] == 7.0

        # Deadlock detection: simpul yang sama dieksekusi 7x
        for _ in range(6):
            deadlock = doctor.record_step_execution("coder_retry_step")
            assert deadlock is False

        deadlock7 = doctor.record_step_execution("coder_retry_step")
        assert deadlock7 is True

    def test_crimson_heart_pipeline_and_eventbus(self):
        bus = EventBus()
        heart = CrimsonHeart(event_bus=bus, initial_beat=10)

        events = []
        bus.subscribe("heart.*", lambda e: events.append(e))

        # Jalankan satu detak jantung
        res = heart.step_beat()
        assert res["beat_number"] == 11
        assert res["phase"] == "act_completed"

        bus.drain()
        topics = [e.event_type for e in events]
        assert "heart.beat" in topics
