# -*- coding: utf-8 -*-
"""Response Splitter for Dual Channels (FR-MC-07).

Membagi jawaban otak ke dalam dua kanal:
1. Kanal Suara (Voice): Linear-fana, maksimal 2 kalimat inti, tanpa blok kode atau tabel
2. Kanal Layar (Panel UI): Paralel-abadi, mempertahankan blok kode, tabel, dan tautan sebagai atom utuh
Kode adalah ATOM yang diangkat utuh sebelum pemotongan kalimat.
"""
from __future__ import annotations

import re
from src.converse.models import DualResponse


class ResponseSplitter:
    def split_response(self, full_text: str, latency_ms: float = 0.0) -> DualResponse:
        """Memecah teks tanggapan menjadi kanal suara dan kanal layar."""
        if not full_text or not full_text.strip():
            return DualResponse(voice_text="", screen_markdown="", latency_ms=latency_ms)

        screen_markdown = full_text.strip()

        # 1. Angkat kode blok sebagai atom utuh (hapus dari teks suara)
        text_without_code = re.sub(r"```[\s\S]*?```", "", screen_markdown)

        # 2. Hapus tabel markdown dan tautan raw dari teks suara
        text_clean = re.sub(r"\|[^\n]+\|", "", text_without_code)
        text_clean = re.sub(r"\[([^\]]+)\]\([^\)]+\)", r"\1", text_clean)  # Ubah [teks](url) jadi teks

        # 3. Normalisasi spasi dan baris
        lines = [line.strip() for line in text_clean.splitlines() if line.strip()]
        flat_text = " ".join(lines)

        # 4. Ambil maksimal 2 kalimat pertama untuk suara
        sentences = re.split(r"(?<=[.!?])\s+", flat_text)
        voice_sentences = [s.strip() for s in sentences if s.strip()]

        if len(voice_sentences) > 2:
            voice_text = " ".join(voice_sentences[:2])
        elif voice_sentences:
            voice_text = " ".join(voice_sentences)
        else:
            voice_text = "Tugas telah diselesaikan, My Lord."

        return DualResponse(
            voice_text=voice_text,
            screen_markdown=screen_markdown,
            latency_ms=latency_ms,
        )
