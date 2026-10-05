# -*- coding: utf-8 -*-
"""Command Palette & Unified Action Registry (FR-OS-04).

Menyediakan palet perintah Ctrl+Spasi:
- Satu-satunya jendela yang diizinkan mengambil fokus
- Pencarian samar (fuzzy search) dengan batas maksimal 8 hasil
- Registri aksi tunggal untuk palet perintah, mini menu, dan tray bar
"""
from __future__ import annotations

from dataclasses import dataclass
import difflib
from typing import Any, Callable, Optional


@dataclass(frozen=True)
class PaletteAction:
    action_id: str
    title: str
    category: str
    shortcut: str = ""
    handler: Optional[Callable[[], Any]] = None


class CommandPaletteRegistry:
    def __init__(self) -> None:
        self._actions: dict[str, PaletteAction] = {}
        self.is_open: bool = False

    def register(self, action: PaletteAction) -> None:
        self._actions[action.action_id] = action

    def open_palette(self) -> None:
        self.is_open = True

    def close_palette(self) -> None:
        self.is_open = False

    def search(self, query: str, limit: int = 8) -> list[PaletteAction]:
        """Pencarian samar (fuzzy) terhadap title dan action_id, mengembalikan maks 8 hasil."""
        if not query or not query.strip():
            # Kembalikan 8 aksi pertama
            return list(self._actions.values())[:limit]

        q = query.strip().lower()
        scored: list[tuple[float, PaletteAction]] = []

        for act in self._actions.values():
            target_text = f"{act.title} {act.category} {act.action_id}".lower()
            # 1. Exact substring match
            if q in target_text:
                score = 1.0 + (len(q) / len(target_text))
            else:
                # 2. Difflib similarity ratio
                score = difflib.SequenceMatcher(None, q, target_text).ratio()

            if score > 0.3:
                scored.append((score, act))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [act for _, act in scored[:limit]]

    def execute(self, action_id: str) -> Any:
        action = self._actions.get(action_id)
        if action and action.handler:
            res = action.handler()
            self.close_palette()
            return res
        return None
