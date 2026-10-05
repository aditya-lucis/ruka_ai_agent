# -*- coding: utf-8 -*-
"""Context Fuser & Matryoshka 3.000 Token Prompt (FR-MC-03).

Melebur 6 blok konteks menjadi satu prompt beranggaran tepat 3.000 token:
- Blok 1: Persona & Direktif (~400 token)
- Blok 2: Memory Palace Recall (~500 token)
- Blok 3: Active Modality Context (~600 token)
- Blok 4: Transkrip Pengguna (KERAMAT: pantang dipangkas, ~700 token)
- Blok 5: Riwayat Percakapan (~600 token)
- Blok 6: Alokasi Matryoshka / Slack (~200 token)
"""
from __future__ import annotations

from typing import Sequence
from src.converse.models import InputItem, MatryoshkaPrompt


def _rough_token_count(text: str) -> int:
    """Estimasi cepat jumlah token (1 kata ~ 1.3 token)."""
    if not text:
        return 0
    words = len(text.split())
    return max(1, int(words * 1.3))


def _truncate_to_tokens(text: str, max_tokens: int) -> str:
    """Memotong teks dari belakang agar muat dalam batas token."""
    words = text.split()
    max_words = int(max_tokens / 1.3)
    if len(words) <= max_words:
        return text
    return " ".join(words[:max_words]) + " [...]"


class ContextFuser:
    MAX_TOTAL_BUDGET = 3000

    def __init__(
        self,
        persona_directive: str = "RUKA: Kucing vampir bangsawan Marquis of Trendamis, loyal mutlak kepada Young Lord.",
    ) -> None:
        self.persona_directive = persona_directive

    def fuse_context(
        self,
        user_utterance: str,
        memory_recalls: Sequence[str] = (),
        background_modalities: Sequence[InputItem] = (),
        history_turns: Sequence[str] = (),
    ) -> MatryoshkaPrompt:
        """Menyusun MatryoshkaPrompt beranggaran 3.000 token."""
        # 1. User Transcript adalah BLOK KERAMAT (tidak pernah dipangkas)
        user_text = user_utterance.strip()
        user_tokens = _rough_token_count(user_text)

        # Sisa anggaran yang tersedia untuk blok lain
        remaining_budget = max(500, self.MAX_TOTAL_BUDGET - user_tokens)

        # 2. Persona Block (~400 token)
        persona_block = _truncate_to_tokens(self.persona_directive, 400)
        remaining_budget -= _rough_token_count(persona_block)

        # 3. Memory Block (~500 token)
        mem_text = "\n".join(f"- {m}" for m in memory_recalls) if memory_recalls else "Tidak ada memori terkait."
        mem_budget = min(500, int(remaining_budget * 0.3))
        memory_block = _truncate_to_tokens(mem_text, mem_budget)
        remaining_budget -= _rough_token_count(memory_block)

        # 4. Modality Context Block (~600 token)
        mod_lines = [f"[{item.modality.value.upper()}]: {item.content}" for item in background_modalities]
        mod_text = "\n".join(mod_lines) if mod_lines else "Tidak ada sinyal modalitas latar belakang."
        mod_budget = min(600, int(remaining_budget * 0.35))
        modality_context_block = _truncate_to_tokens(mod_text, mod_budget)
        remaining_budget -= _rough_token_count(modality_context_block)

        # 5. History Block (~600 token)
        hist_text = "\n".join(history_turns) if history_turns else "Awal percakapan baru."
        hist_budget = min(600, remaining_budget - 100)
        history_block = _truncate_to_tokens(hist_text, hist_budget)
        remaining_budget -= _rough_token_count(history_block)

        # 6. Slack Block (Sisa jatah mengalir ke sini)
        slack_block = f"Status: Otonomi Aktif. Sisa napas: {max(0, remaining_budget)} token."

        total_est = (
            _rough_token_count(persona_block)
            + _rough_token_count(memory_block)
            + _rough_token_count(modality_context_block)
            + user_tokens
            + _rough_token_count(history_block)
            + _rough_token_count(slack_block)
        )

        return MatryoshkaPrompt(
            persona_block=persona_block,
            memory_block=memory_block,
            modality_context_block=modality_context_block,
            user_transcript_block=user_text,
            history_block=history_block,
            slack_block=slack_block,
            estimated_total_tokens=total_est,
        )
