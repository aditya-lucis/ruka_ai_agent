# -*- coding: utf-8 -*-
"""Tests for Action-First Agentic Mode (Issue #1 — Foundation)."""
from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from src.gateway.events import EventBus
from src.gateway.permissions import PermissionManager
from src.gateway.skills.coding_bridge import register_builtin_coding_skills
from src.gateway.skills.registry import SkillRegistry
from src.gateway.skills.runtime import SkillsRuntime
from src.ruka_cognition.agentic import (
    AGENTIC_DOCTRINE,
    PlanStep,
    execute_plan,
    fallback_summary,
    format_results_context,
    is_agentic_request,
    make_simple_plan,
    strip_fake_tool_calls,
)
from src.ruka_cognition.brain import RukaCognitiveBrain

REPO_SKILLS_DIR = Path(__file__).resolve().parents[2] / "skills"
ALL_SKILLS = ["code_read", "code_write", "code_edit", "code_search", "run_terminal", "list_dir"]


@pytest.fixture()
def workspace(tmp_path: Path) -> Path:
    ws = tmp_path / "project"
    ws.mkdir()
    (ws / "package.json").write_text(
        '{"name": "demo", "dependencies": {"react": "^19.0.0", "zod": "^3.23.0"}}',
        encoding="utf-8",
    )
    (ws / "src").mkdir()
    (ws / "src" / "app.py").write_text("def handle_request():\n    return 'ok'\n", encoding="utf-8")
    (tmp_path / "secret.txt").write_text("TOP SECRET", encoding="utf-8")
    return ws


@pytest.fixture()
def runtime(workspace: Path) -> SkillsRuntime:
    registry = SkillRegistry()
    register_builtin_coding_skills(registry, skills_dir=REPO_SKILLS_DIR, workspace_root=workspace)
    return SkillsRuntime(
        registry=registry,
        permission_manager=PermissionManager(workspace),
        event_bus=EventBus(),
    )


class FakeLLM:
    def __init__(self, reply: str = "Hmm... Young Lord, hamba telah menelaah berkas Anda.") -> None:
        self.reply = reply
        self.calls: list[dict[str, Any]] = []

    def complete(self, contents: Any, *, system_instruction: str = "", temperature: float | None = None) -> str:
        self.calls.append({"system_instruction": system_instruction, "temperature": temperature})
        return self.reply


class TestDetection:
    @pytest.mark.parametrize(
        "text",
        [
            "Ruka, baca package.json",
            "lihat isi folder ini",
            "tolong cek file src/app.py",
            "jalankan pytest",
            "git status dong",
            "cari 'handle_request' di kode",
            "coba cek ada apa aja di folder ini",
            "folder ini isinya apa",
            "ada apa di sini",
            "apa isi direktori ini",
        ],
    )
    def test_agentic_requests_detected(self, text: str) -> None:
        assert is_agentic_request(text)

    @pytest.mark.parametrize(
        "text",
        [
            "halo Ruka, apa kabar malam ini?",
            "also, that is false",
            "ceritakan tentang Kekaisaran Trendamis",
            "versi 3.5 lebih cepat ya?",
            "",
        ],
    )
    def test_conversation_not_detected(self, text: str) -> None:
        assert not is_agentic_request(text)


