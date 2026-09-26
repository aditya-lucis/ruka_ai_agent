# -*- coding: utf-8 -*-
"""Ranking engine: compose similarity with structured signals.
Retrieval similarity answers "is this text about the same thing?";
ranking answers "does this candidate *deserve* a slot in the context
window". This module implements two composition policies:
- ``RecencyRanker`` — similarity blended with an exponential recency
  decay (the simplest honest version of the context score of Part III);
- ``MMRSelector`` — maximal marginal relevance: trade off relevance
  against redundancy so ten near-copies of one fact do not flood the
  context (diversity for a token-limited budget).
"""
from __future__ import annotations
import math
import time
from dataclasses import dataclass
from typing import Sequence

from .types import ScoredMatch

@dataclass(frozen=True)
class RankedItem:
    match: ScoredMatch
    final_score: float
    reasons: tuple[str, ...]

def recency_factor(timestamp: float, now: float,
                   half_life_seconds: float) -> float:
    """Exponential decay factor in (0, 1].
    ``half_life_seconds`` is the time after which a memory's recency
    component halves. A half-life of a week makes yesterday's memory
    worth ~0.91 and last-month's ~0.36 — recency must inform, never
    dominate, or the agent develops goldfish amnesia for old lessons.
    """
    if half_life_seconds <= 0:
        raise ValueError("half_life_seconds must be positive")
    age = max(now - timestamp, 0.0)
    return math.pow(0.5, age / half_life_seconds)

class RecencyRanker:
    """score = w_sim * similarity + w_rec * decay — both in [0, 1]."""
    def __init__(self, w_similarity: float = 0.7, w_recency: float = 0.3,
                 half_life_seconds: float = 7 * 24 * 3600,
                 now: float | None = None) -> None:
        total = w_similarity + w_recency
        if total <= 0:
            raise ValueError("weights must be positive")
        self._w_sim = w_similarity / total
        self._w_rec = w_recency / total
        self._half_life = half_life_seconds
        self._now = now if now is not None else time.time()

    def rank(self, matches: Sequence[ScoredMatch]) -> list[RankedItem]:
        out: list[RankedItem] = []
        for m in matches:
            ts = float(m.document.metadata.get("timestamp", self._now))
            rec = recency_factor(ts, self._now, self._half_life)
            score = self._w_sim * max(m.similarity, 0.0) + self._w_rec * rec
            out.append(RankedItem(
                match=m, final_score=score,
                reasons=(f"sim={m.similarity:.3f}", f"recency={rec:.3f}"),
            ))
        out.sort(key=lambda r: r.final_score, reverse=True)
        return out

class MMRSelector:
    """Maximal Marginal Relevance (Carbonell & Goldstein, 1998).
    MMR(d) = argmax_{d in R\\S} [ lambda * sim(d, q)
                                 - (1 - lambda) * max_{s in S} sim(d, s) ]
    ``sim`` is the cosine between embeddings; S is the selected set.
    ``lambda=1`` degenerates to pure relevance, ``lambda=0`` to pure
    novelty. The selector needs vectors, so it accepts (match, vector)
    pairs produced by the index.
    """
    def __init__(self, lambda_: float = 0.7) -> None:
        if not 0.0 <= lambda_ <= 1.0:
            raise ValueError("lambda_ must be within [0, 1]")
        self._lambda = lambda_

    def select(self, pairs: Sequence[tuple[ScoredMatch, Sequence[float]]],
               k: int) -> list[RankedItem]:
        if k <= 0:
            return []
        pool = [(m, list(v)) for m, v in pairs]
        selected: list[tuple[ScoredMatch, list[float]]] = []
        report: list[RankedItem] = []
        
        while pool and len(selected) < k:
            best_i, best_val, best_reason = 0, -math.inf, ""
            for i, (m, v) in enumerate(pool):
                rel = max(m.similarity, 0.0)
                redundancy = 0.0
                for _, sv in selected:
                    redundancy = max(redundancy, _cosine(v, sv))
                val = self._lambda * rel - (1.0 - self._lambda) * redundancy
                if val > best_val:
                    best_val, best_i = val, i
                    best_reason = (f"rel={rel:.3f}",
                                   f"redundancy={redundancy:.3f}")
            
            m, v = pool.pop(best_i)
            selected.append((m, v))
            report.append(RankedItem(match=m, final_score=best_val,
                                     reasons=best_reason))
        return report

def _cosine(a: Sequence[float], b: Sequence[float]) -> float:
    dot_ = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a)) or 1e-12
    nb = math.sqrt(sum(x * x for x in b)) or 1e-12
    return dot_ / (na * nb)
