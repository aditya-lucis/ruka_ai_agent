# -*- coding: utf-8 -*-
"""Test Suite for Boss 11: PROJECT NOCTIS Final Acceptance."""

from __future__ import annotations

import pytest
from src.noctis_final_eval import ProjectNoctisFinalEvaluator


def test_boss_11_final_acceptance_evaluation():
    evaluator = ProjectNoctisFinalEvaluator()
    results = evaluator.evaluate_final_system()

    assert results["overall_verdict"] is True
    assert results["total_passed"] >= 8
    assert results["required_gates_passed"] is True

    # Gates 1, 5, and 7 are mandatory
    gate_map = {g["gate"]: g for g in results["gates"]}
    assert gate_map[1]["passed"] is True
    assert gate_map[5]["passed"] is True
    assert gate_map[7]["passed"] is True
