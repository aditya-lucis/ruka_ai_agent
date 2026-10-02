# -*- coding: utf-8 -*-
"""Intent classifier – naik tangga: rules -> embedding -> MLP (Phase 2 Expanded).
Mendukung klasifikasi intent reguler dan intent koding tingkat tinggi:
coding_implement, coding_debug, coding_refactor, coding_review, coding_explain.
"""
from __future__ import annotations

import json
from enum import Enum
from pathlib import Path
from typing import Any

import numpy as np

DEFAULT_CLASSES = ["question", "task_request", "greeting", "smalltalk"]
CODING_CLASSES = [
    "question",
    "task_request",
    "greeting",
    "smalltalk",
    "coding_implement",
    "coding_debug",
    "coding_refactor",
    "coding_review",
    "coding_explain",
]

# Backward compatibility alias
CLASSES = DEFAULT_CLASSES
N_FEATURES = 64 + 6  # 64-dim embedding + 6 fitur leksikal dasar
N_CODING_FEATURES = 64 + 12  # 64-dim embedding + 12 fitur leksikal koding


class CognitiveMode(str, Enum):
    COMPANION = "companion"
    CODING = "coding"
    HYBRID = "hybrid"


def lexical_features(text: str) -> list[float]:
    """Fitur leksikal dasar 6-dimensi (kompatibel penuh v0.1)."""
    t = text.strip().lower()
    return [
        min(1.0, len(t) / 80.0),
        1.0 if t.endswith("?") else 0.0,
        1.0
        if any(
            w in t
            for w in (
                "tolong",
                "buatkan",
                "buat",
                "jalankan",
                "cari",
                "analisa",
                "implement",
            )
        )
        else 0.0,
        1.0
        if any(
            w in t
            for w in ("hai", "halo", "selamat", "pagi", "siang", "malam")
        )
        else 0.0,
        1.0
        if t.startswith(
            ("apa", "siapa", "kenapa", "bagaimana", "kapan", "berapa", "mengapa")
        )
        else 0.0,
        1.0 if len(t.split()) <= 3 else 0.0,
    ]


def coding_lexical_features(text: str) -> list[float]:
    """Fitur leksikal koding yang diperluas (12-dimensi) untuk deteksi intent rekayasa."""
    base = lexical_features(text)
    t = text.strip().lower()

    has_code_syntax = 1.0 if any(k in t for k in ("def ", "class ", "function ", "import ", "const ", "let ", "return ", "async ", "await ")) else 0.0
    has_debug_word = 1.0 if any(k in t for k in ("bug", "error", "exception", "traceback", "fix", "gagal", "rusak", "crash", "perbaiki")) else 0.0
    has_refactor_word = 1.0 if any(k in t for k in ("refactor", "rapikan", "bersihkan", "optimasi", "clean code", "struktur", "rombak")) else 0.0
    has_review_word = 1.0 if any(k in t for k in ("review", "tinjau", "evaluasi", "periksa", "audit", "cek kode")) else 0.0
    has_explain_word = 1.0 if any(k in t for k in ("jelaskan kode", "artinya apa", "bagaimana logika", "explain", "fungsi kode ini")) else 0.0
    has_implement_word = 1.0 if any(k in t for k in ("implementasikan", "tuliskan kode", "buat modul", "tambahkan endpoint", "coding", "bikin class")) else 0.0

    return base + [
        has_code_syntax,
        has_debug_word,
        has_refactor_word,
        has_review_word,
        has_explain_word,
        has_implement_word,
    ]