class TestPlanner:
    def test_known_file_is_read(self) -> None:
        plan = make_simple_plan("apa dependensi utama di package.json?", ALL_SKILLS)
        assert [(s.skill, s.args) for s in plan] == [("code_read", {"path": "package.json"})]

    def test_list_current_dir(self) -> None:
        plan = make_simple_plan("lihat isi folder ini", ALL_SKILLS)
        assert [(s.skill, s.args) for s in plan] == [("list_dir", {"path": "."})]

    def test_list_named_dir(self) -> None:
        plan = make_simple_plan("tampilkan struktur folder src", ALL_SKILLS)
        assert plan[-1].skill == "list_dir"
        assert plan[-1].args == {"path": "src"}

    def test_search_quoted_pattern(self) -> None:
        plan = make_simple_plan("cari 'handle_request' di kode", ALL_SKILLS)
        assert plan[0].skill == "code_search"
        assert plan[0].args["pattern"] == "handle_request"

    def test_search_symbol(self) -> None:
        plan = make_simple_plan("temukan fungsi handle_request", ALL_SKILLS)
        assert plan[0].skill == "code_search"
        assert plan[0].args["pattern"] == "handle_request"

    def test_version_numbers_are_not_files(self) -> None:
        assert make_simple_plan("baca catatan versi 3.5", ALL_SKILLS) == []

    def test_unavailable_skills_filtered(self) -> None:
        assert make_simple_plan("baca package.json", ["list_dir"]) == []

    def test_chitchat_yields_empty_plan(self) -> None:
        assert make_simple_plan("halo Ruka, apa kabar?", ALL_SKILLS) == []

    def test_terminal_only_proposed_for_explicit_command(self) -> None:
        plan = make_simple_plan("ls dan baca package.json lalu jalankan pytest", ALL_SKILLS)
        terminal = [s for s in plan if s.skill == "run_terminal"]
        assert [s.args["command"] for s in terminal] == ["pytest"]
        assert plan[-1].skill == "run_terminal"

    def test_terminal_not_planned_for_vague_or_unknown_commands(self) -> None:
        assert not any(s.skill == "run_terminal" for s in make_simple_plan("jalankan saja semuanya", ALL_SKILLS))
        assert not any(s.skill == "run_terminal" for s in make_simple_plan("jalankan rm-semua", ALL_SKILLS))

    def test_backticked_command_is_extracted(self) -> None:
        plan = make_simple_plan("tolong jalankan `echo halo` ya", ALL_SKILLS)
        assert [s.args["command"] for s in plan if s.skill == "run_terminal"] == ["echo halo"]

    def test_test_fix_verify_planning(self) -> None:
        skills = ALL_SKILLS + ["test_fix_verify"]
        plan = make_simple_plan("tolong jalankan test dan perbaiki jika ada error", skills)
        assert any(s.skill == "test_fix_verify" for s in plan)
        tfv = next(s for s in plan if s.skill == "test_fix_verify")
        assert tfv.args["command"] == "pytest"
        assert not any(s.skill == "run_terminal" for s in plan)

        plan_npm = make_simple_plan("run npm test and fix", skills)
        assert any(s.skill == "test_fix_verify" for s in plan_npm)
        tfv_npm = next(s for s in plan_npm if s.skill == "test_fix_verify")
        assert tfv_npm.args["command"] == "npm test"


class TestExecution:
    def test_read_real_file(self, runtime: SkillsRuntime) -> None:
        results = execute_plan([PlanStep("code_read", {"path": "package.json"})], runtime)
        assert results[0].success
        assert "react" in results[0].data["content"]

    def test_list_dir_real(self, runtime: SkillsRuntime) -> None:
        results = execute_plan([PlanStep("list_dir", {"path": "."})], runtime)
        names = {e["name"] for e in results[0].data["entries"]}
        assert {"package.json", "src"} <= names

    def test_list_dir_empty_directory(self, tmp_path: Path) -> None:
        empty_ws = tmp_path / "empty_dir"
        empty_ws.mkdir()
        registry = SkillRegistry()
        register_builtin_coding_skills(registry, skills_dir=REPO_SKILLS_DIR, workspace_root=empty_ws)
        rt = SkillsRuntime(
            registry=registry,
            permission_manager=PermissionManager(empty_ws),
            event_bus=EventBus(),
        )
        plan = make_simple_plan("coba cek ada apa aja di folder ini", ALL_SKILLS)
        assert len(plan) == 1
        assert plan[0].skill == "list_dir"
        results = execute_plan(plan, rt)
        assert results[0].success
        assert results[0].data["entries"] == []
        ctx = format_results_context(results)
        assert "direktori ini kosong" in ctx

    def test_path_jail_blocks_escape(self, runtime: SkillsRuntime) -> None:
        results = execute_plan([PlanStep("code_read", {"path": "../secret.txt"})], runtime)
        assert not results[0].success
        assert "Path Jail" in results[0].error
        assert "TOP SECRET" not in format_results_context(results)

    def test_high_risk_requires_confirmation(self, runtime: SkillsRuntime) -> None:
        results = execute_plan([PlanStep("run_terminal", {"command": "echo hi"})], runtime)
        assert not results[0].success
        assert "konfirmasi" in results[0].error.lower()

    def test_context_is_bounded(self) -> None:
        from src.ruka_cognition.agentic import MAX_CONTEXT_CHARS, StepResult

        big = [StepResult("code_read", {"path": f"f{i}"}, True, {"content": "x" * 50_000}) for i in range(5)]
        assert len(format_results_context(big)) < MAX_CONTEXT_CHARS + 2000


