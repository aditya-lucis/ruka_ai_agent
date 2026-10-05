# -*- coding: utf-8 -*-
"""Lunar Clock 7-Phase Cycle Engine (FR-OS-07).

Mengatur siklus sirkadian 7 fase harian yang mengontrol:
- Lantai suasana hati (mood floor) & langit-langit energi (level ceiling)
- Izin berbicara bersuara (voice permission): suara malam dilarang tanpa izin Young Lord
"""
from __future__ import annotations

from datetime import datetime
from typing import Optional
from src.os_companion.models import LunarPhase


class LunarClock:
    @staticmethod
    def get_phase(dt: Optional[datetime] = None) -> LunarPhase:
        """Menentukan fase hari berdasarkan waktu lokal."""
        now = dt or datetime.now()
        minutes_since_midnight = now.hour * 60 + now.minute

        # 04:30 = 270 menit
        # 06:00 = 360 menit
        # 11:30 = 690 menit
        # 14:00 = 840 menit
        # 18:00 = 1080 menit
        # 20:00 = 1200 menit
        # 22:00 = 1320 menit

        if 270 <= minutes_since_midnight < 360:
            return LunarPhase.FAJR
        elif 360 <= minutes_since_midnight < 690:
            return LunarPhase.MORNING
        elif 690 <= minutes_since_midnight < 840:
            return LunarPhase.NOON
        elif 840 <= minutes_since_midnight < 1080:
            return LunarPhase.AFTERNOON
        elif 1080 <= minutes_since_midnight < 1200:
            return LunarPhase.DUSK
        elif 1200 <= minutes_since_midnight < 1320:
            return LunarPhase.NIGHT
        else:
            return LunarPhase.MIDNIGHT

    @staticmethod
    def is_voice_allowed(phase: LunarPhase) -> bool:
        """Suara audio keras dilarang pada fase MIDNIGHT (hanya teks/bisikan)."""
        return phase != LunarPhase.MIDNIGHT

    @staticmethod
    def get_mood_constraints(phase: LunarPhase) -> dict[str, str | float]:
        """Mengatur batasan dasar afektif sesuai fase sirkadian."""
        if phase == LunarPhase.MIDNIGHT:
            return {"mood_floor": "sleepy", "max_arousal": 0.2, "voice_allowed": False}
        elif phase == LunarPhase.FAJR:
            return {"mood_floor": "calm", "max_arousal": 0.4, "voice_allowed": True}
        elif phase == LunarPhase.MORNING:
            return {"mood_floor": "happy", "max_arousal": 1.0, "voice_allowed": True}
        elif phase == LunarPhase.NOON:
            return {"mood_floor": "calm", "max_arousal": 0.6, "voice_allowed": True}
        elif phase == LunarPhase.AFTERNOON:
            return {"mood_floor": "focused", "max_arousal": 0.9, "voice_allowed": True}
        elif phase == LunarPhase.DUSK:
            return {"mood_floor": "vampire_noble", "max_arousal": 0.7, "voice_allowed": True}
        else:  # NIGHT
            return {"mood_floor": "vampire_noble", "max_arousal": 0.5, "voice_allowed": True}
