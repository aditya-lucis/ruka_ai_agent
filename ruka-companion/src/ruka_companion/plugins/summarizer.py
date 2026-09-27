"""RUKA VI: Reference Plugin — Notes Summarizer (TF + MMR Extractive Summarization).
Strictly follows RUKA-VI Chapter XXI (baris 40-105).
"""

from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any

_SENT_SPLIT = re.compile(r"(?<=[.!?])\s+")
_WORD = re.compile(r"[A-Za-z0-9_]+")


@dataclass
class Summarizer:
    """Ekstraktif: skor TF + MMR diversity; k kalimat teratas (urut asli)."""

    lambda_mmr: float = 0.7

    def summarize(self, text: str, k: int = 3) -> dict[str, Any]:
        sents = [s.strip() for s in _SENT_SPLIT.split(text.strip()) if s.strip()]
        if not sents:
            return {"summary": "", "n_sentences": 0, "method": "tf+mmr"}

        k = max(1, min(k, len(sents)))
        tokenized = [[w.lower() for w in _WORD.findall(s)] for s in sents]

        # TF dokumen
        df: dict[str, int] = {}
        for toks in tokenized:
            for w in set(toks):
                df[w] = df.get(w, 0) + 1

        # skor kalimat = Σ df(w)/n dinormalisasi panjang
        n = len(sents)
        scores = []
        for toks in tokenized:
            s = sum(df[w] / n for w in set(toks)) / max(1, len(toks) ** 0.5)
            scores.append(s)

        # MMR selection
        def overlap(a: int, b: int) -> float:
            sa, sb = set(tokenized[a]), set(tokenized[b])
            if not sa or not sb:
                return 0.0
            return len(sa & sb) / min(len(sa), len(sb))

        selected: list[int] = []
        pool = list(range(n))
        while len(selected) < k and pool:
            best_i, best_v = None, float("-inf")
            for i in pool:
                red = max((overlap(i, j) for j in selected), default=0.0)
                mmr = self.lambda_mmr * scores[i] - (1 - self.lambda_mmr) * red
                if mmr > best_v:
                    best_i, best_v = i, mmr
            if best_i is not None:
                selected.append(best_i)
                pool.remove(best_i)
            else:
                break

        order = sorted(selected)
        return {
            "summary": " ".join(sents[i] for i in order),
            "n_sentences": n,
            "selected": [i + 1 for i in order],  # 1-based urutan kalimat
            "method": "tf+mmr-extractive",
        }


def summarize(text: str, k: int = 3) -> dict[str, Any]:
    return Summarizer().summarize(text, k)
