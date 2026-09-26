"""Unit tests for expression/avatar.py — Listing 13.1 AvatarMapper."""

import pytest

from ruka_perception.expression.avatar import (
    AVATAR_LABELS,
    EXTENDED_LABELS,
    AvatarMapper,
)


class TestAvatarMapper:
    def test_known_label_returns_correct_path(self):
        """Label yang dikenal -> path sesuai (asset_dir/label.png)."""
        m = AvatarMapper(asset_dir="assets/avatar")
        assert m.asset_path("calm") == "assets/avatar/calm.png"
        assert m.asset_path("curious") == "assets/avatar/curious.png"

    def test_unknown_label_falls_back_neutral(self):
        """Label asing harus jatuh ke neutral (bukan exception)."""
        m = AvatarMapper()
        assert m.asset_path("angry_unknown") == "assets/avatar/neutral.png"

    def test_extended_label_accepted(self):
        """Label dari EXTENDED_LABELS harus diterima."""
        m = AvatarMapper()
        for label in EXTENDED_LABELS:
            path = m.asset_path(label)
            assert label in path

    def test_blend_threshold_invalid(self):
        with pytest.raises(ValueError, match="blend_threshold"):
            AvatarMapper(blend_threshold=0)
        with pytest.raises(ValueError, match="blend_threshold"):
            AvatarMapper(blend_threshold=1.0)

    def test_plan_below_threshold_is_neutral(self):
        """Intensitas < blend_threshold -> neutral (anti avatar menari)."""
        m = AvatarMapper(blend_threshold=0.35)
        plan = m.plan("curious", intensity=0.2)
        assert plan["label"] == "neutral"
        assert plan["blend_ms"] == 0  # potong langsung

    def test_plan_above_threshold_uses_label(self):
        """Intensitas >= blend_threshold -> label target."""
        m = AvatarMapper(blend_threshold=0.35)
        plan = m.plan("playful", intensity=0.6)
        assert plan["label"] == "playful"
        assert plan["blend_ms"] == 180  # cross-fade L1

    def test_plan_intensity_out_of_range(self):
        m = AvatarMapper()
        with pytest.raises(ValueError, match="intensity"):
            m.plan("calm", intensity=1.5)

    def test_plan_render_tier(self):
        m = AvatarMapper()
        plan = m.plan("calm", intensity=0.5)
        assert plan["render_tier"] == "L1_blend"

    def test_continuity_rule_neighbor_ok(self):
        """Transisi tetangga (jarak <= 2) -> True."""
        m = AvatarMapper()
        assert m.continuity_rule("calm", "curious") is True
        assert m.continuity_rule("calm", "playful") is True

    def test_continuity_rule_far_jump_suspicious(self):
        """Transisi jauh (jarak > 2) -> False (curiga)."""
        m = AvatarMapper()
        assert m.continuity_rule("calm", "concerned") is False

    def test_continuity_rule_unknown_label_passes(self):
        """Label asing -> True (lewatkan, bukan blokir)."""
        m = AvatarMapper()
        assert m.continuity_rule("calm", "mysterious_new_label") is True
