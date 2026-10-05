# -*- coding: utf-8 -*-
"""6-Branch Idle Animation Tree (FR-AV-07).

Pohon animasi menganggur 6 cabang:
- NOBLE_OBSERVE, TAIL_PLAY, EAR_PREEN, CURIOUS_TILT, DEEP_REST, VIGILANT_GUARD
- Pemilihan berdasarkan suasana hati * energi
- Transisi blending 800 ms
- Batasan pengulangan: tidak ada cabang berulang lebih dari 2 kali berturut-turut
"""
from __future__ import annotations

import random
from typing import Optional
from src.avatar.models import IdleBranch
from src.presence.models import MoodState

MOOD_TO_BRANCH_AFFINITIES: dict[MoodState, list[IdleBranch]] = {
    MoodState.VAMPIRE_NOBLE: [IdleBranch.NOBLE_OBSERVE, IdleBranch.TAIL_PLAY],
    MoodState.CALM: [IdleBranch.NOBLE_OBSERVE, IdleBranch.EAR_PREEN],
    MoodState.SLEEPY: [IdleBranch.DEEP_REST],
    MoodState.FOCUSED: [IdleBranch.NOBLE_OBSERVE, IdleBranch.CURIOUS_TILT],
    MoodState.PROTECTIVE: [IdleBranch.VIGILANT_GUARD, IdleBranch.NOBLE_OBSERVE],
    MoodState.HAPPY: [IdleBranch.TAIL_PLAY, IdleBranch.CURIOUS_TILT],
    MoodState.EXCITED: [IdleBranch.TAIL_PLAY, IdleBranch.EAR_PREEN, IdleBranch.CURIOUS_TILT],
    MoodState.ANXIOUS: [IdleBranch.VIGILANT_GUARD, IdleBranch.EAR_PREEN],
}


class IdleAnimationTree:
    TRANSITION_DURATION_S = 0.800  # 800 ms transisi

    def __init__(self, rng_seed: Optional[int] = None) -> None:
        self.rng = random.Random(rng_seed)
        self.current_branch: IdleBranch = IdleBranch.NOBLE_OBSERVE
        self.previous_branch: IdleBranch = IdleBranch.NOBLE_OBSERVE
        self.consecutive_repeat_count: int = 1
        self.history_trace: list[IdleBranch] = [IdleBranch.NOBLE_OBSERVE]

    def select_next_branch(self, mood: MoodState, energy: float = 0.5) -> IdleBranch:
        """Memilih cabang animasi idle berikutnya dengan aturan maksimal 2x berulang."""
        candidates = list(MOOD_TO_BRANCH_AFFINITIES.get(mood, [IdleBranch.NOBLE_OBSERVE]))

        # Tambahkan variasi jika energi tinggi
        if energy > 0.7 and IdleBranch.TAIL_PLAY not in candidates:
            candidates.append(IdleBranch.TAIL_PLAY)

        # Jika cabang saat ini sudah 2x berturut-turut, buang dari kandidat
        if self.consecutive_repeat_count >= 2 and self.current_branch in candidates and len(candidates) > 1:
            candidates = [c for c in candidates if c != self.current_branch]

        # Pilih cabang baru
        chosen = self.rng.choice(candidates) if candidates else IdleBranch.NOBLE_OBSERVE

        if chosen == self.current_branch:
            self.consecutive_repeat_count += 1
        else:
            self.previous_branch = self.current_branch
            self.current_branch = chosen
            self.consecutive_repeat_count = 1

        self.history_trace.append(chosen)
        return self.current_branch
