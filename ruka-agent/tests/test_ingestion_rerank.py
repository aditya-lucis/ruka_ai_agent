from pathlib import Path
import pytest
from src.retrieval.ingestion import (MarkdownParser, chunk_quality,
                                     make_chunks, parser_for)
from src.retrieval.reranker import Candidate, rerank

MD = """# RUKA Guide
## Setup
Instal dengan pip install google-genai lalu set GEMINI_API_KEY.
## Tools
Tools dideklarasikan sebagai JSON schema. Nomor error 429 berarti
rate limit; retry dengan exponential backoff dan jitter.
"""

class FakeStore:
    def __init__(self):
        self.doc_hashes: dict[str, str] = {}
        self.chunks: list = []

    def get_doc_hash(self, p):
        return self.doc_hashes.get(p)

    def set_doc_hash(self, p, h, mtime):
        self.doc_hashes[p] = h

    def drop_chunks(self, p):
        n = len(self.chunks)
        self.chunks = [c for c in self.chunks if c.source_path != p]
        return n - len(self.chunks)

    def upsert_chunk(self, c):
        self.chunks.append(c)

def test_markdown_parser_splits_by_heading(tmp_path: Path):
    p = tmp_path / "guide.md"
    p.write_text(MD, encoding="utf-8")
    doc = MarkdownParser().parse(p)
    assert len(doc.blocks) == 2
    assert doc.blocks[0].heading == "Setup"
    assert doc.doc_hash and len(doc.doc_hash) == 16

def test_incremental_second_run_touches_nothing(tmp_path: Path):
    from src.retrieval.ingestion import ingest
    (tmp_path / "a.md").write_text(MD, encoding="utf-8")
    store = FakeStore()
    first = ingest(store, tmp_path)
    second = ingest(store, tmp_path)
    assert first["updated"] == 1 and second["updated"] == 0
    assert second["unchanged"] == first["scanned"]

def test_chunk_quality_penalizes_junk():
    assert chunk_quality("x" * 20) < 0.3
    good = ("Kalimat penuh dengan struktur. Dan lagi. Dan lagi. "
            "Sampai cukup panjang untuk dianggap sehat. " * 3)
    assert chunk_quality(good) > 0.6

def test_rerank_prefers_exact_error_code_and_fresh():
    q = "error 429 rate limit retry"
    hit = Candidate("c1", "Nomor error 429 berarti rate limit; retry "
                          "dengan exponential backoff dan jitter.",
                    "Tools", "docs/errors.md", dense=0.42, stale_days=2)
    miss = Candidate("c2", "Instal dengan pip lalu set kunci API.",
                     "Setup", "docs/setup.md", dense=0.46, stale_days=400)
    out = rerank(q, [miss, hit], top_n=2)
    assert out[0][1].chunk_id == "c1"      # lexical + fresh menang
    assert out[0][0] > out[1][0]
