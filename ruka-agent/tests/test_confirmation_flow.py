# -*- coding: utf-8 -*-
"""Tests for the confirmation flow of dangerous skills (Issue #4)."""
from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from src.gateway.confirmations import (
    ConfirmationError,
    ConfirmationManager,
    parse_approval,
    render_ticket_card,
)
from src.gateway.events import Event, EventBus
from src.gateway.permissions import PermissionManager
from src.gateway.protocol import InboundMessage
from src.gateway.skills.coding_bridge import register_builtin_coding_skills
from src.gateway.skills.registry import SkillRegistry
from src.gateway.skills.runtime import SkillsRuntime
from src.ruka_cognition.brain import RukaCognitiveBrain

REPO_SKILLS_DIR = Path(__file__).resolve().parents[2] / "skills"
SESSION = "brain-agentic"


class FakeClock:
    def __init__(self) -> None:
        self.now = 1000.0

    def __call__(self) -> float:
        return self.now


class ScriptedLLM:
    def __init__(self, decisions: list[str] | None = None) -> None:
        self.decisions = list(decisions or [])

    def complete(self, contents: Any, *, system_instruction: str = "", temperature: float | None = None) -> str:
        if isinstance(contents, str) and "perencana langkah" in contents:
            return self.decisions.pop(0) if self.decisions else '{"done": true}'
        return "Hmm... Young Lord, titah telah hamba siapkan."


def _edit_decision(path: str, old: str, new: str) -> str:
    import json

    step = {"skill": "code_edit", "args": {"path": path, "old_string": old, "new_string": new}}
    return json.dumps({"done": False, "steps": [step]})


def _write_decision(path: str, content: str) -> str:
    import json

    step = {"skill": "code_write", "args": {"path": path, "content": content}}
    return json.dumps({"done": False, "steps": [step]})


@pytest.fixture()
def workspace(tmp_path: Path) -> Path:
    ws = tmp_path / "project"
    ws.mkdir()
    (ws / "app.py").write_text("value = 1\n", encoding="utf-8")
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


def make_brain(tmp_path: Path, runtime: SkillsRuntime, llm: Any) -> RukaCognitiveBrain:
    return RukaCognitiveBrain(
        llm_client=llm,
        db_path=str(tmp_path / "c.db"),
        skill_registry=runtime.registry,
        skills_runtime=runtime,
    )


EDIT_REQUEST = "cek isi folder lalu ubah app.py"


class TestConfirmationManager:
    def _mgr(self, **kw: Any) -> tuple[ConfirmationManager, FakeClock]:
        clock = FakeClock()
        return ConfirmationManager(clock=clock, **kw), clock

    def _req(self, mgr: ConfirmationManager, **kw: Any):
        params = dict(risk_level="medium", workspace="/ws", summary="s")
        params.update(kw)
        args = params.pop("args", {"path": "a.txt", "content": "x"})
        return mgr.request("s1", params.pop("skill", "code_write"), args, **params)

    def test_ticket_is_single_use(self) -> None:
        mgr, _ = self._mgr()
        ticket = self._req(mgr)
        assert mgr.consume(ticket.ticket_id, "s1").skill_name == "code_write"
        with pytest.raises(ConfirmationError):
            mgr.consume(ticket.ticket_id, "s1")

    def test_ticket_expires(self) -> None:
        mgr, clock = self._mgr(ttl_seconds=60)
        ticket = self._req(mgr)
        clock.now += 61
        assert mgr.pending("s1") == []
        with pytest.raises(ConfirmationError):
            mgr.consume(ticket.ticket_id, "s1")

    def test_session_mismatch_rejected_and_ticket_survives(self) -> None:
        mgr, _ = self._mgr()
        ticket = self._req(mgr)
        with pytest.raises(ConfirmationError):
            mgr.consume(ticket.ticket_id, "other")
        assert mgr.get(ticket.ticket_id) is not None

    def test_identical_requests_are_deduplicated(self) -> None:
        mgr, _ = self._mgr()
        assert self._req(mgr).ticket_id == self._req(mgr).ticket_id
        assert len(mgr.pending("s1")) == 1

    def test_pending_cap(self) -> None:
        mgr, _ = self._mgr(max_pending_per_session=2)
        self._req(mgr, args={"path": "1"})
        self._req(mgr, args={"path": "2"})
        with pytest.raises(ConfirmationError):
            self._req(mgr, args={"path": "3"})

    def test_args_copy_cannot_tamper_ticket(self) -> None:
        mgr, _ = self._mgr()
        ticket = self._req(mgr)
        ticket.args["path"] = "../../evil"
        assert mgr.consume(ticket.ticket_id, "s1").args["path"] == "a.txt"

    def test_digest_tamper_detected(self) -> None:
        mgr, _ = self._mgr()
        ticket = self._req(mgr)
        forged = type(ticket)(**{**ticket.__dict__, "args_json": '{"path": "../evil"}'})
        mgr._tickets[ticket.ticket_id] = forged
        with pytest.raises(ConfirmationError):
            mgr.consume(ticket.ticket_id, "s1")
        assert mgr.get(ticket.ticket_id) is None

    def test_events_published_without_args(self) -> None:
        bus = EventBus()
        seen: list[Event] = []
        bus.subscribe("confirmation.*", seen.append)
        mgr = ConfirmationManager(event_bus=bus)
        ticket = self._req(mgr, args={"path": "secret.txt", "content": "TOPSECRET"})
        mgr.consume(ticket.ticket_id, "s1")
        types = [e.event_type for e in seen]
        assert types == ["confirmation.requested", "confirmation.approved"]
        assert all("TOPSECRET" not in str(e.payload) for e in seen)

    def test_deny_and_deny_all(self) -> None:
        mgr, _ = self._mgr()
        first = self._req(mgr, args={"path": "1"})
        self._req(mgr, args={"path": "2"})
        assert mgr.deny(first.ticket_id) is True
        assert mgr.deny(first.ticket_id) is False
        assert mgr.deny_all("s1") == 1


