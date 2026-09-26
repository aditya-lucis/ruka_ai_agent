"""Unit tests for multimodal/fusion.py — Listings 8.2 & 8.3."""

import pytest

from ruka_perception.multimodal.fusion import (
    ScoreFusion,
    choose_fusion_strategy,
    late_fusion_borda,
)


class TestScoreFusion:
    def test_weighted_average(self):
        """Skor = rata-rata terbobot."""
        f = ScoreFusion({"text": 0.6, "image": 0.4})
        result = f.fuse({"text": 0.8, "image": 0.5})
        expected = 0.6 * 0.8 + 0.4 * 0.5
        assert abs(result - expected) < 1e-6

    def test_out_of_range_rejected(self):
        """Skor > 1.0 harus ditolak (bug satuan)."""
        f = ScoreFusion({"text": 1.0})
        with pytest.raises(ValueError, match=r"di luar \[0,1\]"):
            f.fuse({"text": 2.5})

    def test_no_matching_scores_raises(self):
        """Tidak ada skor yang cocok -> ValueError."""
        f = ScoreFusion({"text": 1.0})
        with pytest.raises(ValueError, match="tidak ada skor"):
            f.fuse({"audio": 0.5})

    def test_missing_modality_reported(self):
        """Modality berbobot tapi tak tersedia harus dilaporkan."""
        f = ScoreFusion({"text": 0.5, "image": 0.3, "audio": 0.2})
        m = f.missing({"text": 0.8})
        assert "image" in m
        assert "audio" in m
        assert "text" not in m

    def test_weights_normalized(self):
        """Bobot harus dinormalkan ke jumlah 1."""
        f = ScoreFusion({"a": 3, "b": 7})
        assert abs(sum(f.weights.values()) - 1.0) < 1e-10

    def test_zero_weights_rejected(self):
        with pytest.raises(ValueError, match="total bobot"):
            ScoreFusion({"a": 0, "b": 0})


class TestChooseFusionStrategy:
    def test_single_modality(self):
        assert choose_fusion_strategy(["text"], 500) == "single"

    def test_no_modality(self):
        assert choose_fusion_strategy([], 500) == "single"

    def test_fast_no_interaction(self):
        """Budget rendah tanpa interaksi token -> score fusion."""
        assert choose_fusion_strategy(
            ["text", "image"], 200, interaction_needs_cross_modal=False
        ) == "score"

    def test_slow_no_interaction(self):
        """Budget tinggi tanpa interaksi token -> late fusion."""
        assert choose_fusion_strategy(
            ["text", "image"], 500, interaction_needs_cross_modal=False
        ) == "late"

    def test_fast_with_interaction(self):
        """Budget rendah + butuh interaksi -> early fusion."""
        assert choose_fusion_strategy(
            ["text", "image"], 200, interaction_needs_cross_modal=True
        ) == "early"

    def test_slow_with_interaction(self):
        """Budget tinggi + butuh interaksi -> cross_attention."""
        assert choose_fusion_strategy(
            ["text", "image"], 500, interaction_needs_cross_modal=True
        ) == "cross_attention"


class TestLateFusionBorda:
    def test_unanimous_winner(self):
        """Kandidat pertama di semua ranking -> juara Borda."""
        rankings = {
            "text": ["A", "B", "C"],
            "image": ["A", "C", "B"],
        }
        result = late_fusion_borda(rankings)
        assert result[0] == "A"

    def test_joint_winners(self):
        """Kandidat juara bersama dua modality -> keduanya di atas."""
        rankings = {
            "text": ["A", "B"],
            "image": ["B", "A"],
        }
        result = late_fusion_borda(rankings)
        assert set(result[:2]) == {"A", "B"}
