from __future__ import annotations
from pydantic import BaseModel, ValidationError
from src.llm.errors import LLMPermanentError
from src.llm.gemini_client import GeminiClient

def ask_structured(
    client: GeminiClient,
    prompt: str,
    schema_model: type[BaseModel],
    *,
    system_instruction: str = "",
) -> BaseModel:
    """Panggil Gemini dengan kontrak schema; hasil dijamin valid.
    response_format Interactions API + model_json_schema();
    hasil diparse ulang lewat Pydantic (validasi dua kali:
    schema di server, Pydantic di klien).
    """
    interaction = client.client.interactions.create(
        model=client.cfg.model,
        input=prompt,
        system_instruction=system_instruction or None,
        response_format={
            "type": "text",
            "mime_type": "application/json",
            "schema": schema_model.model_json_schema(),
        },
        generation_config={"temperature": 0.0},  # keputusan: T=0
    )
    
    raw = interaction.output_text
    try:
        return schema_model.model_validate_json(raw)
    except ValidationError as e:
        raise LLMPermanentError(
            f"model melanggar kontraknya sendiri: {e}"
        ) from e
