# -*- coding: utf-8 -*-
import pytest
from src.confidence.model import (
    EpistemicLevel,
    Evidence,
    confidence,
    epistemic_level,
)


def test_identity_fact_is_known():
    e = Evidence(from_identity=True)
    assert epistemic_level(e)[0] is EpistemicLevel.KNOW


def test_strong_evidence_claims_evidence():
    e = Evidence(
        retrieval_top=0.78,
        tool_success=1.0,
        n_sources=3,
        stale_days=12,
    )
    level, c = epistemic_level(e)
    assert level is EpistemicLevel.EVIDENCE and c > 0.8


def test_conflicts_push_to_uncertain():
    e = Evidence(
        retrieval_top=0.60,
        tool_success=1.0,
        n_sources=3,
        n_conflicts=2,
        stale_days=30,
    )
    level, _ = epistemic_level(e)
    assert level is EpistemicLevel.UNCERTAIN


def test_no_evidence_asks_for_more():
    level, c = epistemic_level(Evidence())
    assert level is EpistemicLevel.NEED_INFO and c < 0.05


def test_confidence_bounds_and_penalty():
    strong = Evidence(
        retrieval_top=1.0,
        tool_success=1.0,
        n_sources=1,
        stale_days=0,
    )
    weak = Evidence(
        retrieval_top=0.5,
        tool_success=0.0,
        n_sources=1,
        stale_days=365,
    )
    assert confidence(strong) <= 1.0 and confidence(weak) < 0.3
    # dataclass: bandingkan manual – konflik menurunkan skor
    e2 = Evidence(
        retrieval_top=1.0,
        tool_success=1.0,
        n_sources=2,
        n_conflicts=1,
        stale_days=0,
    )
    assert confidence(e2) < confidence(strong)
