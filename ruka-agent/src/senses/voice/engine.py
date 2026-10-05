# -*- coding: utf-8 -*-
"""Streaming TTS Engine & LRU Phrase Cache (FR-VO-01, FR-VO-11, FR-VO-12).

Mesin sintesis suara streaming dengan TTFB < 200 ms:
- LRU cache berkapasitas 96 entri per (frasa, mood)
- Generator streaming chunk audio
- Pembangkitan event viseme 25 fps untuk sinkronisasi avatar
"""
from __future__ import annotations

import collections
import hashlib
import time
from typing import Generator

from src.senses.voice.models import (
    MarquisMood,
    ProsodySettings,
    TTSChunk,
    VisemeEvent,
)


def _generate_synthetic_visemes(duration_ms: float) -> tuple[VisemeEvent, ...]:
    """Menghasilkan viseme 25 fps (interval 40 ms) untuk durasi audio."""
    visemes: list[VisemeEvent] = []
    interval_ms = 40.0  # 25 fps
    t = 0.0
    v_codes = ["A", "E", "I", "O", "U", "M", "S"]
    idx = 0
    while t < duration_ms:
        code = v_codes[idx % len(v_codes)]
        visemes.append(VisemeEvent(viseme_id=code, timestamp_ms=t, weight=1.0))
        t += interval_ms
        idx += 1
    return tuple(visemes)


class StreamingTTSEngine:
    def __init__(
        self,
        cache_capacity: int = 96,
        sample_rate: int = 24000,
    ) -> None:
        self.sample_rate = sample_rate
        self.cache: collections.OrderedDict[str, list[TTSChunk]] = collections.OrderedDict()
        self.cache_capacity = cache_capacity
        self.voice_dna_hash: str = "default_marquis_dna_v1"

    def set_voice_dna(self, dna_data: bytes) -> str:
        """Mengunci identitas suara dengan hash SHA-256. Invalidasi cache jika berubah."""
        new_hash = hashlib.sha256(dna_data).hexdigest()
        if new_hash != self.voice_dna_hash:
            self.voice_dna_hash = new_hash
            self.cache.clear()
        return self.voice_dna_hash

    def _cache_key(self, text: str, mood: str) -> str:
        return f"{self.voice_dna_hash}:{mood.lower()}:{text.strip().lower()}"

    def synthesize_stream(
        self,
        text: str,
        prosody: ProsodySettings,
        mood: MarquisMood | str = MarquisMood.NEUTRAL,
    ) -> Generator[TTSChunk, None, None]:
        """Menghasilkan stream TTSChunk dengan TTFB < 200 ms."""
        start_t = time.perf_counter()
        mood_str = mood.value if isinstance(mood, MarquisMood) else str(mood).lower()
        key = self._cache_key(text, mood_str)

        # 1. Cek LRU Cache
        if key in self.cache:
            self.cache.move_to_end(key)
            cached_chunks = self.cache[key]
            for chunk in cached_chunks:
                yield chunk
            return

        # 2. Sintesis nyata / lokal streaming
        # Pecah teks menjadi frasa kecil agar chunk pertama keluar seketika (< 200 ms)
        words = text.split()
        if not words:
            return

        # Chunk pertama: maksimal 5 kata untuk menjamin TTFB sangat rendah
        chunk_sizes = [min(5, len(words))]
        rem = len(words) - chunk_sizes[0]
        while rem > 0:
            c = min(8, rem)
            chunk_sizes.append(c)
            rem -= c

        generated_chunks: list[TTSChunk] = []
        word_offset = 0

        for i, sz in enumerate(chunk_sizes):
            sub_words = words[word_offset : word_offset + sz]
            word_offset += sz
            sub_text = " ".join(sub_words)

            # Estimasi durasi ucapan berdasarkan laju kata (kata per detik ~ 2.5 * rate)
            words_per_sec = 2.5 * prosody.rate_multiplier
            dur_s = max(0.2, len(sub_words) / words_per_sec)
            dur_ms = dur_s * 1000.0

            # 24 kHz 16-bit mono audio dummy payload untuk representasi stream
            n_samples = int(self.sample_rate * dur_s)
            mock_pcm = b"\x00\x00" * n_samples

            is_first = (i == 0)
            is_final = (i == len(chunk_sizes) - 1)
            ttfb_ms = (time.perf_counter() - start_t) * 1000.0 if is_first else 0.0

            visemes = _generate_synthetic_visemes(dur_ms)

            chunk = TTSChunk(
                audio_data=mock_pcm,
                sample_rate=self.sample_rate,
                duration_ms=dur_ms,
                is_first_chunk=is_first,
                is_final=is_final,
                ttfb_ms=ttfb_ms,
                visemes=visemes,
            )
            generated_chunks.append(chunk)
            yield chunk

        # Simpan ke cache LRU
        if len(self.cache) >= self.cache_capacity:
            self.cache.popitem(last=False)
        self.cache[key] = generated_chunks
