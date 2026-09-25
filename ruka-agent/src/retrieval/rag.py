from __future__ import annotations
from src.llm.gemini_client import GeminiClient
from src.retrieval.embedder import GeminiEmbedder
from src.retrieval.store import VectorStore, ScoredChunk

class RAGPipeline:
    def __init__(self, embedder: GeminiEmbedder,
                 store: VectorStore, client: GeminiClient):
        self.embedder = embedder
        self.store = store
        self.client = client

    def retrieve(self, query: str, *, top_k: int = 5) -> list[ScoredChunk]:
        qv = self.embedder.embed_query(query)
        hits = self.store.search(qv, top_k=top_k * 2)
        return self._rerank(query, hits)[:top_k]

    def answer(self, query: str) -> str:
        hits = self.retrieve(query)
        if not hits:
            return ("[RUKA-RAG] Tidak ada sumber relevan ditemukan "
                    "di knowledge base — saya tidak akan mengarang.")
        
        context = "\n\n".join(
            f"[Sumber {i+1}: {h.chunk.source}]\n{h.chunk.text}"
            for i, h in enumerate(hits)
        )
        
        prompt = (
            "Jawab HANYA berdasar konteks berikut. Bila konteks "
            "tidak memuat jawaban, katakan itu secara eksplisit.\n\n"
            f"KONTEKS:\n{context}\n\nPERTANYAAN: {query}"
        )
        return self.client.complete(prompt, temperature=0.1)

    def _rerank(self, query: str, hits: list[ScoredChunk]) -> list[ScoredChunk]:
        """Rerank cross-encoder ringan: model menilai ulang kandidat."""
        if len(hits) <= 3:
            return hits
            
        pairs = "\n".join(
            f"[{i}] {h.chunk.text[:300]}" for i, h in enumerate(hits)
        )
        
        resp = self.client.complete(
            f"Nilai relevansi 0-100 tiap kandidat untuk pertanyaan: "
            f"'{query}'\n{pairs}\n"
            "Balas JSON list skor, contoh: [82, 17, 95]",
            temperature=0.0,
        )
        
        import json
        try:
            scores = json.loads(resp)
            for h, s in zip(hits, scores):
                h.score = 0.5 * h.score + 0.5 * (float(s) / 100.0)
        except (ValueError, TypeError):
            pass  # rerank gagal -> fallback cosine
            
        return sorted(hits, key=lambda h: h.score, reverse=True)