class TestSanitizer:
    def test_strips_fake_calls_outside_code(self) -> None:
        text = "Baik, Young Lord.\n[SYSTEM_CALL: list_directory('.')]\nread_file(\"a.py\")\nSelesai."
        out = strip_fake_tool_calls(text)
        assert "SYSTEM_CALL" not in out
        assert "read_file" not in out
        assert "Selesai." in out

    def test_code_blocks_untouched(self) -> None:
        code = "```python\nread_file(path)\n\n\n\nx = 1\n```"
        assert code in strip_fake_tool_calls(f"Berikut kodenya:\n{code}")


class TestBrainIntegration:
    def _brain(self, tmp_path: Path, runtime: SkillsRuntime, llm: Any) -> RukaCognitiveBrain:
        return RukaCognitiveBrain(
            llm_client=llm,
            db_path=str(tmp_path / "brain.db"),
            skill_registry=runtime.registry,
            skills_runtime=runtime,
        )

    def test_agentic_injects_real_results(self, tmp_path: Path, runtime: SkillsRuntime) -> None:
        llm = FakeLLM("Hmm... Young Lord.\n[SYSTEM_CALL: read_file('package.json')]\nDependensi: react, zod.")
        brain = self._brain(tmp_path, runtime, llm)
        reply = brain.think_and_reply("Ruka, baca package.json dan sebutkan dependensinya")

        prompt = llm.calls[-1]["system_instruction"]
        assert "HASIL EKSEKUSI NYATA" in prompt
        assert '"react": "^19.0.0"' in prompt
        assert AGENTIC_DOCTRINE.splitlines()[0] in prompt
        assert "SYSTEM_CALL" not in reply
        assert "Young Lord" in reply

    def test_chitchat_skips_skills(self, tmp_path: Path, runtime: SkillsRuntime) -> None:
        llm = FakeLLM("Heh... malam yang tenang, Young Lord.")
        brain = self._brain(tmp_path, runtime, llm)
        brain.think_and_reply("halo Ruka, apa kabar malam ini?")
        assert brain.last_agentic_results == []
        assert "=== HASIL EKSEKUSI NYATA (SkillsRuntime) ===" not in llm.calls[-1]["system_instruction"]

    def test_offline_fallback_reports_real_data(self, tmp_path: Path, runtime: SkillsRuntime) -> None:
        brain = self._brain(tmp_path, runtime, llm=None)
        reply = brain.think_and_reply("lihat isi folder ini")
        assert "Young Lord" in reply
        assert "package.json" in reply

    def test_no_runtime_degrades_gracefully(self, tmp_path: Path) -> None:
        brain = RukaCognitiveBrain(llm_client=FakeLLM(), db_path=str(tmp_path / "b.db"))
        brain.think_and_reply("baca package.json")
        assert brain.last_agentic_results == []

    def test_fallback_summary_mentions_failures(self) -> None:
        from src.ruka_cognition.agentic import StepResult

        text = fallback_summary([StepResult("run_terminal", {"command": "x"}, False, error="butuh konfirmasi")])
        assert "butuh konfirmasi" in text


class TestGatewayWiring:
    def test_gateway_registers_skills_and_wires_brain(self, tmp_path: Path) -> None:
        from src.gateway.server import RukaGatewayServer

        brain = RukaCognitiveBrain(llm_client=None, db_path=str(tmp_path / "g.db"))
        gw = RukaGatewayServer(workspace_root=tmp_path, brain=brain)
        try:
            names = {s.name for s in gw.skill_registry.list()}
            assert set(ALL_SKILLS) <= names
            assert brain.skills_runtime is gw.skills_runtime
            assert brain.skill_registry is gw.skill_registry
        finally:
            gw.server_sock.close()


