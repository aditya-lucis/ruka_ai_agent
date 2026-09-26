# -*- coding: utf-8 -*-
"""IntentClassifier: the full discipline of Part VI in one artifact.
Three models, one interface, one shared evaluation:
1. ``RuleBasedIntentClassifier`` — keyword/pattern baseline;
2. ``CentroidIntentClassifier`` — nearest-embedding-centroid
   baseline (the "embedding similarity" middle rung);
3. ``MLPIntentClassifier`` — the trained neural rung.
The point is not that the MLP wins — it is that whichever wins, we can
*prove it with numbers* on identical splits, and ship the cheapest
model that meets the bar. ``confidence`` is reported with an honest
caveat: raw softmax outputs are not calibrated probabilities (Part VIII
shows what to do about that).
"""
from __future__ import annotations
import re
from dataclasses import dataclass
import numpy as np

from .datasets import INTENTS, INTENT_ID
from .features import hashed_trigram_features
from .network import MLP
from .trainer import Trainer, TrainingReport

_RULES: dict[str, list[str]] = {
    "question": [r"\bapa\b", r"\bbagaimana\b", r"\bkenapa\b", r"\bkapan\b",
                 r"\bsiapa\b", r"\bjelaskan\b", r"\bwhat\b", r"\bhow\b",
                 r"\bwhy\b", r"\?"],
    "command": [r"\bjalankan\b", r"\bbuatkan\b", r"\bhapus\b", r"\bkirim\b",
                r"\bupdate\b", r"\batur\b", r"\brun\b", r"\bdelete\b",
                r"\bset\b"],
    "chitchat": [r"\bkabar\b", r"\bngobrol\b", r"\blucu\b", r"\bcuaca\b",
                 r"\bcapek\b", r"\bhow are you\b", r"\bfun\b", r"\bhai\b",
                 r"\bhi\b", r"\bthanks\b"],
    "lookup": [r"\bcari\b", r"\btemukan\b", r"\btampilkan\b", r"\bbuka\b",
               r"\bsearch\b", r"\bfind\b", r"\bshow\b", r"\bwhere\b"],
    "code_help": [r"\bbug\b", r"\brefactor\b", r"\btest\b", r"\bdebug\b",
                  r"\berror\b", r"\bexception\b", r"\boptimize\b",
                  r"\breview\b", r"\bfix\b", r"\btraceback\b"],
}

_RULE_COMPILED = {k: [re.compile(p, re.IGNORECASE) for p in v]
                  for k, v in _RULES.items()}

@dataclass
class Prediction:
    label: str
    confidence: float
    probabilities: tuple[float, ...]
    reason: str

def _probs_from_logits(logits: np.ndarray) -> np.ndarray:
    z = logits.astype(np.float64)
    z = z - z.max()
    e = np.exp(z)
    return e / e.sum()

class RuleBasedIntentClassifier:
    """Baseline 1: transparent keyword scoring. Zero training."""
    def predict_one(self, text: str) -> Prediction:
        scores = {}
        for intent, patterns in _RULE_COMPILED.items():
            scores[intent] = sum(1 for p in patterns if p.search(text))
            
        total = sum(scores.values())
        best = max(scores, key=scores.get) if total else "chitchat"
        conf = scores[best] / total if total else 1.0 / len(INTENTS)
        reason = (f"matched {scores.get(best, 0)}/{total or len(INTENTS)} keyword "
                  f"hits for {best}")
        return Prediction(best, round(float(conf), 6), (), reason)

class CentroidIntentClassifier:
    """Baseline 2: nearest class centroid in hashed-feature space."""
    def __init__(self, dimension: int = 512) -> None:
        self.dimension = dimension
        self._centroids: np.ndarray | None = None

    def fit(self, texts: list[str], labels: np.ndarray) -> None:
        x = hashed_trigram_features(texts, self.dimension)
        cents = []
        for c in range(len(INTENTS)):
            mask = labels == c
            if not mask.any():
                raise ValueError(f"no training examples for intent '{INTENTS[c]}'")
            v = x[mask].mean(axis=0)
            n = np.linalg.norm(v)
            cents.append(v / (n or 1e-12))
        self._centroids = np.vstack(cents)

    def predict_one(self, text: str) -> Prediction:
        if self._centroids is None:
            raise RuntimeError("fit() must run before predict_one()")
        v = hashed_trigram_features([text], self.dimension)[0]
        sims = self._centroids @ v
        order = np.argsort(-sims)
        best = int(order[0])
        
        # softmax over sims with temperature: pseudo-probabilities
        t = max(float(sims.max() - np.sort(sims)[-2] if len(sims) > 1 else 1.0), 1e-3)
        exp = np.exp((sims - sims.max()) / t)
        probs = exp / exp.sum()
        
        return Prediction(INTENTS[best], round(float(probs[best]), 6),
                          tuple(round(float(p), 6) for p in probs),
                          f"centroid cosine={float(sims[best]):.3f}")

class MLPIntentClassifier:
    """The neural rung: hashed features -> small MLP over logits."""
    def __init__(self, dimension: int = 512, hidden: tuple[int, ...] = (64,),
                 seed: int = 0) -> None:
        self.dimension = dimension
        self.net = MLP(d_in=dimension, d_out=len(INTENTS), hidden=hidden,
                       activation="relu", seed=seed)
        self._fit_report: TrainingReport | None = None

    @property
    def fit_report(self) -> TrainingReport | None:
        return self._fit_report

    def fit(self, train_x: list[str], train_y: np.ndarray,
            val_x: list[str], val_y: np.ndarray,
            lr: float = 0.01, epochs: int = 60, batch: int = 32,
            l2: float = 1e-4) -> TrainingReport:
        xt = hashed_trigram_features(train_x, self.dimension)
        xv = hashed_trigram_features(val_x, self.dimension)
        
        trainer = Trainer(self.net, loss="cce", optimizer="adam", lr=lr,
                          batch_size=batch, max_epochs=epochs, patience=12,
                          l2=l2, grad_clip=5.0, seed=0)
        self._fit_report = trainer.fit(xt, train_y, xv, val_y)
        return self._fit_report

    def predict_one(self, text: str) -> Prediction:
        x = hashed_trigram_features([text], self.dimension)
        logits = self.net.forward(x)[0]
        probs = _probs_from_logits(logits)
        best = int(np.argmax(probs))
        return Prediction(INTENTS[best], round(float(probs[best]), 6),
                          tuple(round(float(p), 6) for p in probs),
                          "mlp softmax (uncalibrated)")
