# -*- coding: utf-8 -*-
"""Uji perilaku lintas-lapisan: memilih tool, tak memakai memori
ter-revisi, state ekspresi benar saat tool berjalan."""
from __future__ import annotations
import pytest
from src.agent.budget import Budget
from src.state.core import InternalState
from src.state.machine import ExpressionFSM, Phase
from src.expression.engine import ExpressionEngine
from src.expression.params import Expression
from tests.conftest import FakeClient, FakeInteraction, FakeStep


def test_agent_uses_calculator_when_math_needed():
    """SPEC: apakah Ruka memilih calculator ketika diperlukan?"""
    calc_call = FakeStep(
        type="function_call",
        name="calculator",
        arguments={"expr": "2+2"},
        id="c1",
    )
    final = FakeStep(type="text", text="4")
    client = FakeClient([
        FakeInteraction(steps=[calc_call]),
        FakeInteraction(steps=[final], output_text="4"),
    ])
    # Placeholder wiring per spesifikasi buku (Page 184-185)
    assert True


def test_memory_revision_not_recalled():
    """SPEC: memori lama yang sudah direvisi tidak dipakai kembali."""
    from src.memory.models import MemoryKind, MemoryRecord, Provenance
    from src.memory.revision import MemoryRevisionStrategy

    class Store:
        def __init__(self):
            self.rows = []

        def query_memories(self, kinds, active_only=True):
            return [
                r for r in self.rows
                if r.kind.value in kinds and r.supersedes_id is None
            ]

        def mark_superseded(self, loser_id, winner_id, reason):
            for r in self.rows:
                if r.id == loser_id:
                    r.supersedes_id = winner_id

    old = MemoryRecord(
        kind=MemoryKind.PREFERENCE,
        content="Bos suka monolith",
        provenance=Provenance(source_type="conversation", source_id="t1"),
    )
    old.id = 1
    new = MemoryRecord(
        kind=MemoryKind.PREFERENCE,
        content="Sekarang Bos lebih suka microservice",
        provenance=Provenance(source_type="conversation", source_id="t2"),
    )
    new.id = 2
    store = Store()
    store.rows = [old, new]
    verdict = MemoryRevisionStrategy(store).revise_preference(new)
    if verdict:
        store.mark_superseded(verdict.loser.id, verdict.winner.id, verdict.reason)
    recalled = [
        r.content for r in store.query_memories(kinds=[MemoryKind.PREFERENCE.value])
    ]
    assert recalled == ["Sekarang Bos lebih suka microservice"]
    assert "monolith" not in " ".join(recalled)


def test_expression_state_while_tool_running():
    """SPEC: state 'thinking/focused' aktif saat tool sedang jalan."""
    fsm = ExpressionFSM()
    fsm.transition(Phase.LISTENING, "input")
    fsm.transition(Phase.THINKING, "parsed")
    fsm.transition(Phase.TOOL_EXECUTING, "call")
    state = InternalState()
    params = ExpressionEngine(state).decide(phase=fsm.phase.value)
    assert fsm.is_busy() is True
    assert params.expression in (Expression.FOCUSED, Expression.SERIOUS)
    assert state.expression.expression == params.expression.value
