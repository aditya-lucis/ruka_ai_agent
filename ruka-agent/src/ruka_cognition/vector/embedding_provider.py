# -*- coding: utf-8 -*-
"""Embedding providers: Gemini (cloud) and HashedNGram (offline).
Provider independence is the whole point of this module: the vector
engine, the context engine, and the tool intelligence layer receive an
``EmbeddingProvider`` and never learn which vendor produced vectors.
- ``GeminiEmbeddingProvider`` — DOC-VERIFIED surface: uses
  ``client.models.embed_content`` with ``types.EmbedContentConfig``
  (task_type RETRIEVAL_DOCUMENT / RETRIEVAL_QUERY, output_dimensionality),
  the path verified against official docs and runtime-checked on
  google-genai 2.22.0 during Patch Edition 1.1. The import is lazy so a
  machine without the SDK can still use every other subsystem.
- ``HashedNGramEmbeddingProvider`` — deterministic, dependency-free
  feature hashing of character 3-grams into a fixed dimension. Not a
  semantic model: it exists so tests, demos, and CI run offline with
  reproducible vectors.
"""
from __future__ import annotations
import hashlib
from typing import Sequence

class EmbeddingError(RuntimeError):
    """Raised when a provider cannot produce a valid embedding."""

def _require_non_empty(texts: Sequence[str]) -> None:
    if len(texts) == 0:
        raise EmbeddingError("empty input: nothing to embed")
    for t in texts:
        if not t or not t.strip():
            raise EmbeddingError("empty or whitespace-only text cannot be embedded")

class GeminiEmbeddingProvider:
    """Cloud provider over ``google-genai`` (lazy import).
    The API key comes from the process environment (loaded by the
    project's configuration layer, never hardcoded). ``model`` defaults
    to the text embedding model documented as GA in September 2026.
    """
    dimension: int
    def __init__(self, model: str = "gemini-embedding-001",
                 output_dimensionality: int = 768,
                 api_key: str | None = None) -> None:
        try:
            from google import genai
            from google.genai import types
        except ImportError as exc: # pragma: no cover - environment guard
            raise EmbeddingError(
                "google-genai is not installed: pip install google-genai"
            ) from exc
        self._types = types
        self._client = genai.Client(api_key=api_key) if api_key else genai.Client()
        self._model = model
        self.dimension = int(output_dimensionality)

    def _embed(self, texts: Sequence[str], task_type: str) -> list[list[float]]:
        _require_non_empty(texts)
        try:
            result = self._client.models.embed_content(
                model=self._model,
                contents=list(texts),
                config=self._types.EmbedContentConfig(
                    task_type=task_type,
                    output_dimensionality=self.dimension,
                ),
            )
        except Exception as exc:
            raise EmbeddingError(f"embed_content failed: {exc}") from exc
        
        vectors = [list(map(float, e.values)) for e in result.embeddings]
        for v in vectors:
            if len(v) != self.dimension:
                raise EmbeddingError(
                    f"provider returned {len(v)} dims, expected {self.dimension}"
                )
        return vectors

    def embed_documents(self, texts: Sequence[str]) -> list[list[float]]:
        return self._embed(texts, "RETRIEVAL_DOCUMENT")

    def embed_query(self, text: str) -> list[float]:
        return self._embed([text], "RETRIEVAL_QUERY")[0]

class HashedNGramEmbeddingProvider:
    """Deterministic offline provider (feature hashing of char 3-grams).
    Same text always yields the same vector; different texts collide
    rarely thanks to signed hashing. Useful for tests, demos, and any
    environment where "semantic" quality is secondary to reproducibility.
    """
    def __init__(self, dimension: int = 512, norm: bool = True) -> None:
        if dimension < 8:
            raise ValueError("dimension must be >= 8")
        self.dimension = int(dimension)
        self._norm = norm

    def _vector(self, text: str) -> list[float]:
        v = [0.0] * self.dimension
        padded = f" {text.strip().lower()} "
        for i in range(len(padded) - 2):
            gram = padded[i:i + 3].encode("utf-8")
            h = int.from_bytes(hashlib.md5(gram).digest()[:8], "big")
            idx = h % self.dimension
            sign = 1.0 if (h >> 63) & 1 == 0 else -1.0
            v[idx] += sign * 1.0
        if self._norm:
            sq = sum(x * x for x in v)
            if sq > 0.0:
                inv = (sq ** -0.5)
                v = [x * inv for x in v]
        return v

    def embed_documents(self, texts: Sequence[str]) -> list[list[float]]:
        _require_non_empty(texts)
        return [self._vector(t) for t in texts]

    def embed_query(self, text: str) -> list[float]:
        _require_non_empty([text])
        return self._vector(text)
