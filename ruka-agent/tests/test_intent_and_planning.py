# -*- coding: utf-8 -*-
"""Tests for improved intent detection and skill planning quality (Issue #3)."""
from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from src.ruka_cognition.agentic import (
    is_agentic_request,
    make_simple_plan,
)
from src.ruka_cognition.brain import NeuralIntentRouter, RukaCognitiveBrain

ALL_SKILLS = ["code_read", "code_write", "code_edit", "code_search", "run_terminal", "list_dir"]


class TestNeuralIntentRouter:
    @pytest.fixture()
    def router(self) -> NeuralIntentRouter:
        return NeuralIntentRouter()

    def test_coding_intent_detected_across_languages(self, router: NeuralIntentRouter) -> None:
        samples = [
            "bagaimana cara membuat goroutine di golang?",
            "mengapa borrow checker di rust menolak kode ini?",
            "jelaskan async await promise pada typescript",
            "ada memory leak di modul python saya",
            "tolong optimasi query sql dan schema orm ini",
        ]
        for text in samples:
            res = router.analyze(text)
            assert res.is_technical is True
            assert res.intent in ("code_help", "command")

    def test_imperative_coding_command_classified_as_command(self, router: NeuralIntentRouter) -> None:
        samples = [
            "jalankan pytest di terminal",
            "buatkan file helper.py",
            "hapus file temporary di folder cache",
            "perbaiki bug syntax di app.py",
            "git status dong Ruka",
        ]
        for text in samples:
            res = router.analyze(text)
            assert res.intent == "command"
            assert res.is_technical is True

    def test_code_blocks_and_extensions_boost_technical_flag(self, router: NeuralIntentRouter) -> None:
        res1 = router.analyze("coba periksa berkas config.json")
        assert res1.is_technical is True

        res2 = router.analyze("lihat fungsi ini:\n```\ndef foo():\n    return 42\n```")
        assert res2.is_technical is True
        assert res2.intent == "code_help"

    def test_lookup_and_memory_intent(self, router: NeuralIntentRouter) -> None:
        res = router.analyze("Ruka, carikan memori preferensi kopi saya")
        assert res.intent == "lookup"
        assert res.is_technical is False

    def test_chitchat_and_question_classification(self, router: NeuralIntentRouter) -> None:
        chat = router.analyze("halo Ruka, selamat malam!")
        assert chat.intent == "chitchat"
        assert chat.is_technical is False

        q = router.analyze("mengapa langit senja berwarna merah keemasan?")
        assert q.intent == "question"
        assert q.is_technical is False

    def test_confidence_is_calibrated(self, router: NeuralIntentRouter) -> None:
        res = router.analyze("jalankan pytest")
        assert 0.0 <= res.confidence <= 1.0


class TestMakeSimplePlanQuality:
    def test_read_with_line_range_extraction(self) -> None:
        plan1 = make_simple_plan("baca src/app.py baris 10 sampai 30", ALL_SKILLS)
        assert len(plan1) == 1
        assert plan1[0].skill == "code_read"
        assert plan1[0].args == {"path": "src/app.py", "start_line": 10, "end_line": 30}

        plan2 = make_simple_plan("read lines 50-80 of main.py", ALL_SKILLS)
        assert len(plan2) == 1
        assert plan2[0].skill == "code_read"
        assert plan2[0].args == {"path": "main.py", "start_line": 50, "end_line": 80}

    def test_explicit_code_edit_planned(self) -> None:
        plan = make_simple_plan("ganti 'old_val' dengan 'new_val' di src/app.py", ALL_SKILLS)
        assert any(s.skill == "code_edit" for s in plan)
        step = next(s for s in plan if s.skill == "code_edit")
        assert step.args == {"path": "src/app.py", "old_string": "old_val", "new_string": "new_val"}

    def test_explicit_code_write_planned(self) -> None:
        plan = make_simple_plan("buat file hello.py isinya print('halo dunia')", ALL_SKILLS)
        assert any(s.skill == "code_write" for s in plan)
        step = next(s for s in plan if s.skill == "code_write")
        assert step.args["path"] == "hello.py"
        assert step.args["content"] == "print('halo dunia')"

    def test_search_with_scoped_path(self) -> None:
        plan = make_simple_plan("cari handle_request di src", ALL_SKILLS)
        assert any(s.skill == "code_search" for s in plan)
        step = next(s for s in plan if s.skill == "code_search")
        assert step.args["pattern"] == "handle_request"
        assert step.args["path"] == "src"

    def test_direct_cli_command_without_jalankan(self) -> None:
        plan_git = make_simple_plan("git status", ALL_SKILLS)
        assert any(s.skill == "run_terminal" and s.args["command"] == "git status" for s in plan_git)

        plan_pytest = make_simple_plan("pytest tests/test_agentic_mode.py", ALL_SKILLS)
        assert any(s.skill == "run_terminal" and s.args["command"] == "pytest tests/test_agentic_mode.py" for s in plan_pytest)

    def test_question_about_cli_does_not_execute_command(self) -> None:
        plan = make_simple_plan("apa itu git status?", ALL_SKILLS)
        assert not any(s.skill == "run_terminal" for s in plan)

        plan_how = make_simple_plan("bagaimana cara menjalankan pytest?", ALL_SKILLS)
        assert not any(s.skill == "run_terminal" for s in plan_how)

    def test_skill_composition_inspection_before_fix(self) -> None:
        plan = make_simple_plan("perbaiki bug crash di src/auth.py", ALL_SKILLS)
        assert any(s.skill == "code_read" and s.args["path"] == "src/auth.py" for s in plan)


class TestBrainAgenticRouting:
    def test_pure_theoretical_question_avoids_agentic_execution(self, tmp_path: Path) -> None:
        brain = RukaCognitiveBrain(llm_client=None, db_path=str(tmp_path / "t.db"))
        analysis = brain.router.analyze("kenapa python populer untuk machine learning?")
        assert brain._is_agentic_request("kenapa python populer untuk machine learning?", analysis) is False

    def test_actionable_command_triggers_agentic_request(self, tmp_path: Path) -> None:
        brain = RukaCognitiveBrain(llm_client=None, db_path=str(tmp_path / "t.db"))
        analysis = brain.router.analyze("Ruka, tolong baca package.json")
        assert brain._is_agentic_request("Ruka, tolong baca package.json", analysis) is True
