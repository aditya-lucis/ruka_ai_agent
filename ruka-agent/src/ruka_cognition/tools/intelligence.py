# -*- coding: utf-8 -*-
"""Tool Intelligence — mathematical pre-ranking before the LLM chooses.
Pipeline (Part IV of the book):
 user goal -> TaskProfile -> relevance scoring over ToolCatalog
 -> top-k candidates -> LLM decision -> permission check
 -> execution -> observation
The scorer is deliberately deterministic and explainable: the same task
and catalog always yield the same ranking, and every score decomposes
into printed reasons. The LLM keeps final selection authority; the
math narrows the field, saves context tokens, and gives tests
something to assert against.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Mapping, Sequence
import numpy as np

from ..vector.interfaces import EmbeddingProvider
from ..vector.similarity import normalize

@dataclass(frozen=True)
class ToolSpec:
    """Machine-readable tool capability card.
    ``capabilities`` are abstract verbs ("read_file", "http_get");
    ``risk`` in 0..1 (0 = read-only, 1 = irreversible side effect);
    ``cost`` in 0..1 relative to latency/token budget of peers.
    """
    name: str
    description: str
    capabilities: tuple[str, ...] = ()
    risk: float = 0.0
    cost: float = 0.1
    keywords: tuple[str, ...] = ()
    metadata: Mapping = field(default_factory=dict)

@dataclass(frozen=True)
class TaskProfile:
    """The request side of tool selection."""
    goal_text: str
    required_capabilities: tuple[str, ...] = ()

@dataclass(frozen=True)
class ToolCandidate:
    tool: ToolSpec
    relevance: float            # semantic similarity component (0..1)
    capability_match: float     # fraction of required capabilities covered
    penalty: float              # cost + risk adjustment (>= 0)
    score: float                # final pre-ranking score
    reasons: tuple[str, ...] = ()

class ToolIntelligence:
    """Deterministic tool pre-ranker over an embedding provider."""
    def __init__(self, provider: EmbeddingProvider,
                 w_relevance: float = 0.6, w_capability: float = 0.4,
                 risk_penalty: float = 0.5, cost_penalty: float = 0.25,
                 candidate_floor: float = 0.05) -> None:
        if w_relevance + w_capability <= 0:
            raise ValueError("weights must be positive")
        self._provider = provider
        self._w_rel = w_relevance / (w_relevance + w_capability)
        self._w_cap = w_capability / (w_relevance + w_capability)
        self._risk_pen = float(risk_penalty)
        self._cost_pen = float(cost_penalty)
        self._floor = float(candidate_floor)

    def _tool_text(self, t: ToolSpec) -> str:
        kw = " ".join(t.keywords)
        return f"{t.name}: {t.description} {kw}".strip()

    def rank(self, task: TaskProfile, catalog: Sequence[ToolSpec],
             top_k: int = 5) -> list[ToolCandidate]:
        """Rank tools for a task; returns at most ``top_k`` candidates."""
        if top_k <= 0:
            raise ValueError("top_k must be positive")
        if not catalog:
            return []
            
        task_vec = normalize(np.asarray(
            self._provider.embed_query(task.goal_text), dtype=np.float64))[0]
        tool_vecs = normalize(np.asarray(
            self._provider.embed_documents(
                [self._tool_text(t) for t in catalog]), dtype=np.float64))
        sims = (tool_vecs @ task_vec).tolist()
        required = set(task.required_capabilities)
        
        out: list[ToolCandidate] = []
        for t, s in zip(catalog, sims):
            rel = max(float(s), 0.0)
            if required:
                covered = len(required.intersection(t.capabilities)) / len(required)
            else:
                covered = 0.5   # neutral when task states no capability
            
            penalty = (self._risk_pen * max(t.risk, 0.0)
                       + self._cost_pen * max(t.cost, 0.0))
            score = self._w_rel * rel + self._w_cap * covered - penalty
            reasons = (f"relevance={rel:.3f}",
                       f"capability_match={covered:.2f}",
                       f"penalty={penalty:.3f}")
            out.append(ToolCandidate(tool=t, relevance=rel,
                                     capability_match=covered,
                                     penalty=penalty,
                                     score=round(score, 6),
                                     reasons=reasons))
                                     
        out.sort(key=lambda c: c.score, reverse=True)
        return [c for c in out[:top_k] if c.score > self._floor] or out[:1]
