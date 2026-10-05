# -*- coding: utf-8 -*-
"""Multimodal Input Router (FR-MC-02).

Router 6 pintu masuk:
- Suara, kamera, layar, berkas, terminal, gestur
- Prioritas suara SELALU menang
- Kandidat kalah diturunkan menjadi konteks latar belakang (tidak dibuang)
- Deduplikasi isi dalam jendela 30 detik (kecuali ucapan pengguna)
"""
from __future__ import annotations

import collections
import time
from typing import Any

from src.converse.models import InputItem, ModalityType


class InputRouter:
    def __init__(self, dedup_window_s: float = 30.0) -> None:
        self.dedup_window_s = dedup_window_s
        self._recent_hashes: collections.OrderedDict[str, float] = collections.OrderedDict()

    def _is_duplicate(self, item: InputItem) -> bool:
        # Ucapan pengguna (VOICE) tidak pernah dideduplikasi
        if item.modality == ModalityType.VOICE:
            return False

        content_str = str(item.content) if not isinstance(item.content, str) else item.content
        key = f"{item.modality.value}:{hash(content_str)}"
        now = time.time()

        # Bersihkan entri kedaluwarsa
        cutoff = now - self.dedup_window_s
        expired = [k for k, t in self._recent_hashes.items() if t < cutoff]
        for k in expired:
            del self._recent_hashes[k]

        if key in self._recent_hashes:
            return True

        self._recent_hashes[key] = now
        return False

    def route_inputs(
        self,
        incoming: list[InputItem],
    ) -> tuple[InputItem | None, list[InputItem]]:
        """Memilah masukan: pemenang utama (suara diutamakan) dan konteks latar belakang.

        Returns:
            tuple (primary_input, background_contexts)
        """
        if not incoming:
            return None, []

        # Filter duplikat 30 detik
        valid_items = [item for item in incoming if not self._is_duplicate(item)]
        if not valid_items:
            return None, []

        # 1. Cari suara (voice) sebagai pemenang prioritas mutlak
        voice_item = next((item for item in valid_items if item.modality == ModalityType.VOICE), None)

        if voice_item:
            primary = voice_item
            background = [item for item in valid_items if item != voice_item]
        else:
            # Jika tidak ada suara, ambil item pertama sebagai penggerak utama
            primary = valid_items[0]
            background = valid_items[1:]

        return primary, background
