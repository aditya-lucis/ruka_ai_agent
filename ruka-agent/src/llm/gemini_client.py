from __future__ import annotations

import logging
from google import genai
from google.genai import types

from src.config import Config

logger = logging.getLogger(__name__)

class GeminiClient:
    """Pembungkus di atas SDK resmi Google GenAI.
    Menghasilkan teks real-time (<3s) menggunakan model optimal.
    """

    def __init__(self, cfg: Config):
        self.cfg = cfg
        self.client = genai.Client(api_key=cfg.api_key)
        self.last_used_model: str | None = None

    def complete(
        self,
        prompt: str | list[types.Content],
        *,
        system_instruction: str = "",
        temperature: float | None = None,
        model_tier: str | None = None,
    ) -> str:
        """Generate teks (single-turn atau multi-turn) dengan latensi rendah real-time dan model routing."""
        temp = temperature if temperature is not None else getattr(self.cfg, "temperature", 0.7)
        config = types.GenerateContentConfig(
            system_instruction=system_instruction or None,
            temperature=temp,
        )

        configured_model = getattr(self.cfg, "model", "")
        cached_model = getattr(self, "last_used_model", None)
        if model_tier == "fast":
            raw_candidates = [
                cached_model,
                "gemini-2.5-flash",
                "gemini-2.0-flash",
                "gemini-1.5-flash",
                "gemini-3.5-flash-lite",
                "gemini-flash-latest",
                "gemini-flash-lite-latest",
                configured_model,
            ]
        elif model_tier == "strong":
            raw_candidates = [
                cached_model,
                configured_model,
                "gemini-3.6-flash-medium",
                "gemini-2.5-pro",
                "gemini-1.5-pro",
                "gemini-2.5-flash",
                "gemini-2.0-flash",
                "gemini-flash-latest",
            ]
        else:
            raw_candidates = [
                cached_model,
                configured_model,
                "gemini-2.5-flash",
                "gemini-2.0-flash",
                "gemini-1.5-flash",
                "gemini-3.5-flash-lite",
                "gemini-flash-latest",
                "gemini-flash-lite-latest",
            ]

        model_candidates = []
        for m in raw_candidates:
            if m and m not in model_candidates:
                model_candidates.append(m)

        last_err = None
        for m in model_candidates:
            try:
                res = self.client.models.generate_content(
                    model=m,
                    contents=prompt,
                    config=config,
                )
                if res and res.text:
                    self.last_used_model = m
                    tier_label = model_tier or "default"
                    log_msg = f"[LLM] Model terpilih: {m} (tier: {tier_label})"
                    logger.info(log_msg)
                    print(log_msg, flush=True)
                    return res.text.strip()
            except Exception as e:
                # print(f"[DEBUG-MODEL] {m} failed: {e}")
                last_err = e
                continue

        # Jika API memicu fallback interaction
        if isinstance(prompt, str):
            try:
                interaction = self.client.interactions.create(
                    model=self.cfg.model,
                    input=prompt,
                    system_instruction=system_instruction or None,
                )
                used_model = getattr(self.cfg, "model", "fallback")
                self.last_used_model = used_model
                tier_label = model_tier or "default"
                log_msg = f"[LLM] Model terpilih: {used_model} (tier: {tier_label}, fallback interaction)"
                logger.info(log_msg)
                print(log_msg, flush=True)
                return interaction.output_text
            except Exception:
                pass

        raise last_err or RuntimeError("Semua kandidat model Gemini gagal merespons.")
