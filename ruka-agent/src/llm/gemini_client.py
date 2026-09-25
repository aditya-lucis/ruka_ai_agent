from __future__ import annotations

from google import genai

from src.config import Config

class GeminiClient:
    """Pembungkus tipis di atas SDK resmi.
    Tanggung jawab SATU: menerjemahkan kebutuhan internal kita
    menjadi panggilan Interactions API + menyeragamkan error.
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
        """Generate teks satu putaran. Kembalikan output_text."""
        interaction = self.client.interactions.create(
            model=self.cfg.model,
            input=prompt,
            system_instruction=system_instruction or None,
            generation_config={
                "temperature": temperature or self.cfg.temperature,
                "thinking_level": self.cfg.thinking_level,
            },
        )
        return interaction.output_text
