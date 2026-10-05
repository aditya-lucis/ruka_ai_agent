# -*- coding: utf-8 -*-
"""Visual Memory without Raw Pixels (FR-MC-13).

Menyimpan memori visual sebagai deskripsi teks dan hash (~400 byte) tanpa piksel mentah:
- Kunci visual berupa hash jenis visual
- Kembar/duplikat menimpa (overwrite), tidak menumpuk
"""
from __future__ import annotations

import hashlib
import time
from typing import Any


class VisualMemory:
    def __init__(self) -> None:
        # key_hash -> {description, timestamp, metadata}
        self._memory_store: dict[str, dict[str, Any]] = {}

    def store_impression(
        self,
        visual_type: str,
        description: str,
        metadata: dict[str, Any] | None = None,
    ) -> str:
        """Menyimpan jejak visual berukuran ~400 byte."""
        # Buat hash representatif dari jenis visual dan deskripsi pokok
        content_for_hash = f"{visual_type}:{description.strip()[:100]}"
        v_hash = hashlib.sha256(content_for_hash.encode("utf-8")).hexdigest()[:16]

        self._memory_store[v_hash] = {
            "type": visual_type,
            "description": description[:300],  # Dibatasi ~300-400 byte
            "timestamp": time.time(),
            "metadata": metadata or {},
        }
        return v_hash

    def get_recent_impressions(self, limit: int = 5) -> list[dict[str, Any]]:
        """Mengambil impresi visual terbaru."""
        sorted_items = sorted(self._memory_store.values(), key=lambda x: x["timestamp"], reverse=True)
        return sorted_items[:limit]

    def __len__(self) -> int:
        return len(self._memory_store)