class TestWorkspaceSwitch:
    def test_switch_applies_to_all_skills(self, tmp_path: Path) -> None:
        from src.gateway.server import RukaGatewayServer

        ws_a = tmp_path / "a"
        ws_b = tmp_path / "b"
        ws_a.mkdir()
        ws_b.mkdir()
        (ws_a / "only_a.txt").write_text("A", encoding="utf-8")
        (ws_b / "only_b.txt").write_text("B", encoding="utf-8")

        gw = RukaGatewayServer(workspace_root=ws_a)
        try:
            rt = gw.skills_runtime
            assert rt.execute("code_read", {"path": "only_a.txt"}).success
            assert not rt.execute("code_read", {"path": "only_b.txt"}).success

            gw.permission_mgr.set_workspace(ws_b)

            assert rt.execute("code_read", {"path": "only_b.txt"}).success
            res = rt.execute("code_read", {"path": "only_a.txt"})
            assert not res.success
            listing = rt.execute("list_dir", {"path": "."})
            assert {e["name"] for e in listing.data["entries"]} == {"only_b.txt"}
        finally:
            gw.server_sock.close()

    def test_rejects_dangerous_workspaces(self, tmp_path: Path) -> None:
        import os

        from src.gateway.permissions import PermissionError as GatewayPermissionError

        pm = PermissionManager(tmp_path)
        before = pm.jail.base
        bad = [
            Path(tmp_path.anchor),
            Path.home(),
            tmp_path / "does_not_exist",
            "",
        ]
        windir = os.environ.get("WINDIR")
        if windir:
            bad.append(Path(windir) / "System32")
        for candidate in bad:
            with pytest.raises(GatewayPermissionError):
                pm.set_workspace(candidate)
        assert pm.jail.base == before

    def test_rejects_file_as_workspace(self, tmp_path: Path) -> None:
        from src.gateway.permissions import PermissionError as GatewayPermissionError

        f = tmp_path / "f.txt"
        f.write_text("x", encoding="utf-8")
        with pytest.raises(GatewayPermissionError):
            PermissionManager(tmp_path).set_workspace(f)


# ---------------------------------------------------------------------------
# Issue #2 — guarded multi-step loop
# ---------------------------------------------------------------------------
from src.math_foundations.control import BudgetController  # noqa: E402
from src.ruka_cognition.agentic import (  # noqa: E402
    READ_ONLY_SKILLS,
    AgenticLoop,
    StepResult,
    parse_decision,
)


class ScriptedLLM:
    """Returns scripted planner JSON for decision prompts, persona text otherwise."""

    def __init__(self, decisions: list[str] | None = None, persona: str = "Hmm... Young Lord, selesai.") -> None:
        self.decisions = list(decisions or [])
        self.persona = persona
        self.decision_calls = 0
        self.persona_prompts: list[str] = []

    def complete(self, contents: Any, *, system_instruction: str = "", temperature: float | None = None) -> str:
        if isinstance(contents, str) and "perencana langkah" in contents:
            self.decision_calls += 1
            return self.decisions.pop(0) if self.decisions else '{"done": true}'
        self.persona_prompts.append(system_instruction)
        return self.persona


def _steps(*items: tuple[str, dict[str, Any]]) -> list[PlanStep]:
    return [PlanStep(skill, args) for skill, args in items]


class TestParseDecision:
    def test_valid_steps(self) -> None:
        reply = '{"done": false, "steps": [{"skill": "code_read", "args": {"path": "a.py"}, "reason": "baca"}]}'
        steps = parse_decision(reply)
        assert [(s.skill, s.args) for s in steps] == [("code_read", {"path": "a.py"})]

    def test_done_and_garbage_are_empty(self) -> None:
        assert parse_decision('{"done": true}') == []
        assert parse_decision("bukan json") == []
        assert parse_decision("{rusak") == []
        assert parse_decision(None) == []
        assert parse_decision('{"done": false, "steps": "x"}') == []

    def test_fenced_json_and_step_cap(self) -> None:
        items = ",".join('{"skill": "list_dir", "args": {}}' for _ in range(10))
        steps = parse_decision(f'```json\n{{"done": false, "steps": [{items}]}}\n```')
        assert len(steps) == 3

    def test_invalid_step_entries_skipped(self) -> None:
        reply = '{"done": false, "steps": [1, {"skill": 5}, {"skill": "list_dir", "args": []}, {"skill": "list_dir"}]}'
        assert [s.skill for s in parse_decision(reply)] == ["list_dir"]


