from __future__ import annotations
from google import genai
from google.genai import types

class GeminiEmbedder:
    """Embedding dokumen & query — task_type berbeda per fase.
    gemini-embedding-001 + output_dimensionality 768:
    dimensi penuh untuk dokumen (kualitas), opsi reduksi untuk
    query bila anggaran ketat.
    """
    def __init__(self, client: genai.Client,
                 model: str = "gemini-embedding-001"):
        self.client = client
        self.model = model

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        res = self.client.models.embed_content(
            model=self.model,
            contents=texts,
            config=types.EmbedContentConfig(
                task_type="RETRIEVAL_DOCUMENT",
                output_dimensionality=768,
            ),
        )
        return [e.values for e in res.embeddings]

    def embed_query(self, query: str) -> list[float]:
        res = self.client.models.embed_content(
            model=self.model,
            contents=[query],
            config=types.EmbedContentConfig(
                task_type="RETRIEVAL_QUERY",
                output_dimensionality=768,
            ),
        )
        return res.embeddings[0].values
