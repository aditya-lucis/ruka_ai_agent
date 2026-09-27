from __future__ import annotations

from google import genai

from src.config import Config

from google.genai import types

class GeminiClient:
    """Pembungkus di atas SDK resmi Google GenAI.
    Menghasilkan teks real-time (<3s) menggunakan model optimal.
    """

    def __init__(self, cfg: Config):
        self.cfg = cfg
        self.client = genai.Client(api_key=cfg.api_key)

    def complete(
        self,
        prompt: str,
        *,
        system_instruction: str = "",
        temperature: float | None = None,
    ) -> str:
        """Generate teks satu putaran dengan latensi rendah real-time."""
        temp = temperature if temperature is not None else getattr(self.cfg, "temperature", 0.7)
        config = types.GenerateContentConfig(
            system_instruction=system_instruction or None,
            temperature=temp,
        )

        model_candidates = [
            getattr(self.cfg, "model", "gemini-3.5-flash-lite"),
            "gemini-3.5-flash-lite",
            "gemini-3.5-flash",
            "gemini-3.8-flash",
        ]

        last_err = None
        for m in model_candidates:
            try:
                res = self.client.models.generate_content(
                    model=m,
                    contents=prompt,
                    config=config,
                )
                if res and res.text:
                    return res.text.strip()
            except Exception as e:
                last_err = e
                continue

        # Jika API memicu fallback
        try:
            interaction = self.client.interactions.create(
                model=self.cfg.model,
                input=prompt,
                system_instruction=system_instruction or None,
            )
            return interaction.output_text
        except Exception:
            raise last_err or RuntimeError("Semua kandidat model Gemini gagal merespons.")
