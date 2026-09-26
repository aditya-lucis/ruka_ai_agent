# -*- coding: utf-8 -*-
"""Protocols for the vector engine — provider independence by contract.
The engine never imports a concrete embedding vendor here. Any object
satisfying these protocols can be plugged in: the Gemini provider, the
deterministic offline provider used by tests, or a future local model.
"""
from __future__ import annotations
from typing import Protocol, Sequence
from .types import Document

class EmbeddingProvider(Protocol):
    """Turns text into fixed-dimension vectors.
    A provider must be deterministic for identical input, must expose
    ``dimension``, and must raise (not return junk) on empty input.
    """
    dimension: int
    def embed_documents(self, texts: Sequence[str]) -> list[list[float]]:
        """Embed corpus-side texts (RETRIEVAL_DOCUMENT semantics)."""
        ...
    def embed_query(self, text: str) -> list[float]:
        """Embed the query-side text (RETRIEVAL_QUERY semantics)."""
        ...

class VectorStore(Protocol):
    """Persistence + search contract for the vector space."""
    def add(self, documents: Sequence[Document],
            vectors: Sequence[Sequence[float]]) -> None: ...
    def search(self, query_vector: Sequence[float], top_k: int,
               metadata_filter: dict | None = None
               ) -> list[tuple[Document, float]]: ...
