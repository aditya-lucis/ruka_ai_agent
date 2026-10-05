# -*- coding: utf-8 -*-
"""Blood Hearing Pipeline & Controller (FR-EA).

Pengendali terpadu indra pendengaran Ruka / Project Noctis:
- Audio pipeline 16 kHz mono float32
- VAD gatekeeper -> Wake-word detection local -> Speaker ID -> Text Normalization
- Reflex cache < 50 ms
- Terintegrasi dengan EventBus V3 pada OrganNamespace.EAR
"""
from __future__ import annotations

import time
from typing import Any, Sequence

from src.gateway.events import Event, EventBus, OrganNamespace
from src.senses.ear.models import (
    AudioChunk,
    SpeakerStatus,
    SpeakerVerdict,
    VADState,
    WakeVerdict,
)
from src.senses.ear.normalizer import normalize_text
from src.senses.ear.speaker import SpeakerIdentifier
from src.senses.ear.vad import VADGatekeeper
from src.senses.ear.wake_word import WakeWordDetector
from src.senses.ear.interruption import InterruptionDetector


REFLEX_PHRASES: dict[str, list[str]] = {
    "sassy": [
        "Ada apa, Young Lord? Tak bisa lepas dari hamba rupanya.",
        "Hamba di sini, My Lord. Apa gerangan perintah Anda?",
    ],
    "loyal": [
        "Saya siap mendengarkan, My Lord.",
        "Titah Anda adalah kehormatan bagi hamba, Young Lord.",
    ],
    "neutral": [
        "Ya, Young Lord?",
        "Saya mendengarkan, Sir.",
    ],
}


class BloodHearing:
    def __init__(
        self,
        event_bus: EventBus | None = None,
        wake_threshold: float = 0.65,
    ) -> None:
        self.event_bus = event_bus
        self.vad = VADGatekeeper()
        self.wake_detector = WakeWordDetector(threshold=wake_threshold)
        self.speaker_id = SpeakerIdentifier()
        self.interruption = InterruptionDetector()
        self._current_mood: str = "neutral"

    def set_mood(self, mood: str) -> None:
        self._current_mood = mood.lower()

    def get_reflex_phrase(self) -> str:
        """Mengambil frasa refleks bangun di bawah 50 ms sesuai mood."""
        phrases = REFLEX_PHRASES.get(self._current_mood, REFLEX_PHRASES["neutral"])
        return phrases[0]

    def process_audio_frame(
        self,
        samples: Sequence[float],
        score_hint: float | None = None,
        keyword_hint: str | None = None,
        embedding_hint: Sequence[float] | None = None,
    ) -> dict[str, Any]:
        """Memproses satu frame audio melalui kaskade VAD -> Wake Word -> Speaker ID."""
        start_t = time.perf_counter()

        # 1. VAD Gatekeeper
        vad_state = self.vad.process_window(samples)

        # 2. Wake Word Detection
        wake_verdict = self.wake_detector.process_frame(
            samples, score_hint=score_hint, keyword_hint=keyword_hint
        )

        speaker_verdict: SpeakerVerdict | None = None
        reflex_phrase: str = ""

        if wake_verdict.detected:
            # Emit refleks cepat (< 50 ms)
            reflex_phrase = self.get_reflex_phrase()

            # Verifikasi Speaker ID jika embedding disertakan
            if embedding_hint:
                speaker_verdict = self.speaker_id.verify(embedding_hint)
            else:
                speaker_verdict = SpeakerVerdict(
                    status=SpeakerStatus.UNKNOWN,
                    similarity=0.0,
                    speaker_id="unverified",
                )

            # Terbitkan event ke EventBus
            if self.event_bus:
                self.event_bus.publish(
                    Event(
                        namespace=OrganNamespace.EAR.value,
                        event_type="ear.wake_word",
                        source="blood_hearing",
                        payload={
                            "keyword": wake_verdict.keyword,
                            "confidence": wake_verdict.confidence,
                            "latency_ms": wake_verdict.latency_ms,
                            "reflex": reflex_phrase,
                        },
                    )
                )
                if speaker_verdict:
                    self.event_bus.publish(
                        Event(
                            namespace=OrganNamespace.EAR.value,
                            event_type="ear.speaker",
                            source="blood_hearing",
                            payload={
                                "status": speaker_verdict.status.value,
                                "similarity": speaker_verdict.similarity,
                                "speaker_id": speaker_verdict.speaker_id,
                            },
                        )
                    )

        # 3. Interruption check jika Ruka sedang berbicara
        interrupted, int_lat = self.interruption.process_chunk(samples)
        if interrupted and self.event_bus:
            self.event_bus.publish(
                Event(
                    namespace=OrganNamespace.EAR.value,
                    event_type="voice.stop_speaking",
                    source="blood_hearing",
                    payload={"reason": "barge_in", "latency_ms": int_lat},
                )
            )

        total_latency_ms = (time.perf_counter() - start_t) * 1000.0

        return {
            "vad_state": vad_state.value,
            "wake_detected": wake_verdict.detected,
            "keyword": wake_verdict.keyword,
            "reflex_phrase": reflex_phrase,
            "speaker_status": speaker_verdict.status.value if speaker_verdict else None,
            "interrupted": interrupted,
            "latency_ms": total_latency_ms,
        }

    def process_transcript(self, raw_text: str) -> str:
        """Normalisasi transkripsi ASR dan penerbitan event utterance."""
        normalized = normalize_text(raw_text)
        if self.event_bus and normalized:
            self.event_bus.publish(
                Event(
                    namespace=OrganNamespace.EAR.value,
                    event_type="ear.utterance",
                    source="blood_hearing",
                    payload={"text": normalized, "raw": raw_text},
                )
            )
        return normalized
