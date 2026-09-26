# -*- coding: utf-8 -*-
"""Exact in-memory vector index with metadata filtering.
Design decisions (Part II of the book discusses each):
- vectors are L2-normalized at insert time, so cosine similarity
  reduces to a single matrix-vector product — fast and numerically
  consistent;
- metadata filtering happens *before* scoring, so filtered-out
  documents never influence the ranking;
- the store is append-only; ``add`` validates shapes and dimension.
Approximate search (HNSW, IVF) is deliberately out of scope: the
exact path is the correctness baseline every ANN must beat-or-match.
"""
from __future__ import annotations
from typing import Sequence
import numpy as np

from .interfaces import EmbeddingProvider
from .similarity import normalize
from .types import Document, ScoredMatch, check_kind

_EPS = 1e-9

class VectorIndex:
    """Brute-force exact top-k over normalized vectors."""
    def __init__(self, provider: EmbeddingProvider) -> None:
        self._provider = provider
        self.dimension = provider.dimension
        self._ids: list[str] = []
        self._docs: list[Document] = []
        self._matrix = np.zeros((0, self.dimension), dtype=np.float64)

    def __len__(self) -> int:
        return len(self._docs)

    # ------------------------------------------------------------- add
    def add_documents(self, documents: Sequence[Document]) -> int:
        """Embed + insert documents; returns number added."""
        if not documents:
            return 0
        for d in documents:
            check_kind(d.kind)
        
        vectors = self._provider.embed_documents([d.text for d in documents])
        
        for v in vectors:
            if len(v) != self.dimension:
                raise ValueError(
                    f"provider returned dim {len(v)}, index expects {self.dimension}"
                )
        
        batch = normalize(np.asarray(vectors, dtype=np.float64))
        if not np.isfinite(batch).all():
            raise ValueError("embedding contains NaN/inf — refusing to index")
            
        self._matrix = np.vstack([self._matrix, batch]) if len(self) else batch
        for d in documents:
            self._ids.append(d.doc_id)
            self._docs.append(d)
        return len(documents)

    # ---------------------------------------------------------- search
    def _filtered_indices(self, metadata_filter: dict | None) -> list[int]:
        """Filter before scoring. The document's ``kind`` field is
        matched as if it were metadata (a real field, not a dict entry
        — the distinction leaked once and cost us a vacuous test)."""
        if not metadata_filter:
            return list(range(len(self._docs)))
        out = []
        for i, doc in enumerate(self._docs):
            record = {**doc.metadata, "kind": doc.kind}
            if all(record.get(k) == v for k, v in metadata_filter.items()):
                out.append(i)
        return out

    def search(self, query_text: str, top_k: int = 5,
               metadata_filter: dict | None = None
               ) -> list[ScoredMatch]:
        """Return top-k matches sorted by cosine similarity (desc)."""
        if top_k <= 0:
            raise ValueError("top_k must be positive")
        if len(self) == 0:
            return []
            
        idx = self._filtered_indices(metadata_filter)
        if not idx:
            return []
            
        q = normalize(np.asarray(self._provider.embed_query(query_text),
                                 dtype=np.float64))[0]
        
        sims = self._matrix[idx] @ q # cosine: unit norms
        k = min(top_k, len(idx))
        order = np.argsort(-sims)[:k]
        
        out: list[ScoredMatch] = []
        for pos in order:
            i = idx[int(pos)]
            s = float(sims[int(pos)])
            if s < _EPS: # orthogonal junk should not masquerade as a hit
                continue
            out.append(ScoredMatch(document=self._docs[i], similarity=s, score=s))
        return out

    def deduplicate(self, threshold: float = 0.98) -> int:
        """Drop near-duplicate documents; returns how many were removed."""
        if len(self) < 2:
            return 0
        keep: list[int] = []
        removed = 0
        for i in range(len(self)):
            duplicate = False
            for j in keep:
                if float(self._matrix[i] @ self._matrix[j]) >= threshold:
                    duplicate = True
                    removed += 1
                    break
            if not duplicate:
                keep.append(i)
        
        self._ids = [self._ids[i] for i in keep]
        self._docs = [self._docs[i] for i in keep]
        self._matrix = self._matrix[np.array(keep, dtype=int)]
        return removed