class IntentMLP:
    """MLP numpy murni – 2 layer, softmax, tanh dengan dukungan multi-kelas dinamis."""

    def __init__(
        self,
        seed: int = 42,
        classes: list[str] | None = None,
        n_features: int = N_FEATURES,
    ) -> None:
        self.classes = list(classes) if classes is not None else list(CLASSES)
        self.n_features = n_features
        rng = np.random.default_rng(seed)
        self.w1 = rng.normal(0, 0.05, (self.n_features, 32))
        self.b1 = np.zeros(32)
        self.w2 = rng.normal(0, 0.05, (32, len(self.classes)))
        self.b2 = np.zeros(len(self.classes))

    # ---- forward ----
    def forward(self, x: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        h = np.tanh(x @ self.w1 + self.b1)
        logits = h @ self.w2 + self.b2
        e = np.exp(logits - logits.max(axis=-1, keepdims=True))
        return h, e / e.sum(axis=-1, keepdims=True)

    def predict(self, features: list[float]) -> tuple[str, float]:
        x = np.asarray(features, dtype=np.float64)
        _, probs = self.forward(x)
        idx = int(probs.argmax())
        return self.classes[idx], float(probs[idx])

    # ---- training ----
    def train(
        self,
        X: np.ndarray,
        y: list[int],
        epochs: int = 200,
        lr: float = 0.1,
        l2: float = 1e-4,
        X_val: np.ndarray | None = None,
        y_val: list[int] | None = None,
        patience: int = 20,
    ) -> list[float]:
        n_classes = len(self.classes)
        y_onehot = np.zeros((len(y), n_classes))
        y_onehot[np.arange(len(y)), y] = 1.0
        best, best_epoch, wait = 1e9, 0, 0
        history: list[float] = []

        for epoch in range(epochs):
            h, probs = self.forward(X)
            loss = -(y_onehot * np.log(probs + 1e-9)).sum() / len(X)
            loss += l2 * ((self.w1 ** 2).sum() + (self.w2 ** 2).sum())
            history.append(float(loss))

            grad_logits = (probs - y_onehot) / len(X)
            gw2 = h.T @ grad_logits + 2 * l2 * self.w2
            gb2 = grad_logits.sum(axis=0)
            gh = grad_logits @ self.w2.T
            gz = gh * (1 - h ** 2)
            gw1 = X.T @ gz + 2 * l2 * self.w1
            gb1 = gz.sum(axis=0)

            for w, g in ((self.w1, gw1), (self.w2, gw2)):
                w -= lr * g
            self.b1 -= lr * gb1
            self.b2 -= lr * gb2

            if X_val is not None and y_val is not None:
                _, pv = self.forward(X_val)
                val_loss = -float(
                    np.log(pv[np.arange(len(y_val)), y_val] + 1e-9).mean()
                )
                if val_loss < best - 1e-4:
                    best, best_epoch, wait = val_loss, epoch, 0
                else:
                    wait += 1
                    if wait >= patience:
                        break
        return history

    # ---- persistensi ----
    def save(self, path: Path) -> None:
        blob = {
            "w1": self.w1.tolist(),
            "b1": self.b1.tolist(),
            "w2": self.w2.tolist(),
            "b2": self.b2.tolist(),
            "classes": self.classes,
            "n_features": self.n_features,
        }
        path.write_text(json.dumps(blob), encoding="utf-8")

    @classmethod
    def load(cls, path: Path) -> "IntentMLP":
        blob = json.loads(path.read_text(encoding="utf-8"))
        saved_classes = blob.get("classes", CLASSES)
        saved_features = blob.get("n_features", N_FEATURES)
        model = cls(classes=saved_classes, n_features=saved_features)
        model.w1 = np.asarray(blob["w1"])
        model.b1 = np.asarray(blob["b1"])
        model.w2 = np.asarray(blob["w2"])
        model.b2 = np.asarray(blob["b2"])
        return model


class CodingIntentMLP(IntentMLP):
    """MLP spesifik untuk kognisi koding Ruka (9 kelas, 76-dimensi)."""

    def __init__(self, seed: int = 42) -> None:
        super().__init__(seed=seed, classes=CODING_CLASSES, n_features=N_CODING_FEATURES)


def route_cognitive_mode(intent: str) -> CognitiveMode:
    """Mengonversi intent hasil klasifikasi menjadi CognitiveMode Ruka."""
    if intent.startswith("coding_"):
        return CognitiveMode.CODING
    if intent in ("greeting", "smalltalk"):
        return CognitiveMode.COMPANION
    return CognitiveMode.HYBRID


def embed_or_fallback(text: str, embedder: Any = None) -> list[float]:
    """Embedding 64-d (output_dimensionality Vol I) atau vektor
    hash deterministik untuk offline/dev – kontrak panjang tetap.
    """
    if embedder is not None:
        return embedder.embed(text, dim=64)
    rng = np.random.default_rng(abs(hash(text)) % (2 ** 32))
    v = rng.normal(0, 1, 64)
    return (v / np.linalg.norm(v)).tolist()
