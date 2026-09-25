from __future__ import annotations
import hashlib
from pathlib import Path
from src.retrieval.chunker import chunk_markdown
from src.retrieval.embedder import GeminiEmbedder
from src.retrieval.store import VectorStore

def build_index(
    docs_dir: str,
    embedder: GeminiEmbedder,
    store: VectorStore,
    *,
    batch_size: int = 20,
) -> int:
    """Index seluruh .md dari docs_dir: chunk -> embed -> store.
    Dedup hash per chunk: re-run tidak menduplikasi index.
    """
    seen: set[str] = set()
    total = 0
    pending_texts, pending_chunks = [], []
    
    for path in sorted(Path(docs_dir).glob("**/*.md")):
        md = path.read_text(encoding="utf-8")
        for chunk in chunk_markdown(md, source=path.name):
            digest = hashlib.sha1(chunk.text.encode()).hexdigest()
            if digest in seen:
                continue  # dedup konten identik
            seen.add(digest)
            pending_chunks.append(chunk)
            pending_texts.append(chunk.text)
            
            if len(pending_texts) == batch_size:
                total += _flush(pending_chunks, pending_texts,
                                embedder, store)
                pending_chunks, pending_texts = [], []
                
    if pending_texts:
        total += _flush(pending_chunks, pending_texts,
                        embedder, store)
    return total

def _flush(chunks, texts, embedder, store) -> int:
    vectors = embedder.embed_documents(texts)
    store.add(chunks, vectors)
    return len(chunks)
