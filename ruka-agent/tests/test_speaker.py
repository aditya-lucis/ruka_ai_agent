"""Unit tests for speaker verification, enrollment, and EER metrics from Ruka Volume IV."""

import numpy as np
import pytest

from ruka_perception.speaker.verification import (
    SpeakerVerifier,
    cosine_similarity,
    eer,
    far_frr_sweep,
    identify,
    roc_points,
)


def test_cosine_similarity():
    """Uji kasus batas kemiripan kosinus."""
    v1 = np.array([1.0, 0.0, 0.0])
    v2 = np.array([1.0, 0.0, 0.0])
    v3 = np.array([0.0, 1.0, 0.0])
    v4 = np.array([-1.0, 0.0, 0.0])
    zero = np.array([0.0, 0.0, 0.0])

    assert np.isclose(cosine_similarity(v1, v2), 1.0)
    assert np.isclose(cosine_similarity(v1, v3), 0.0)
    assert np.isclose(cosine_similarity(v1, v4), -1.0)
    assert np.isclose(cosine_similarity(v1, zero), 0.0)


def test_speaker_verifier_threshold_validation():
    """Ambang harus berada di (0, 1)."""
    with pytest.raises(ValueError, match="threshold di \\(0, 1\\)"):
        SpeakerVerifier(threshold=0.0)
    with pytest.raises(ValueError, match="threshold di \\(0, 1\\)"):
        SpeakerVerifier(threshold=1.0)
    with pytest.raises(ValueError, match="threshold di \\(0, 1\\)"):
        SpeakerVerifier(threshold=-0.5)


def test_enrollment_centroid_unit_norm():
    """Centroid enrollment harus ternormalisasi menjadi unit-norm."""
    samples = np.array([
        [1.0, 2.0, 3.0],
        [2.0, 1.0, 2.0],
        [3.0, 3.0, 1.0],
    ])
    centroid = SpeakerVerifier.enroll(samples)
    norm = np.linalg.norm(centroid)
    assert np.isclose(norm, 1.0, atol=1e-6)


def test_enrollment_validation():
    """Enrollment harus berdimensi 2D dengan minimal 1 sampel."""
    with pytest.raises(ValueError, match="enrollment butuh \\(n, d\\)"):
        SpeakerVerifier.enroll(np.array([1.0, 2.0, 3.0]))
    with pytest.raises(ValueError, match="enrollment butuh \\(n, d\\)"):
        SpeakerVerifier.enroll(np.empty((0, 3)))


def test_verifier_decide():
    """Keputusan biner verifier berdasarkan threshold."""
    verifier = SpeakerVerifier(threshold=0.72)
    assert verifier.decide(0.72) is True
    assert verifier.decide(0.85) is True
    assert verifier.decide(0.719) is False


def test_far_frr_sweep_monotonicity():
    """Invarian matematis buku:

    FAR monoton turun & FRR monoton naik terhadap threshold.
    """
    np.random.seed(42)
    gen = np.random.normal(loc=0.8, scale=0.05, size=200)
    imp = np.random.normal(loc=0.6, scale=0.05, size=200)

    sweep = far_frr_sweep(gen, imp)
    fars = [r["far"] for r in sweep]
    frrs = [r["frr"] for r in sweep]

    # Monoton turun untuk FAR (non-increasing)
    for i in range(len(fars) - 1):
        assert fars[i] >= fars[i + 1]

    # Monoton naik untuk FRR (non-decreasing)
    for i in range(len(frrs) - 1):
        assert frrs[i] <= frrs[i + 1]


def test_far_frr_sweep_empty_scores_error():
    """Sweep pada skor kosong harus memicu ValueError."""
    with pytest.raises(ValueError, match="skor genuine dan impostor tidak boleh kosong"):
        far_frr_sweep([], [0.5, 0.6])
    with pytest.raises(ValueError, match="skor genuine dan impostor tidak boleh kosong"):
        far_frr_sweep([0.8, 0.9], [])


def test_eer_perfect_separation():
    """Pada dataset terpisah sempurna, EER < 1%."""
    gen = np.random.uniform(0.85, 0.95, size=100)
    imp = np.random.uniform(0.1, 0.3, size=100)

    sweep = far_frr_sweep(gen, imp, thresholds=np.linspace(0.0, 1.0, 201))
    res = eer(sweep)
    assert res["eer"] < 0.01


def test_eer_overlapping_distribution():
    """Pada dataset realistis bertindih (seperti Tabel 11.1), EER berada di 2% - 45%."""
    np.random.seed(42)
    gen = np.random.normal(loc=0.78, scale=0.04, size=300)
    imp = np.random.normal(loc=0.68, scale=0.05, size=300)

    sweep = far_frr_sweep(gen, imp, thresholds=np.linspace(0.4, 0.9, 201))
    res = eer(sweep)
    assert 0.02 <= res["eer"] <= 0.45
    assert 0.68 <= res["threshold"] <= 0.78


def test_roc_points():
    """ROC points menghasilkan pasangan (FAR, 1 - FRR)."""
    sweep = [
        {"threshold": 0.0, "far": 1.0, "frr": 0.0},
        {"threshold": 0.5, "far": 0.2, "frr": 0.1},
        {"threshold": 1.0, "far": 0.0, "frr": 1.0},
    ]
    roc = roc_points(sweep)
    assert roc == [(1.0, 1.0), (0.2, 0.9), (0.0, 0.0)]


def test_identify():
    """Uji identifikasi 1-dari-N memilih kandidat kemiripan tertinggi."""
    gallery = {
        "alice": np.array([1.0, 0.0, 0.0]),
        "bob": np.array([0.0, 1.0, 0.0]),
        "charlie": np.array([0.0, 0.0, 1.0]),
    }
    probe = np.array([0.1, 0.9, 0.0])  # Suara bernoise mirip Bob
    name, score = identify(probe, gallery)
    assert name == "bob"
    assert score > 0.8


def test_identify_empty_gallery():
    """Galeri kosong harus memicu ValueError."""
    with pytest.raises(ValueError, match="galeri kosong"):
        identify(np.array([1.0, 0.0]), {})
