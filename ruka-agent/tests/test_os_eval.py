# -*- coding: utf-8 -*-
"""Test Suite for Boss 9 Desktop Companion Evaluator."""

from __future__ import annotations

import pytest
from src.os_companion.os_eval import DesktopCompanionEvaluator


def test_boss_9_desktop_companion_evaluation():
    evaluator = DesktopCompanionEvaluator()
    results = evaluator.evaluate_boss_9_gates()

    assert results["overall_verdict"] is True
    assert results["total_passed"] >= 7
    assert results["required_gates_passed"] is True
    assert results["acceptance_scenarios_passed"] == "30/30"

    # Verify gates 1, 5, 8 (mandatory gates)
    gate_map = {g["gate"]: g for g in results["gates"]}
    assert gate_map[1]["passed"] is True
    assert gate_map[5]["passed"] is True
    assert gate_map[8]["passed"] is True
