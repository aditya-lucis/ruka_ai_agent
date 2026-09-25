# -*- coding: utf-8 -*-
"""Live API v0.3.1 — sesi suara dua arah + manajemen siklus sesi.
PERBAIKAN Patch 1.1:
BUG A — `response.transcript` tidak ada.
    LiveServerMessage (SDK 2.22.0) TIDAK punya field `transcript`.
    Akses yang benar: response.server_content.input_transcription.text
    (types.Transcription: text, finished, language_code, speaker_label,
    words).
BUG B — affective dialog dipaksa pada model yang tidak mendukung.
    gemini-3.1-flash-live-preview + enable_affective_dialog=True tanpa
    deteksi. Dok. resmi: hanya 2.5 Flash Live (+ api_version v1beta).
    Kini: CapabilityRegistry.live_config_extras() -> deteksi -> fallback.
HARDENING tambahan:
    - go_away: server memberi tahu sambungan akan diputus (time_left).
    - session_resumption: simpan handle; koneksi baru melanjutkan sesi
      (token valid 2 jam setelah sesi terakhir berakhir).
    - context_window_compression: sliding window -> sesi lebih panjang.
    - interrupted: deteksi user menyela (VAD) -> hentikan pemutaran.
    - generation_complete: tanda model selesai pada giliran ini.
    - Pola "kirim Blob kosong = EOF" DIHAPUS: akhir giliran ditentukan
      VAD (silence_duration_ms), bukan blob kosong.
"""
from __future__ import annotations
import asyncio
import logging
from dataclasses import dataclass, field
from typing import AsyncIterator, Callable
from google import genai
from google.genai import types
from src.capability.registry import CapabilityRegistry

logger = logging.getLogger("ruka.live")
LiveCallback = Callable[[bytes], None]
TranscriptCallback = Callable[[str], None]

@dataclass
class LiveLimits:
    """Batas yang diakui (dok. resmi — jangan ditembak melewati)."""
    session_audio_seconds: int = 15 * 60      # sesi audio-only: 15 menit
    connection_seconds: int = 10 * 60         # umur KONEKSI: ~10 menit
    reconnect_budget: int = 3                 # maksimum retry per run
    backoff_base: float = 2.0                 # detik; 0 = tanpa jeda (test)

@dataclass
class LiveRuntimeState:
    """Status yang bisa diamati dari luar (untuk trace & test)."""
    received_audio_chunks: int = 0
    received_transcripts: int = 0
    interrupted: int = 0
    go_away_seen: bool = False
    reconnects: int = 0
    last_resumption_handle: str | None = None
    warnings: list[str] = field(default_factory=list)

