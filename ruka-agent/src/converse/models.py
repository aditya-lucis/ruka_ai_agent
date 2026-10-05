# -*- coding: utf-8 -*-
"""Multimodal Conversation Models & Dataclasses (FR-MC).

Kontrak dataclass beku untuk percakapan multimodal Ruka / Project Noctis:
- 6 pintu modalitas (suara, kamera, layar, berkas, terminal, gestur)
- 3 state percakapan: LISTENING, THINKING, SPEAKING
- Alokasi prompt Matryoshka 3.000 token
- Respons dua kanal (suara linear-fana maks 2 kalimat vs layar paralel-abadi)
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Tuple, Optional


class ModalityType(str, Enum):
    VOICE = "voice"          # Prioritas tertinggi
    CAMERA = "camera"
    SCREEN = "screen"
    FILE = "file"
    TERMINAL = "terminal"
    GESTURE = "gesture"


class ConversationState(str, Enum):
    LISTENING = "listening"
    THINKING = "thinking"
    SPEAKING = "speaking"


@dataclass(frozen=True)
class InputItem:
    modality: ModalityType
    content: str
    timestamp: float
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class MatryoshkaPrompt:
    """Prompt terpadu beranggaran 3.000 token dari 6 blok tetap (FR-MC-03)."""
    persona_block: str           # ~400 token
    memory_block: str            # ~500 token
    modality_context_block: str  # ~600 token
    user_transcript_block: str   # ~700 token (KERAMAT: pantang dipangkas)
    history_block: str           # ~600 token
    slack_block: str             # ~200 token
    estimated_total_tokens: int = 3000

    def assemble(self) -> str:
        """Menggabungkan seluruh blok menjadi prompt tunggal."""
        parts = [
            f"[PERSONA & DIRECTIVE]\n{self.persona_block}",
            f"[MEMORY PALACE RECALL]\n{self.memory_block}",
            f"[ENVIRONMENT & MODALITIES]\n{self.modality_context_block}",
            f"[CONVERSATION HISTORY]\n{self.history_block}",
            f"[USER UTTERANCE (SACRED)]\n{self.user_transcript_block}",
        ]
        if self.slack_block:
            parts.append(f"[ADDITIONAL CONTEXT]\n{self.slack_block}")
        return "\n\n".join(parts)


@dataclass(frozen=True)
class DualResponse:
    """Jawaban terbelah dua kanal (FR-MC-07)."""
    voice_text: str          # Maksimal 2 kalimat inti untuk suara linear-fana
    screen_markdown: str     # Markdown utuh dengan kode, tabel, dan link untuk layar paralel-abadi
    latency_ms: float = 0.0
