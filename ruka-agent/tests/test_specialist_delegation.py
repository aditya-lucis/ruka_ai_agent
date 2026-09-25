# -*- coding: utf-8 -*-
import pytest
from pydantic import ValidationError
from src.agent.delegation import (
    RESEARCH_SPEC,
    SpecialistSpec,
    SpecialistVerdict,
    as_tool_schema,
)
from src.capability.registry import Permission


def test_schema_shape_is_ordinary_tool():
    schema = as_tool_schema(RESEARCH_SPEC)
    assert schema["type"] == "function"
    assert schema["name"] == "specialist_research"
    assert schema["parameters"]["required"] == ["task"]


def test_verdict_contract_validates():
    v = SpecialistVerdict(
        specialist="research",
        summary="tiga sumber konsisten",
        key_findings=["A", "B"],
        confidence=0.9,
    )
    with pytest.raises((ValueError, ValidationError)):
        SpecialistVerdict(specialist="x", summary="s", confidence=1.7)          # di luar 0..1


def test_research_permissions_are_minimal():
    assert Permission.EXECUTE not in RESEARCH_SPEC.allowed_permissions
    assert Permission.DESTRUCTIVE not in RESEARCH_SPEC.allowed_permissions


def test_budget_share_is_fraction():
    assert 0.0 < RESEARCH_SPEC.share_of_budget < 1.0   # turunan, bukan baru