class TestAgenticLoop:
    def test_multi_step_exploration_completes(self, runtime: SkillsRuntime) -> None:
        script = [
            _steps(("list_dir", {"path": "."})),
            _steps(("code_read", {"path": "package.json"})),
            [],
        ]
        loop = AgenticLoop(runtime, lambda res: script.pop(0))
        out = loop.run()
        assert out.stop_reason is None
        assert out.rounds == 2
        assert [r.skill for r in out.results] == ["list_dir", "code_read"]
        assert all(r.success for r in out.results)

    def test_duplicate_step_detected_as_loop(self, runtime: SkillsRuntime) -> None:
        loop = AgenticLoop(runtime, lambda res: _steps(("list_dir", {"path": "."})))
        out = loop.run()
        assert "loop terdeteksi" in (out.stop_reason or "")
        assert len(out.results) == 1

    def test_duplicate_detection_normalises_paths(self, runtime: SkillsRuntime) -> None:
        script = [
            _steps(("code_read", {"path": "package.json"})),
            _steps(("code_read", {"path": "./package.json"})),
        ]
        out = AgenticLoop(runtime, lambda res: script.pop(0)).run()
        assert "loop terdeteksi" in (out.stop_reason or "")
        assert len(out.results) == 1

    def test_seed_results_count_towards_duplicates(self, runtime: SkillsRuntime) -> None:
        seed = execute_plan([PlanStep("list_dir", {"path": "."})], runtime)
        out = AgenticLoop(runtime, lambda res: _steps(("list_dir", {"path": "."}))).run(seed)
        assert "loop terdeteksi" in (out.stop_reason or "")
        assert len(out.results) == 1

    def test_repeated_failure_stops(self, runtime: SkillsRuntime) -> None:
        counter = iter(range(100))
        decide = lambda res: _steps(("code_read", {"path": f"missing_{next(counter)}.py"}))  # noqa: E731
        out = AgenticLoop(runtime, decide).run()
        assert "kegagalan berulang" in (out.stop_reason or "")
        assert len(out.results) == 2

    def test_disallowed_skill_never_executes(self, runtime: SkillsRuntime) -> None:
        decide = lambda res: _steps(("run_terminal", {"command": "echo hi"}))  # noqa: E731
        out = AgenticLoop(runtime, decide).run()
        assert out.results
        assert all(not r.success for r in out.results)
        assert all("tidak diizinkan" in (r.error or "") for r in out.results)
        assert "terlarang" in (out.stop_reason or "")

    def test_mutating_skills_not_in_default_allowlist(self) -> None:
        assert READ_ONLY_SKILLS == {
            "code_read",
            "code_search",
            "list_dir",
            "git_status",
            "git_diff",
            "git_log",
            "repo_map",
            "web_search",
            "current_time",
            "geolocation",
            "weather_info",
            "currency_rate",
        }
        for mutating in ("code_write", "code_edit", "run_terminal", "git_commit"):
            assert mutating not in READ_ONLY_SKILLS

    def test_confirmation_required_halts_without_auto_confirm(self, runtime: SkillsRuntime) -> None:
        decide = lambda res: _steps(("run_terminal", {"command": "echo hi"}))  # noqa: E731
        out = AgenticLoop(runtime, decide, allowed_skills={"run_terminal"}).run()
        assert out.stop_reason == "menunggu konfirmasi Young Lord"
        assert not out.results[0].success

    def test_budget_exhaustion_stops(self, runtime: SkillsRuntime) -> None:
        counter = iter(range(100))
        decide = lambda res: _steps(("list_dir", {"path": f"src/../{'.' if next(counter) else 'src'}"}))  # noqa: E731
        budget = BudgetController(max_iterations=1, max_tool_calls=1)
        out = AgenticLoop(runtime, decide, budget=budget).run()
        assert out.stop_reason == "anggaran eksekusi habis"
        assert len(out.results) == 1

    def test_round_cap(self, runtime: SkillsRuntime) -> None:
        counter = iter(range(100))
        decide = lambda res: _steps(("code_search", {"pattern": f"p{next(counter)}", "path": "."}))  # noqa: E731
        out = AgenticLoop(runtime, decide, max_rounds=2).run()
        assert out.stop_reason == "batas putaran perencanaan tercapai"
        assert out.rounds == 2

    def test_planner_exception_is_contained(self, runtime: SkillsRuntime) -> None:
        def boom(res: list[StepResult]) -> list[PlanStep]:
            raise RuntimeError("LLM down")

        out = AgenticLoop(runtime, boom).run()
        assert out.stop_reason == "perencana gagal merespons"

    def test_path_jail_enforced_inside_loop(self, runtime: SkillsRuntime) -> None:
        script = [_steps(("code_read", {"path": "../secret.txt"})), []]
        out = AgenticLoop(runtime, lambda res: script.pop(0)).run()
        assert not out.results[0].success
        assert "Path Jail" in out.results[0].error
        assert "TOP SECRET" not in format_results_context(out.results)

    def test_outcome_reports_health_and_budget(self, runtime: SkillsRuntime) -> None:
        script = [_steps(("list_dir", {"path": "."})), []]
        out = AgenticLoop(runtime, lambda res: script.pop(0)).run()
        assert 0.0 <= out.health <= 1.0
        assert out.budget["tool_calls"].startswith("1/")


