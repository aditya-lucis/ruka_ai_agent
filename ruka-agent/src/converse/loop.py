# -*- coding: utf-8 -*-
"""Conversation Loop & Strict Single-Brain-Call Enforcement (FR-MC-01, FR-MC-05, FR-MC-06).

Alur percakapan multimodal terpadu 5 tahap:
1. Router masukan 6 pintu (suara selalu prioritas)
2. Pelebur konteks Matryoshka 3.000 token
3. Satu panggilan otak tunggal (tepat 1 panggilan per giliran)
4. Pembagi jawaban dua kanal (suara maks 2 kalimat vs layar)
5. Distribusi ke kanal suara dan panel
Barge-in interupsi < 300 ms dari SPEAKING ke LISTENING.
"""
from __future__ import annotations

import time
from typing import Any, Callable

from src.converse.fuser import ContextFuser
from src.converse.latency import LatencyMeter
from src.converse.models import (
    ConversationState,
    DualResponse,
    InputItem,
    ModalityType,
)
from src.converse.router import InputRouter
from src.converse.splitter import ResponseSplitter
from src.converse.visual_memory import VisualMemory
from src.gateway.events import Event, EventBus, OrganNamespace


class SingleBrainCallViolation(Exception):
    """Dilempar jika ada pelanggaran hukum persis 1 panggilan otak per giliran."""
    pass


class ConversationLoop:
    def __init__(
        self,
        event_bus: EventBus | None = None,
        memory_palace: Any | None = None,
        persona_directive: str = "RUKA: Kucing vampir bangsawan Marquis of Trendamis, loyal mutlak kepada Young Lord.",
    ) -> None:
        self.event_bus = event_bus
        self.memory_palace = memory_palace
        self.state = ConversationState.LISTENING

        self.router = InputRouter()
        self.fuser = ContextFuser(persona_directive=persona_directive)
        self.splitter = ResponseSplitter()
        self.latency_meter = LatencyMeter()
        self.visual_memory = VisualMemory()

        self._turn_history: list[str] = []

    def set_state(self, new_state: ConversationState) -> None:
        self.state = new_state
        if self.event_bus:
            self.event_bus.publish(
                Event(
                    namespace=OrganNamespace.CONVERSE.value,
                    event_type="converse.state",
                    source="conversation_loop",
                    payload={"state": new_state.value},
                )
            )

    def trigger_barge_in(self) -> float:
        """Menangani interupsi pengguna: transisi ke LISTENING di bawah 300 ms."""
        start_t = time.perf_counter()
        if self.state == ConversationState.SPEAKING:
            self.set_state(ConversationState.LISTENING)
        latency_ms = (time.perf_counter() - start_t) * 1000.0
        return latency_ms

    def execute_turn(
        self,
        inputs: list[InputItem],
        brain_caller: Callable[[str], str],
    ) -> DualResponse:
        """Menjalankan satu giliran percakapan lengkap dengan penegakan 1 panggilan otak."""
        start_t = time.perf_counter()

        # 1. Tahap 1: Router Masukan
        primary, background = self.router.route_inputs(inputs)
        if not primary:
            return DualResponse(voice_text="", screen_markdown="")

        # 2. Tahap 2: Memory Recall & Context Fusion
        self.set_state(ConversationState.THINKING)
        try:
            recalls = []
            if self.memory_palace:
                try:
                    res = self.memory_palace.recall(primary.content, top_k=3)
                    if isinstance(res, list):
                        recalls = [r.content if hasattr(r, "content") else str(r) for r in res]
                    elif isinstance(res, dict):
                        recalls = [r.get("content", "") for r in res.get("results", [])]
                except Exception:
                    pass

            prompt = self.fuser.fuse_context(
                user_utterance=primary.content,
                memory_recalls=recalls,
                background_modalities=background,
                history_turns=self._turn_history[-4:],
            )

            assembled_prompt = prompt.assemble()

            # 3. Tahap 3: Panggilan Otak Tunggal (Disiplin Keras: Tepat 1 Kali)
            call_count = 0

            def wrapped_caller(p: str) -> str:
                nonlocal call_count
                call_count += 1
                if call_count > 1:
                    raise SingleBrainCallViolation(f"Haram: Terdeteksi {call_count} panggilan otak dalam satu giliran!")
                return brain_caller(p)

            brain_start = time.perf_counter()
            raw_response = wrapped_caller(assembled_prompt)
            brain_latency_ms = (time.perf_counter() - brain_start) * 1000.0

            if call_count != 1:
                raise SingleBrainCallViolation(f"Giliran gagal: jumlah panggilan otak adalah {call_count}, harus tepat 1.")

            # 4. Tahap 4: Pembagian Jawaban Dua Kanal
            self.set_state(ConversationState.SPEAKING)
            total_latency_ms = (time.perf_counter() - start_t) * 1000.0

            dual = self.splitter.split_response(raw_response, latency_ms=total_latency_ms)

            # Catat metrik latensi
            self.latency_meter.record_turn_latency(
                asr_ms=50.0,  # Estimasi ASR lokal
                brain_ttft_ms=brain_latency_ms,
                tts_ttfb_ms=80.0,
                network_buffer_ms=20.0,
            )

            # Simpan ke riwayat percakapan
            self._turn_history.append(f"User: {primary.content}")
            self._turn_history.append(f"Ruka: {dual.voice_text}")

            # Terbitkan event giliran ke EventBus
            if self.event_bus:
                self.event_bus.publish(
                    Event(
                        namespace=OrganNamespace.CONVERSE.value,
                        event_type="converse.turn",
                        source="conversation_loop",
                        payload={
                            "user_input": primary.content,
                            "voice_text": dual.voice_text,
                            "screen_length": len(dual.screen_markdown),
                            "latency_ms": total_latency_ms,
                        },
                    )
                )

            return dual
        finally:
            self.set_state(ConversationState.LISTENING)
