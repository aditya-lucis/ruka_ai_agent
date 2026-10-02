# -*- coding: utf-8 -*-
"""RUKA Retrieval Store — Vector Database via Pure Linear Algebra.

Menggunakan batch_cosine dan Score dari math_foundations untuk
pencarian kesamaan semantik ber-confidence tinggi.
"""
from __future__ import annotations

import sqlite3
from dataclasses import dataclass
import numpy as np

from src.retrieval.chunker import Chunk
from src.math_foundations.types import Score
from src.math_foundations.linear import batch_cosine


@dataclass
class ScoredChunk:
    chunk: Chunk
    score: Score | float


class VectorStore:
    """Brute-force cosine top-k — jujur untuk korpus < 50 ribu chunk.
    Menggunakan batch_cosine atas matriks (N, d) dan mengembalikan Score ber-confidence.
    """
    def __init__(self, dim: int = 768, path: str = "ruka.db"):
        self.dim = dim
        self.conn = sqlite3.connect(path)
        self.conn.executescript(
            "CREATE TABLE IF NOT EXISTS vectors ("
            "id INTEGER PRIMARY KEY AUTOINCREMENT, "
            "text TEXT NOT NULL, source TEXT NOT NULL, "
            "heading TEXT DEFAULT '', vec BLOB NOT NULL)"
        )

    def add(self, chunks: list[Chunk], vectors: list[list[float]]) -> None:
        rows = [
            (
                c.text,
                c.source,
                c.heading,
                np.asarray(v, dtype=np.float32).tobytes(),
            )
            for c, v in zip(chunks, vectors)
        ]
        self.conn.executemany(
            "INSERT INTO vectors (text, source, heading, vec) "
            "VALUES (?,?,?,?)",
            rows,
        )
        self.conn.commit()

    def search(
        self,
        query_vec: list[float],
        *,
        top_k: int = 5,
        min_score: float = 0.30,
    ) -> list[ScoredChunk]:
        rows = list(self.conn.execute("SELECT id, text, source, heading, vec FROM vectors"))
        if not rows:
            return []

        q = np.asarray(query_vec, dtype=np.float32)
        vectors_arr = np.vstack([np.frombuffer(r[4], dtype=np.float32) for r in rows])
        sims = batch_cosine(q, vectors_arr)

        out: list[ScoredChunk] = []
        for i, row in enumerate(rows):
            sim = float(sims[i])
            if sim >= min_score:
                # Confidence dihitung berdasarkan kekuatan sinyal di atas min_score
                margin = max(0.0, sim - min_score)
                max_margin = max(1e-6, 1.0 - min_score)
                conf = min(1.0, 0.5 + 0.5 * (margin / max_margin))
                score_obj = Score(
                    value=round(sim, 4),
                    confidence=round(conf, 4),
                    components={
                        "cosine": round(sim, 4),
                        "heading_depth": 1.0 if row[3] else 0.5,
                    },
                )
                out.append(ScoredChunk(Chunk(row[1], row[2], row[3]), score_obj))

        out.sort(key=lambda s: float(s.score), reverse=True)
        return out[:top_k]
