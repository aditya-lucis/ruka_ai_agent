# -*- coding: utf-8 -*-
"""Context Relevance Engine — what deserves a slot in the context window.
   Score = w1*similarity + w2*recency + w3*importance
           + w4*task_relevance + w5*source_reliability
Every factor is squashed into [0, 1] *before* the weighted sum: raw
scales are incomparable (a cosine of 0.83, an age of 4 hours, and an
importance of 7-on-10 must not be added as numbers). Weights are
validated to be non-negative and sum to 1, so the final score also
lives in [0, 1] and thresholds mean the same thing across deployments.
"""
from __future__ import annotations
import math
from dataclasses import dataclass, field
from typing import Mapping, Sequence

_EPS = 1e-12

class RelevanceConfigError(ValueError):
    """Invalid weights or floors — configuration must fail fast."""

def _clamp01(x: float) -> float:
    return 0.0 if x < 0.0 else (1.0 if x > 1.0 else x)

@dataclass(frozen=True)
class ContextCandidate:
    """One memory/knowledge item competing for context budget.
    Factors are pre-normalized by the caller (each producer knows its
    own scale); ``same_topic_key`` marks items that make claims about
    the same entity/fact so conflicts can be detected.
    """
    item_id: str
    text: str
    similarity: float           # 0..1 vs current query/goal
    recency: float              # 0..1 (1 = fresh)
    importance: float           # 0..1 (user mark or heuristic)
    task_relevance: float       # 0..1 vs active task description
    source_reliability: float   # 0..1 (provenance trust)
    same_topic_key: str | None = None
    metadata: Mapping = field(default_factory=dict)

@dataclass(frozen=True)
class ScoredCandidate:
    item_id: str
    text: str
    score: float
    factors: tuple[float, ...]
    pinned: bool = False

class ContextRelevanceEngine:
    """Deterministic multi-factor scorer with pins, floors, conflicts."""
    FACTORS = ("similarity", "recency", "importance",
               "task_relevance", "source_reliability")

    def __init__(self, weights: Sequence[float] | None = None,
                 importance_floor: float = 0.9,
                 recency_ceiling: float = 0.85) -> None:
        if weights is None:
            weights = (0.35, 0.15, 0.20, 0.20, 0.10)
        w = tuple(float(x) for x in weights)
        if len(w) != 5:
            raise RelevanceConfigError("need exactly 5 weights (one per factor)")
        if any(x < 0 for x in w):
            raise RelevanceConfigError("weights must be non-negative")
        total = sum(w)
        if total <= 0:
            raise RelevanceConfigError("weights must not sum to zero")
        self._w = tuple(x / total for x in w)
        self.importance_floor = _clamp01(importance_floor)
        self.recency_ceiling = _clamp01(recency_ceiling)

    def score(self, candidates: Sequence[ContextCandidate],
              pinned_ids: Sequence[str] = ()
              ) -> list[ScoredCandidate]:
        """Score, sort, and pin: important context must not evaporate."""
        pinned = set(pinned_ids)
        out: list[ScoredCandidate] = []
        for c in candidates:
            factors = (
                _clamp01(c.similarity), _clamp01(c.recency),
                _clamp01(c.importance), _clamp01(c.task_relevance),
                _clamp01(c.source_reliability),
            )
            # recency anti-bias: fresh-but-shallow cannot rule alone
            eff_recency = min(factors[1], self.recency_ceiling)
            eff = (factors[0], eff_recency) + factors[2:]
            
            score = sum(wi * fi for wi, fi in zip(self._w, eff))
            
            if factors[2] >= self.importance_floor and c.item_id in pinned:
                score = max(score, self.importance_floor)
                is_pinned = True
            else:
                is_pinned = False
                
            out.append(ScoredCandidate(item_id=c.item_id, text=c.text,
                                       score=round(score, 6),
                                       factors=factors, pinned=is_pinned))
        out.sort(key=lambda s: (s.pinned, s.score), reverse=True)
        return out

    def detect_conflicts(self, scored: Sequence[ScoredCandidate],
                         keys: Mapping[str, str],
                         disagree: Mapping[str, bool]
                         ) -> list[tuple[float, str, str, str]]:
        """Flag high-scoring pairs that claim the same topic and disagree.
        ``keys`` maps item_id -> topic key; ``disagree`` maps
        item_id-pair "a|b" -> True when the two items contradict (the
        producer decides what 'contradiction' means — label mismatch,
        opposite polarity, different value for the same field).
        Returns pairs sorted by combined score: the pairs a human (or
        the LLM) should look at first.
        """
        pairs: list[tuple[float, str, str, str]] = []
        by_id = {s.item_id: s for s in scored}
        for a in scored:
            ka = keys.get(a.item_id)
            if not ka:
                continue
            for b in scored:
                if b.item_id <= a.item_id:
                    continue
                if keys.get(b.item_id) != ka:
                    continue
                if not disagree.get(f"{a.item_id}|{b.item_id}", False):
                    continue
                pairs.append((a.score + b.score, a.item_id, b.item_id, ka))
        pairs.sort(reverse=True)
        return [(a, b, k) for _, a, b, k in pairs]

def recency_from_timestamp(timestamp: float, now: float,
                           half_life_seconds: float) -> float:
    """0..1 recency factor from an exponential half-life decay."""
    if half_life_seconds <= 0:
        raise RelevanceConfigError("half_life_seconds must be positive")
    age = max(now - timestamp, 0.0)
    return math.pow(0.5, age / half_life_seconds)
