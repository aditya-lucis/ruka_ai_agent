# -*- coding: utf-8 -*-
"""Eternal Voice Pipeline & Controller (FR-VO).

Pengendali terpadu modul suara Ruka / Project Noctis:
- Penyaring rahasia (SecretScrubber) menjamin 0 kebocoran kata sandi/token
- Pengontrol prosodi 8 suasana Marquis
- Mesin TTS streaming ber-TTFB < 200 ms
- Terintegrasi dengan EventBus V3 pada OrganNamespace.VOICE
"""
from __future__ import annotations

import time
from typing import Generator

from src.gateway.events import Event, EventBus, OrganNamespace
from src.senses.voice.engine import StreamingTTSEngine
from src.senses.voice.models import (
    MarquisMood,
    ProsodySettings,
    TTSChunk,
    VisemeEvent,
)
from src.senses.voice.prosody import ProsodyController
from src.senses.voice.scrubber import SecretScrubber


class EternalVoice:
    def __init__(
        self,
        event_bus: EventBus | None = None,
        cache_capacity: int = 96,
    ) -> None:
        self.event_bus = event_bus
        self.scrubber = SecretScrubber()
        self.prosody_controller = ProsodyController()
        self.engine = StreamingTTSEngine(cache_capacity=cache_capacity)
        self._is_speaking: bool = False

    @property
    def is_speaking(self) -> bool:
        return self._is_speaking

    def speak(
        self,
        raw_text: str,
        mood: MarquisMood | str = MarquisMood.NEUTRAL,
        custom_pitch_offset: float = 0.0,
        custom_rate_multiplier: float = 1.0,
    ) -> Generator[TTSChunk, None, None]:
        """Menyaring rahasia, mengatur prosodi, dan menghasilkan chunk audio streaming."""
        start_t = time.perf_counter()

        # 1. Penyaringan Rahasia Mutlak
        clean_text = self.scrubber.scrub(raw_text)
        if not clean_text or not clean_text.strip():
            return

        # 2. Perhitungan Prosodi Mood
        prosody = self.prosody_controller.get_settings(
            mood=mood,
            custom_pitch_offset=custom_pitch_offset,
            custom_rate_multiplier=custom_rate_multiplier,
        )

        # 3. Publikasikan event speaking_start
        self._is_speaking = True
        if self.event_bus:
            self.event_bus.publish(
                Event(
                    namespace=OrganNamespace.VOICE.value,
                    event_type="voice.speaking_start",
                    source="eternal_voice",
                    payload={
                        "text": clean_text,
                        "mood": mood.value if isinstance(mood, MarquisMood) else str(mood),
                        "pitch": prosody.pitch_semitones,
                        "rate": prosody.rate_multiplier,
                    },
                )
            )

        try:
            for chunk in self.engine.synthesize_stream(clean_text, prosody, mood=mood):
                # Publikasikan viseme untuk sinkronisasi avatar
                if self.event_bus and chunk.visemes:
                    for v in chunk.visemes:
                        self.event_bus.publish(
                            Event(
                                namespace=OrganNamespace.VOICE.value,
                                event_type="voice.viseme",
                                source="eternal_voice",
                                payload={
                                    "viseme": v.viseme_id,
                                    "timestamp_ms": v.timestamp_ms,
                                    "weight": v.weight,
                                },
                            )
                        )
                yield chunk
        finally:
            self._is_speaking = False
            total_duration_ms = (time.perf_counter() - start_t) * 1000.0
            if self.event_bus:
                self.event_bus.publish(
                    Event(
                        namespace=OrganNamespace.VOICE.value,
                        event_type="voice.speaking_stop",
                        source="eternal_voice",
                        payload={"duration_ms": total_duration_ms},
                    )
                )
