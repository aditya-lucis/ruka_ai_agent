# -*- coding: utf-8 -*-
"""Test Suite for Boss 10 Crimson Astral Forge."""

from __future__ import annotations

import pytest
from src.forge.forge_eval import CrimsonForgeEvaluator


def test_boss_10_crimson_forge_evaluation():
    evaluator = CrimsonForgeEvaluator()
    results = evaluator.evaluate_all_gates()

    assert results["overall_verdict"] is True
    assert results["total_passed"] >= 7
    assert results["required_gates_passed"] is True

    # Gates 6 and 7 are mandatory
    gate_map = {g["gate"]: g for g in results["gates"]}
    assert gate_map[6]["passed"] is True
    assert gate_map[7]["passed"] is True
