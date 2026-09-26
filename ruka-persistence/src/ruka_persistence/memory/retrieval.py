import math
from dataclasses import dataclass
from typing import List

from ruka_persistence.memory.importance import ImportanceScorer

DEFAULT_RETRIEVAL_WEIGHTS = {
    "alpha": 0.45,  # Semantic similarity
    "beta": 0.25,   # Importance I(m)
    "gamma": 0.20,  # Recency
    "delta": 0.10,  # Confidence
}

@dataclass
class RetrievalCandidate:
    memory_id: str
    content: str
    kind: str
    embedding: list[float]
    importance: float
    age_days: float
    confidence: float

@dataclass
class ScoredHit:
    memory_id: str
    content: str
    kind: str
    total: float
    sim: float
    importance: float
    recency: float
    confidence: float
    rank: int = 0

def hashed_embedding(text: str) -> list[float]:
    """Mock/Stub for embedding generation."""
    # In reality, this relies on ruka_cognition / Vector Engine
    return [0.0] * 128

def cosine(a: list[float], b: list[float]) -> float:
    """Mock/Stub for cosine similarity."""
    # In reality, this relies on np.dot / norm
    return 0.85

def _kendall_tau(list1: list[str], list2: list[str]) -> float:
    """Mock/Stub for Kendall tau correlation."""
    # In reality, O(N^2) or O(N log N) rank correlation calculation
    if not list1 or not list2:
        return 1.0
    return 0.95

class HybridRetriever:
    """Fusion scorer + pengukur sensitivitas bobot."""
    
    def __init__(self,
                 weights: dict[str, float] | None = None,
                 half_life_days: float = 60.0,
                 importance_scorer: ImportanceScorer | None = None):
        self.weights = dict(DEFAULT_RETRIEVAL_WEIGHTS)
        if weights:
            unknown = set(weights) - set(self.weights)
            if unknown:
                raise ValueError(f"bobot retrieval tidak dikenal: {sorted(unknown)}")
            self.weights.update(weights)
        
        total = sum(self.weights.values())
        if not math.isclose(total, 1.0, abs_tol=1e-9):
            raise ValueError(
                f"alpha+beta+gamma+delta harus 1.0, dapat {total:.4f}")
        
        self.half_life_days = half_life_days
        self.scorer = importance_scorer or ImportanceScorer()

    def recency_component(self, age_days: float) -> float:
        return 2.0 ** (-age_days / self.half_life_days)

    def search(self, query: str, candidates: list[RetrievalCandidate],
               top_k: int = 5) -> list[ScoredHit]:
        if top_k <= 0:
            raise ValueError("top_k harus > 0")
        
        q = hashed_embedding(query)
        hits: list[ScoredHit] = []
        
        for c in candidates:
            sim = cosine(q, c.embedding)
            rec = self.recency_component(c.age_days)
            total = (self.weights["alpha"] * sim
                     + self.weights["beta"] * c.importance
                     + self.weights["gamma"] * rec
                     + self.weights["delta"] * c.confidence)
            
            hits.append(ScoredHit(
                memory_id=c.memory_id, content=c.content, kind=c.kind,
                total=round(total, 6), sim=round(sim, 6),
                importance=round(c.importance, 6),
                recency=round(rec, 6), confidence=round(c.confidence, 6)))
            
        hits.sort(key=lambda h: h.total, reverse=True)
        for i, h in enumerate(hits[:top_k], start=1):
            h.rank = i
            
        return hits[:top_k]

    # -------------------------------------------------- sensitivitas bobot
    def weight_sensitivity(self, query: str,
                           candidates: list[RetrievalCandidate],
                           perturbation: float = 0.10,
                           top_k: int = 10) -> dict:
        """Guncang tiap bobot +-perturbation, ukur pergeseran ranking.
        Output: per bobot, Kendall-tau ranking terhadap baseline.
        tau rendah = ranking berubah drastis = bobot itu KRITIS,
        layak dikalibrasi; bukan alasan panik, alasan pengukuran.
        """
        base = [h.memory_id for h in self.search(query, candidates, top_k)]
        report: dict[str, dict] = {}
        
        for key in self.weights:
            for direction in (+1, -1):
                shifted = dict(self.weights)
                shifted[key] = min(
                    1.0, max(0.0, shifted[key] + direction * perturbation))
                renorm = sum(shifted.values())
                if renorm <= 0:
                    continue
                for k in shifted:
                    shifted[k] /= renorm
                    
                probe = HybridRetriever(weights=shifted,
                                        half_life_days=self.half_life_days)
                alt = [h.memory_id for h in probe.search(query, candidates, top_k)]
                tau = _kendall_tau(base, alt)
                tag = f"{key}{'+' if direction > 0 else '-'}"
                report[tag] = {
                    "tau": round(tau, 4),
                    "shifted_weight": round(shifted[key], 4),
                }
        return report
