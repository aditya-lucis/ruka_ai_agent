# -*- coding: utf-8 -*-
"""Asymmetric Idle Breathing Engine (FR-PR-02).

Mengimplementasikan kurva pernapasan asimetris murni matematis:
- Mode tenang (CALM / VAMPIRE_NOBLE): 15 napas/menit (periode 4.0s), rasio dada 1.00 s.d. 1.04.
  Inhale (40% siklus), Exhale (60% siklus) dengan kurva peredaman cosinus halus.
- Mode mengantuk (SLEEPY): Pola pranayama 4-7-8 (Inhale 4.0s, Hold 7.0s, Exhale 8.0s, total 19.0s).
- Mode waspada/bersemangat (EXCITED / ANXIOUS): 24 napas/menit (periode 2.5s), skala 1.00 s.d. 1.05.
"""
from __future__ import annotations

import math
from src.presence.models import BreathingState, MoodState


class BreathingEngine:
    def __init__(self) -> None:
        self._start_time: float = 0.0

    def compute(self, timestamp: float, mood: MoodState) -> BreathingState:
        """Menghitung skala dada dan fase napas pada waktu `timestamp`."""
        if mood == MoodState.SLEEPY:
            # Pola 4-7-8: Inhale 4s, Hold 7s, Exhale 8s (Total 19s)
            cycle_duration = 19.0
            t_in_cycle = timestamp % cycle_duration
            if t_in_cycle < 4.0:
                # Inhale: 1.0 -> 1.03 (sinusoidal)
                progress = t_in_cycle / 4.0
                scale = 1.0 + 0.03 * (0.5 - 0.5 * math.cos(progress * math.pi))
                return BreathingState(chest_scale=round(scale, 4), phase_ratio=t_in_cycle / cycle_duration, is_inhale=True)
            elif t_in_cycle < 11.0:
                # Hold: tahan di 1.03
                return BreathingState(chest_scale=1.03, phase_ratio=t_in_cycle / cycle_duration, is_inhale=False)
            else:
                # Exhale: 1.03 -> 1.0 (8s)
                progress = (t_in_cycle - 11.0) / 8.0
                scale = 1.03 - 0.03 * (0.5 - 0.5 * math.cos(progress * math.pi))
                return BreathingState(chest_scale=round(scale, 4), phase_ratio=t_in_cycle / cycle_duration, is_inhale=False)

        elif mood in (MoodState.EXCITED, MoodState.ANXIOUS):
            # Cepat: 24 napas per menit (periode 2.5s), skala 1.0 s.d. 1.05
            cycle_duration = 2.5
            inhale_duration = 1.0
            t_in_cycle = timestamp % cycle_duration
            if t_in_cycle < inhale_duration:
                progress = t_in_cycle / inhale_duration
                scale = 1.0 + 0.05 * (0.5 - 0.5 * math.cos(progress * math.pi))
                return BreathingState(chest_scale=round(scale, 4), phase_ratio=t_in_cycle / cycle_duration, is_inhale=True)
            else:
                progress = (t_in_cycle - inhale_duration) / (cycle_duration - inhale_duration)
                scale = 1.05 - 0.05 * (0.5 - 0.5 * math.cos(progress * math.pi))
                return BreathingState(chest_scale=round(scale, 4), phase_ratio=t_in_cycle / cycle_duration, is_inhale=False)

        else:
            # Mode Tenang (CALM, HAPPY, FOCUSED, VAMPIRE_NOBLE, PROTECTIVE)
            # 15 napas per menit (periode 4.0s), rasio asimetris: Inhale 1.6s (40%), Exhale 2.4s (60%)
            # Skala dada: 1.00 s.d. 1.04
            cycle_duration = 4.0
            inhale_duration = 1.6
            t_in_cycle = timestamp % cycle_duration
            if t_in_cycle < inhale_duration:
                progress = t_in_cycle / inhale_duration
                scale = 1.0 + 0.04 * (0.5 - 0.5 * math.cos(progress * math.pi))
                return BreathingState(chest_scale=round(scale, 4), phase_ratio=t_in_cycle / cycle_duration, is_inhale=True)
            else:
                progress = (t_in_cycle - inhale_duration) / (cycle_duration - inhale_duration)
                scale = 1.04 - 0.04 * (0.5 - 0.5 * math.cos(progress * math.pi))
                return BreathingState(chest_scale=round(scale, 4), phase_ratio=t_in_cycle / cycle_duration, is_inhale=False)