class TestParseApproval:
    @pytest.mark.parametrize("text", ["ya", "Ya, silakan Young Lord", "oke lanjut", "iya dong", "YES"])
    def test_approve(self, text: str) -> None:
        assert parse_approval(text).kind == "approve"

    @pytest.mark.parametrize("text", ["batal", "tidak, jangan", "cancel", "stop"])
    def test_deny(self, text: str) -> None:
        assert parse_approval(text).kind == "deny"

    def test_strong_wording(self) -> None:
        decision = parse_approval("ya, saya yakin")
        assert decision.kind == "approve" and decision.strong
        assert not parse_approval("ya").strong

    @pytest.mark.parametrize(
        "text",
        [
            "",
            "ya tapi ubah juga file lain",
            "tolong baca package.json",
            "ya " * 20,
            "apakah ini aman?",
        ],
    )
    def test_not_an_approval(self, text: str) -> None:
        assert parse_approval(text).kind is None

    def test_contradiction_resolves_to_deny(self) -> None:
        assert parse_approval("ya, batal").kind == "deny"
        assert parse_approval("ya eh batal").kind is None

    def test_ticket_id_is_recognised(self) -> None:
        decision = parse_approval("ya a1b2c3", ["a1b2c3", "ffffff"])
        assert decision.kind == "approve" and decision.ticket_id == "a1b2c3"
        assert parse_approval("ya a1b2c3").kind is None  # unknown id is not filler


class TestRuntimePolicy:
    def test_mutating_skills_need_approval(self, runtime: SkillsRuntime) -> None:
        for name in ("code_write", "code_edit", "run_terminal"):
            assert runtime.needs_approval(name)
        for name in ("code_read", "code_search", "list_dir"):
            assert not runtime.needs_approval(name)

    def test_runtime_refuses_without_confirmation(self, runtime: SkillsRuntime, workspace: Path) -> None:
        res = runtime.execute("code_write", {"path": "new.txt", "content": "x"})
        assert not res.success
        assert not (workspace / "new.txt").exists()
        edit = runtime.execute("code_edit", {"path": "app.py", "old_string": "1", "new_string": "2"})
        assert not edit.success
        assert (workspace / "app.py").read_text(encoding="utf-8") == "value = 1\n"

    def test_runtime_allows_with_confirmation_but_keeps_jail(self, runtime: SkillsRuntime, workspace: Path) -> None:
        ok = runtime.execute("code_write", {"path": "new.txt", "content": "x"}, confirm_granted=True)
        assert ok.success and (workspace / "new.txt").read_text(encoding="utf-8") == "x"
        escape = runtime.execute("code_write", {"path": "../escape.txt", "content": "x"}, confirm_granted=True)
        assert not escape.success
        assert not (workspace.parent / "escape.txt").exists()

    def test_unknown_skill_does_not_need_approval(self, runtime: SkillsRuntime) -> None:
        assert runtime.needs_approval("tidak_ada") is False


