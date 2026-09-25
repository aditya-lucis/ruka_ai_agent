from __future__ import annotations
import json
import sqlite3
from dataclasses import dataclass
import numpy as np
from src.retrieval.chunker import Chunk

@dataclass
class ScoredChunk:
    chunk: Chunk
    score: float

class VectorStore:
    """Brute-force cosine top-k — jujur untuk korpus < 50 ribu chunk.
    PART I bekerja di sini: batch_cosine atas matriks (N, d).
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
        rows = [(c.text, c.source, c.heading,
                 np.asarray(v, dtype=np.float32).tobytes())
                for c, v in zip(chunks, vectors)]
        self.conn.executemany(
            "INSERT INTO vectors (text, source, heading, vec) "
            "VALUES (?,?,?,?)", rows)
        self.conn.commit()

    def search(self, query_vec: list[float], *, top_k: int = 5,
               min_score: float = 0.30) -> list[ScoredChunk]:
        q = np.asarray(query_vec, dtype=np.float32)
        qn = q / (np.linalg.norm(q) + 1e-12)
        out: list[ScoredChunk] = []
        for rid, text, source, heading, blob in self.conn.execute(
                "SELECT id, text, source, heading, vec FROM vectors"):
            v = np.frombuffer(blob, dtype=np.float32)
            vn = v / (np.linalg.norm(v) + 1e-12)
            score = float(qn @ vn)
            if score >= min_score:
                out.append(ScoredChunk(Chunk(text, source, heading), score))
        out.sort(key=lambda s: s.score, reverse=True)
        return out[:top_k]
