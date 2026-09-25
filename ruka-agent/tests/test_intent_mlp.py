# -*- coding: utf-8 -*-
from pathlib import Path
import numpy as np
import pytest
from src.neural.intent import (
    CLASSES,
    IntentMLP,
    embed_or_fallback,
    lexical_features,
)


def _features(text: str) -> list[float]:
    return embed_or_fallback(text) + lexical_features(text)


def test_shapes_and_output_range():
    m = IntentMLP(seed=42)
    label, p = m.predict(_features("berapa 2+2?"))
    assert label in CLASSES
    assert 0.25 <= p <= 1.0              # softmax 4 kelas: min 0.25


def test_training_reduces_loss_on_separable_data():
    rng = np.random.default_rng(7)
    X = rng.normal(0, 1, (200, 64 + 6))
    y = (X[:, 0] > 0).astype(int)        # kelas 0/1 terpisah jelas
    m = IntentMLP(seed=42)
    hist = m.train(X, list(y), epochs=60)
    assert hist[-1] < hist[0] * 0.5


def test_roundtrip_save_load(tmp_path: Path):
    m = IntentMLP(seed=42)
    p = tmp_path / "m.json"
    m.save(p)
    m2 = IntentMLP.load(p)
    assert np.allclose(m.w1, m2.w1) and np.allclose(m.b2, m2.b2)


def test_lexical_features_signal():
    f = lexical_features("Tolong buatkan laporan")
    assert f[2] == 1.0                    # penanda permintaan tugas
    assert f[3] == 0.0                    # tanpa sapaan
    g = lexical_features("Halo, siapa kamu?")
    assert g[1] == 1.0 and g[3] == 1.0