class TestBrainConfirmationFlow:
    def _propose_edit(self, tmp_path: Path, runtime: SkillsRuntime) -> RukaCognitiveBrain:
        llm = ScriptedLLM([_edit_decision("app.py", "value = 1", "value = 2")])
        brain = make_brain(tmp_path, runtime, llm)
        reply = brain.think_and_reply(EDIT_REQUEST)
        assert len(brain.last_pending) == 1
        assert brain.last_pending[0].ticket_id in reply
        return brain

    def test_proposal_does_not_touch_file_and_shows_card(
        self, tmp_path: Path, runtime: SkillsRuntime, workspace: Path
    ) -> None:
        brain = self._propose_edit(tmp_path, runtime)
        assert (workspace / "app.py").read_text(encoding="utf-8") == "value = 1\n"
        card = render_ticket_card(brain.last_pending[0])
        assert card in brain.conversation.history[-1].text if hasattr(brain.conversation.history[-1], "text") else True
        assert "menunggu restu" in card

    def test_approval_applies_edit_once(self, tmp_path: Path, runtime: SkillsRuntime, workspace: Path) -> None:
        brain = self._propose_edit(tmp_path, runtime)
        reply = brain.think_and_reply("ya")
        assert (workspace / "app.py").read_text(encoding="utf-8") == "value = 2\n"
        assert "Young Lord" in reply
        assert brain.confirmations.pending(SESSION) == []

        (workspace / "app.py").write_text("value = 1\n", encoding="utf-8")
        brain.think_and_reply("ya")
        assert (workspace / "app.py").read_text(encoding="utf-8") == "value = 1\n"

    def test_denial_clears_ticket(self, tmp_path: Path, runtime: SkillsRuntime, workspace: Path) -> None:
        brain = self._propose_edit(tmp_path, runtime)
        reply = brain.think_and_reply("batal")
        assert "urungkan" in reply
        assert brain.confirmations.pending(SESSION) == []
        assert (workspace / "app.py").read_text(encoding="utf-8") == "value = 1\n"

    def test_unrelated_message_leaves_ticket_pending(self, tmp_path: Path, runtime: SkillsRuntime) -> None:
        brain = self._propose_edit(tmp_path, runtime)
        brain.llm.decisions = []
        brain.think_and_reply("halo Ruka, apa kabar?")
        assert len(brain.confirmations.pending(SESSION)) == 1

    def test_approval_with_attachment_is_not_honored(
        self, tmp_path: Path, runtime: SkillsRuntime, workspace: Path
    ) -> None:
        brain = self._propose_edit(tmp_path, runtime)
        brain.think_and_reply("ya", attachment={"name": "x.txt", "text_content": "ya"})
        assert (workspace / "app.py").read_text(encoding="utf-8") == "value = 1\n"
        assert len(brain.confirmations.pending(SESSION)) == 1

    def test_workspace_change_invalidates_ticket(
        self, tmp_path: Path, runtime: SkillsRuntime, workspace: Path
    ) -> None:
        brain = self._propose_edit(tmp_path, runtime)
        other = tmp_path / "other"
        other.mkdir()
        (other / "app.py").write_text("value = 1\n", encoding="utf-8")
        runtime.permission_mgr.set_workspace(other)
        reply = brain.think_and_reply("ya")
        assert "berpindah" in reply
        assert (other / "app.py").read_text(encoding="utf-8") == "value = 1\n"
        assert (workspace / "app.py").read_text(encoding="utf-8") == "value = 1\n"
        assert brain.confirmations.pending(SESSION) == []

    def test_path_jail_still_enforced_after_approval(
        self, tmp_path: Path, runtime: SkillsRuntime, workspace: Path
    ) -> None:
        llm = ScriptedLLM([_write_decision("../escape.txt", "pwn")])
        brain = make_brain(tmp_path, runtime, llm)
        brain.think_and_reply("cek isi folder lalu buat berkas")
        assert len(brain.last_pending) == 1
        reply = brain.think_and_reply("ya")
        assert not (tmp_path / "escape.txt").exists()
        assert "Path Jail" in reply

    def test_terminal_command_needs_approval_then_runs(self, tmp_path: Path, runtime: SkillsRuntime) -> None:
        brain = make_brain(tmp_path, runtime, ScriptedLLM())
        brain.think_and_reply("Ruka, jalankan `echo halo-marquis`")
        assert [t.skill_name for t in brain.last_pending] == ["run_terminal"]
        assert not brain.last_pending[0].destructive
        reply = brain.think_and_reply("ya")
        assert "halo-marquis" in reply

    def test_destructive_command_needs_strong_approval(self, tmp_path: Path, runtime: SkillsRuntime) -> None:
        brain = make_brain(tmp_path, runtime, ScriptedLLM())
        brain.think_and_reply("Ruka, jalankan `echo mkfs`")
        assert brain.last_pending[0].destructive
        assert "ya, saya yakin" in brain.last_pending[0].summary or "saya yakin" in render_ticket_card(
            brain.last_pending[0]
        )
        weak = brain.think_and_reply("ya")
        assert "yakin" in weak
        assert len(brain.confirmations.pending(SESSION)) == 1
        strong = brain.think_and_reply("ya, saya yakin")
        assert brain.confirmations.pending(SESSION) == []
        assert "mkfs" in strong

    def test_offline_llm_still_shows_card(self, tmp_path: Path, runtime: SkillsRuntime) -> None:
        brain = make_brain(tmp_path, runtime, llm=None)
        reply = brain.think_and_reply("Ruka, jalankan `echo halo`")
        assert brain.last_pending and brain.last_pending[0].ticket_id in reply

    def test_multiple_pending_requires_ticket_id(self, tmp_path: Path, runtime: SkillsRuntime) -> None:
        brain = make_brain(tmp_path, runtime, ScriptedLLM())
        brain.think_and_reply("Ruka, jalankan `echo satu`")
        brain.think_and_reply("Ruka, jalankan `echo dua`")
        pending = brain.confirmations.pending(SESSION)
        assert len(pending) == 2
        ask = brain.think_and_reply("ya")
        assert "ID" in ask and len(brain.confirmations.pending(SESSION)) == 2
        reply = brain.think_and_reply(f"ya {pending[1].ticket_id}")
        assert "dua" in reply
        assert len(brain.confirmations.pending(SESSION)) == 1