class LiveSession:
    """Satu percakapan live (satu koneksi). Kirim mic; terima audio +
    transkrip; patuhi batas sesi; laporkan go_away."""
    def __init__(self, client: genai.Client, live_model: str,
                 system_instruction: str,
                 registry: CapabilityRegistry,
                 affective: bool = False) -> None:
        self._client = client
        self._model = live_model
        self._system = system_instruction
        self._registry = registry
        self._affective = affective
        self.state = LiveRuntimeState()

    def _build_config(self, resumption_handle: str | None
                      ) -> types.LiveConnectConfig:
        extras = self._registry.live_config_extras(
            self._model, affective=self._affective)
        if self._affective and not extras:
            # fallback terjadi di registry (warning sudah dicatat) —
            # simpan jejaknya untuk trace aplikasi
            self.state.warnings.append(
                "affective_dialog fallback: tidak didukung model/SDK")
        return types.LiveConnectConfig(
            response_modalities=["AUDIO"],
            system_instruction=self._system,
            input_audio_transcription={},
            # Sesi lebih panjang + pemulihan konteks (dok. Session Mgmt):
            context_window_compression=types.ContextWindowCompressionConfig(
                sliding_window=types.SlidingWindow()),
            session_resumption=types.SessionResumptionConfig(
                handle=resumption_handle),     # None = sesi baru
            thinking_config=types.ThinkingConfig(
                thinking_level="low"),         # default 'minimal' = latensi
            **extras,                          # affective bila didukung
        )

    async def run(self, mic_chunks: AsyncIterator[bytes],
                  on_audio: LiveCallback,
                  on_transcript: TranscriptCallback) -> None:
        """Satu koneksi penuh. Selesai normal saat iterator mic habis.
        go_away / drop koneksi tidak ditangani di sini — itu urusan
        LiveSessionManager (di atasnya) yang memegang handle resumption.
        """
        config = self._build_config(self.state.last_resumption_handle)
        async with self._client.aio.live.connect(model=self._model,
                                                 config=config) as session:
            producer = asyncio.create_task(self._pump_mic(session, mic_chunks))
            try:
                async for message in session.receive():
                    self._dispatch(message, on_audio, on_transcript)
            finally:
                producer.cancel()
                await asyncio.gather(producer, return_exceptions=True)

    def _dispatch(self, message: types.LiveServerMessage,
                  on_audio: LiveCallback,
                  on_transcript: TranscriptCallback) -> None:
        # (1) GoAway — sambungan akan diputus; manager harus bersiap.
        if message.go_away is not None:
            self.state.go_away_seen = True
            time_left = getattr(message.go_away, "time_left", None)
            self.state.warnings.append(
                f"go_away: server memutus dalam ~{time_left}")
            logger.warning("Live go_away: time_left=%s", time_left)
            return
        # (2) Resumption update — panen handle untuk koneksi berikutnya.
        sru = message.session_resumption_update
        if sru is not None and getattr(sru, "new_handle", None):
            self.state.last_resumption_handle = sru.new_handle
        # (3) Konten server: audio keluar, transkrip, interupsi, selesai.
        sc = message.server_content
        if sc is None:
            return
        if sc.interrupted:
            self.state.interrupted += 1
            # aplikasi menghentikan pemutaran buffer (callback polos)
            on_audio(b"")                     # sinyal 'stop playback'
        if sc.input_transcription and sc.input_transcription.text:
            self.state.received_transcripts += 1
            on_transcript(sc.input_transcription.text)
        if sc.model_turn:
            for part in sc.model_turn.parts:
                if part.inline_data:
                    self.state.received_audio_chunks += 1
                    on_audio(part.inline_data.data)   # PCM 24 kHz
        if sc.generation_complete:
            pass                               # giliran model selesai

    @staticmethod
    async def _pump_mic(session, mic_chunks: AsyncIterator[bytes]) -> None:
        """Stream mic ke server. TANPA blob-EOF: akhir giliran ditentukan
        VAD server (silence_duration_ms) — bukan pesan klien."""
        async for chunk in mic_chunks:
            await session.send_realtime_input(
                audio=types.Blob(data=chunk,
                                 mime_type="audio/pcm;rate=16000"))

class LiveSessionManager:
    """Pemilik siklus hidup live: connect, pantau go_away, reconnect.
    Dipisahkan sengaja dari Agent Orchestrator (PART 13): orchestrator
    tidak boleh tahu soal websocket, dan sesi live tidak boleh tahu
    soal budget agent. Manager menyimpan resumption handle antar
    koneksi (token sah 2 jam) dan mematuhi anggaran reconnect.
    """
    def __init__(self, client: genai.Client, live_model: str,
                 registry: CapabilityRegistry,
                 limits: LiveLimits | None = None) -> None:
        self._client = client
        self._model = live_model
        self._registry = registry
        self._limits = limits or LiveLimits()

    async def converse(self, system_instruction: str,
                       mic_chunks_factory: Callable[[], AsyncIterator[bytes]],
                       on_audio: LiveCallback,
                       on_transcript: TranscriptCallback,
                       affective: bool = False) -> LiveRuntimeState:
        """Jalankan hingga mic selesai ATAU anggaran reconnect habis.
        mic_chunks_factory dipanggil ulang per koneksi — pemanggil
        memutuskan apakah buffer mic yang sama dikirim ulang (mis.
        hanya sisa yang belum terkirim) atau diganti sumber baru.
        """
        session = LiveSession(self._client, self._model, system_instruction,
                              self._registry, affective=affective)
        connection_attempt = 0                # 1 = koneksi awal
        while True:
            connection_attempt += 1
            try:
                await session.run(mic_chunks_factory(), on_audio,
                                  on_transcript)
                return session.state          # selesai normal
            except asyncio.CancelledError:
                raise                          # batal = permintaan eksplisit
            except Exception as exc:           # noqa: BLE001 — dibatasi budget
                session.state.reconnects = connection_attempt - 1
                if connection_attempt > self._limits.reconnect_budget:
                    logger.error(
                        "anggaran reconnect habis setelah %d koneksi "
                        "(%s terakhir) — berhenti terhormat",
                        connection_attempt, type(exc).__name__)
                    return session.state
                handle = session.state.last_resumption_handle
                logger.warning(
                    "koneksi live putus (%s); reconnect %d/%d handle=%s",
                    type(exc).__name__, session.state.reconnects,
                    self._limits.reconnect_budget,
                    "ada" if handle else "tanpa konteks")
                await asyncio.sleep(
                    min(self._limits.backoff_base ** session.state.reconnects,
                        8.0))
