# -*- coding: utf-8 -*-
"""8-State Mood FSM with Valence-Arousal Appraisal & 3-Eval Hysteresis (FR-PR-07).

Mengelola kondisi emosional RUKA dalam ruang Valence-Arousal [-1.0, 1.0]:
- 8 Suasana Hati: CALM, HAPPY, EXCITED, FOCUSED, PROTECTIVE, ANXIOUS, VAMPIRE_NOBLE, SLEEPY.
- Histeresis 3 evaluasi berturut-turut untuk mencegah perubahan liar (mood jitter).
- Publikasi event `presence.mood` ke EventBus V3 pada OrganNamespace.PRESENCE.
"""
from __future__ import annotations

import math
from typing import Optional
from src.gateway.events import Event, EventBus, OrganNamespace
from src.presence.models import MoodState, ValenceArousal

# Titik pusat prototipe suasana hati dalam ruang Valence-Arousal
MOOD_PROTOTYPES: dict[MoodState, ValenceArousal] = {
    MoodState.SLEEPY: ValenceArousal(valence=0.0, arousal=-0.8),
    MoodState.CALM: ValenceArousal(valence=0.3, arousal=-0.3),
    MoodState.VAMPIRE_NOBLE: ValenceArousal(valence=0.4, arousal=0.2),
    MoodState.FOCUSED: ValenceArousal(valence=0.2, arousal=0.5),
    MoodState.HAPPY: ValenceArousal(valence=0.7, arousal=0.4),
    MoodState.EXCITED: ValenceArousal(valence=0.8, arousal=0.8),
    MoodState.PROTECTIVE: ValenceArousal(valence=0.1, arousal=0.7),
    MoodState.ANXIOUS: ValenceArousal(valence=-0.6, arousal=0.6),
}


class MoodStateMachine:
    def __init__(
        self,
        event_bus: Optional[EventBus] = None,
        initial_mood: MoodState = MoodState.VAMPIRE_NOBLE,
    ) -> None:
        self.event_bus = event_bus
        self.current_mood: MoodState = initial_mood
        self.current_va: ValenceArousal = MOOD_PROTOTYPES[initial_mood]

        # Histeresis 3 evaluasi
        self._candidate_mood: Optional[MoodState] = None
        self._consecutive_candidate_count: int = 0

    def _distance(self, va1: ValenceArousal, va2: ValenceArousal) -> float:
        return math.sqrt((va1.valence - va2.valence) ** 2 + (va1.arousal - va2.arousal) ** 2)

    def appraise_nearest_mood(self, target_va: ValenceArousal) -> MoodState:
        """Mencari prototipe suasana hati terdekat dari koordinat Valence-Arousal."""
        best_mood = self.current_mood
        min_dist = float("inf")
        for mood, proto in MOOD_PROTOTYPES.items():
            dist = self._distance(target_va, proto)
            if dist < min_dist:
                min_dist = dist
                best_mood = mood
        return best_mood

    def update_va(
        self,
        new_valence: float,
        new_arousal: float,
        immediate: bool = False,
    ) -> MoodState:
        """Memperbarui nilai Valence-Arousal dan melakukan transisi dengan histeresis 3 evaluasi."""
        self.current_va = ValenceArousal(valence=new_valence, arousal=new_arousal).clamp()
        nearest = self.appraise_nearest_mood(self.current_va)

        if immediate:
            # Bypass histeresis jika transisi mendesak
            self._transition_to(nearest)
            return self.current_mood

        if nearest == self.current_mood:
            self._candidate_mood = None
            self._consecutive_candidate_count = 0
            return self.current_mood

        # Evaluasi histeresis
        if nearest == self._candidate_mood:
            self._consecutive_candidate_count += 1
            if self._consecutive_candidate_count >= 3:
                self._transition_to(nearest)
        else:
            self._candidate_mood = nearest
            self._consecutive_candidate_count = 1

        return self.current_mood

    def _transition_to(self, new_mood: MoodState) -> None:
        old_mood = self.current_mood
        self.current_mood = new_mood
        self._candidate_mood = None
        self._consecutive_candidate_count = 0

        if self.event_bus:
            self.event_bus.publish(
                Event(
                    namespace=OrganNamespace.PRESENCE.value,
                    event_type="presence.mood",
                    source="mood_fsm",
                    payload={
                        "from_mood": old_mood.value,
                        "to_mood": new_mood.value,
                        "valence": self.current_va.valence,
                        "arousal": self.current_va.arousal,
                    },
                )
            )
