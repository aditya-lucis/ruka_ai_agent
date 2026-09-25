from __future__ import annotations
from pydantic import BaseModel, ValidationError
from src.llm.structured import ask_structured

def ask_with_retry(client, prompt, schema_model, *, retries=1,
                   system_instruction=""):
    """Structured ask + satu percakapan perbaikan bila kontrak gagal."""
    try:
        return ask_structured(client, prompt, schema_model,
                              system_instruction=system_instruction)
    except Exception as e:  # ValidationError / parse
        if retries <= 0:
            raise
        
        repair_prompt = (
            f"Jawaban Anda sebelumnya melanggar kontrak:\n{e}\n\n"
            f"Tugas asli:\n{prompt}\n\n"
            "Balas LAGI dengan JSON yang memenuhi kontrak."
        )
        return ask_structured(client, repair_prompt, schema_model,
                              system_instruction=system_instruction)
