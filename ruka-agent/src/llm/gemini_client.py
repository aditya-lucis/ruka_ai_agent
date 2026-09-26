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
        temp = temperature if temperature is not None else getattr(self.cfg, "temperature", 0.7)
        thinking = getattr(self.cfg, "thinking_level", "low")
        gen_config = {}
        if temp is not None:
            gen_config["temperature"] = temp
        if thinking:
            gen_config["thinking_level"] = thinking

        interaction = self.client.interactions.create(
            model=self.cfg.model,
            input=prompt,
            system_instruction=system_instruction or None,
            generation_config=gen_config,
        )
        return interaction.output_text
