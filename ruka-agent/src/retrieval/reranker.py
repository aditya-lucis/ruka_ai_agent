"""Hybrid retrieval + rerank — dua sinyal + fitur pendalaman."""
from __future__ import annotations
import math
from collections import Counter
from dataclasses import dataclass

@dataclass(frozen=True)
class Candidate:
    chunk_id: str
    text: str
    heading: str
    source_path: str
    dense: float                      # cosine 0..1 (dari embedder Vol I)
    stale_days: float = 0.0           # umur sumber (mtime)

def bm25_lite(query_tokens: list[str], doc_tokens: list[str],
              avg_len: float, k1: float = 1.5, b: float = 0.75) -> float:
    """BM25 inti untuk korpus kecil (tanpa IDF global — cukup untuk
    meranking kandidat yang sudah terseleksi)."""
    tf = Counter(doc_tokens)
    score = 0.0
    norm = k1 * (1 - b + b * len(doc_tokens) / max(1.0, avg_len))
    for t in query_tokens:
        if t in tf:
            score += (tf[t] * (k1 + 1)) / (tf[t] + norm)
    return score

def rerank(query: str, candidates: list[Candidate],
           top_n: int = 5) -> list[tuple[float, Candidate]]:
    """Gabung dense + lexical + freshness + heading − dup."""
    if not candidates:
        return []
    q_tokens = query.lower().split()
    avg_len = sum(len(c.text.split()) for c in candidates) / len(candidates)
    lexical = [bm25_lite(q_tokens, c.text.lower().split(), avg_len)
               for c in candidates]
    max_lex = max(lexical) or 1.0
    seen_texts: set[str] = set()
    scored: list[tuple[float, Candidate]] = []
    for c, lex in zip(candidates, lexical):
        freshness = 1.0 / (1.0 + c.stale_days / 180.0)   # half-life 6 bulan
        heading_depth = 1.0 if c.heading else 0.5
        dup = c.text[:80] in seen_texts
        seen_texts.add(c.text[:80])
        final = (0.55 * c.dense
                 + 0.25 * (lex / max_lex)
                 + 0.10 * freshness
                 + 0.10 * heading_depth
                 - (0.15 if dup else 0.0))
        scored.append((round(final, 4), c))
    scored.sort(key=lambda pair: -pair[0])
    return scored[:top_n]