class TestBrainLoopIntegration:
    def _brain(self, tmp_path: Path, runtime: SkillsRuntime, llm: Any) -> RukaCognitiveBrain:
        return RukaCognitiveBrain(
            llm_client=llm,
            db_path=str(tmp_path / "loop.db"),
            skill_registry=runtime.registry,
            skills_runtime=runtime,
        )

    def test_multistep_request_follows_llm_plan(self, tmp_path: Path, runtime: SkillsRuntime) -> None:
        llm = ScriptedLLM(
            decisions=[
                '{"done": false, "steps": [{"skill": "code_read", "args": {"path": "src/app.py"}}]}',
                '{"done": true}',
            ]
        )
        brain = self._brain(tmp_path, runtime, llm)
        brain.think_and_reply("cari 'handle_request' di kode lalu jelaskan alurnya")

        skills = [r.skill for r in brain.last_agentic_results]
        assert skills == ["code_search", "code_read"]
        assert llm.decision_calls == 2
        assert "def handle_request" in llm.persona_prompts[-1]
        assert brain.last_loop_outcome is not None and brain.last_loop_outcome.stop_reason is None

    def test_simple_request_does_not_call_planner(self, tmp_path: Path, runtime: SkillsRuntime) -> None:
        llm = ScriptedLLM()
        brain = self._brain(tmp_path, runtime, llm)
        brain.think_and_reply("Ruka, baca package.json")
        assert llm.decision_calls == 0
        assert brain.last_loop_outcome is None
        assert [r.skill for r in brain.last_agentic_results] == ["code_read"]

    def test_stop_reason_reaches_persona_prompt(self, tmp_path: Path, runtime: SkillsRuntime) -> None:
        same = '{"done": false, "steps": [{"skill": "list_dir", "args": {"path": "."}}]}'
        llm = ScriptedLLM(decisions=[same, same, same])
        brain = self._brain(tmp_path, runtime, llm)
        brain.think_and_reply("cek isi folder lalu analisis strukturnya")
        prompt = llm.persona_prompts[-1]
        assert "Catatan sistem" in prompt
        assert "loop terdeteksi" in prompt

    def test_planner_cannot_trigger_terminal(self, tmp_path: Path, runtime: SkillsRuntime) -> None:
        evil = '{"done": false, "steps": [{"skill": "run_terminal", "args": {"command": "echo pwned"}}]}'
        llm = ScriptedLLM(decisions=[evil, evil, evil])
        brain = self._brain(tmp_path, runtime, llm)
        brain.think_and_reply("cek isi folder lalu analisis strukturnya")
        assert not any(r.skill == "run_terminal" and r.success for r in brain.last_agentic_results)
        assert len(brain.last_pending) == 1
        assert brain.last_pending[0].skill_name == "run_terminal"

    def test_offline_llm_skips_loop(self, tmp_path: Path, runtime: SkillsRuntime) -> None:
        brain = self._brain(tmp_path, runtime, llm=None)
        brain.think_and_reply("cek isi folder lalu analisis strukturnya")
        assert brain.last_loop_outcome is None