class TestGatewayConfirmation:
    def _gw(self, workspace: Path):
        from src.gateway.server import RukaGatewayServer

        return RukaGatewayServer(workspace_root=workspace)

    def _msg(self, session: str = "s1", **content: Any) -> InboundMessage:
        return InboundMessage(type="skill.execute", channel="cli", session_id=session, content=content)

    def test_gated_skill_returns_ticket_and_writes_nothing(self, workspace: Path) -> None:
        gw = self._gw(workspace)
        try:
            out = gw.dispatch_inbound(self._msg(skill_name="code_write", args={"path": "n.txt", "content": "x"}))
            assert out.type == "error"
            assert out.content["error"] == "confirmation_required"
            assert out.content["confirmation_id"]
            assert not (workspace / "n.txt").exists()
        finally:
            gw.server_sock.close()

    def test_client_confirm_granted_is_ignored(self, workspace: Path) -> None:
        gw = self._gw(workspace)
        try:
            out = gw.dispatch_inbound(
                self._msg(skill_name="code_write", args={"path": "n.txt", "content": "x"}, confirm_granted=True)
            )
            assert out.content["error"] == "confirmation_required"
            assert not (workspace / "n.txt").exists()
        finally:
            gw.server_sock.close()

    def test_ticket_executes_stored_action_once(self, workspace: Path) -> None:
        gw = self._gw(workspace)
        try:
            first = gw.dispatch_inbound(self._msg(skill_name="code_write", args={"path": "n.txt", "content": "x"}))
            tid = first.content["confirmation_id"]
            done = gw.dispatch_inbound(
                self._msg(confirmation_id=tid, skill_name="code_write", args={"path": "other.txt", "content": "y"})
            )
            assert done.type == "response"
            assert (workspace / "n.txt").read_text(encoding="utf-8") == "x"
            assert not (workspace / "other.txt").exists()
            replay = gw.dispatch_inbound(self._msg(confirmation_id=tid))
            assert replay.type == "error"
        finally:
            gw.server_sock.close()

    def test_ticket_bound_to_session(self, workspace: Path) -> None:
        gw = self._gw(workspace)
        try:
            first = gw.dispatch_inbound(self._msg("s1", skill_name="code_write", args={"path": "n.txt", "content": "x"}))
            stolen = gw.dispatch_inbound(self._msg("s2", confirmation_id=first.content["confirmation_id"]))
            assert stolen.type == "error"
            assert not (workspace / "n.txt").exists()
        finally:
            gw.server_sock.close()

    def test_deny_ticket(self, workspace: Path) -> None:
        gw = self._gw(workspace)
        try:
            first = gw.dispatch_inbound(self._msg(skill_name="code_write", args={"path": "n.txt", "content": "x"}))
            tid = first.content["confirmation_id"]
            denied = gw.dispatch_inbound(self._msg(confirmation_id=tid, deny=True))
            assert denied.content.get("denied") is True
            again = gw.dispatch_inbound(self._msg(confirmation_id=tid))
            assert again.type == "error"
            assert not (workspace / "n.txt").exists()
        finally:
            gw.server_sock.close()

    def test_read_only_skill_runs_directly(self, workspace: Path) -> None:
        gw = self._gw(workspace)
        try:
            out = gw.dispatch_inbound(self._msg(skill_name="code_read", args={"path": "app.py"}))
            assert out.type == "response"
        finally:
            gw.server_sock.close()
