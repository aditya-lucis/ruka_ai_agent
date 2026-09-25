from __future__ import annotations
import logging
from pydantic import BaseModel, Field
from src.llm.gemini_client import GeminiClient
from src.llm.structured import ask_structured

log = logging.getLogger("ruka.evaluator")

class EvaluationResult(BaseModel):
    """Kontrak hasil evaluasi — rubrik, bukan perasaan."""
    passed: bool
    score: float = Field(ge=0.0, le=1.0)
    issues: list[str] = Field(default_factory=list, max_length=5)
    correction_hint: str = Field(default="", max_length=500)

class EvaluatorAgent:
    """Menilai artefak terhadap kriteria eksplisit."""
    def __init__(self, client: GeminiClient, *, threshold: float = 0.75):
        self.client = client
        self.threshold = threshold

    def evaluate(self, task: str, artifact: str,
                 criteria: list[str]) -> EvaluationResult:
        rubric = "\n".join(f"- {c}" for c in criteria)
        prompt = (
            f"Tugas: {task}\n\nArtefak:\n{artifact}\n\n"
            f"Kriteria penilaian:\n{rubric}\n\n"
            "Nilai artefak terhadap SETIAP kriteria."
        )
        
        return ask_structured(
            self.client, prompt, EvaluationResult,
            system_instruction="Anda evaluator ketat dan spesifik; "
                               "sebutkan hanya masalah nyata.",
        )

def generate_evaluate_correct(
    client: GeminiClient,
    evaluator: EvaluatorAgent,
    task: str,
    criteria: list[str],
    *,
    max_revisions: int = 2,
) -> tuple[str, EvaluationResult]:
    """Loop lengkap dengan stop condition dan eskalasi."""
    artifact = client.complete(task)
    for revision in range(max_revisions + 1):
        verdict = evaluator.evaluate(task, artifact, criteria)
        if verdict.passed and verdict.score >= evaluator.threshold:
            return artifact, verdict
            
        if revision == max_revisions:
            log.warning("evaluasi gagal setelah %d revisi", revision)
            return artifact, verdict  # eskalasi ke pemanggil
            
        artifact = client.complete(
            f"Perbaiki hasil berikut.\nTugas: {task}\n"
            f"Masalah yang harus diperbaiki: {verdict.issues}\n"
            f"Petunjuk: {verdict.correction_hint}\n\n"
            f"Versi sekarang:\n{artifact}"
        )
    raise RuntimeError("unreachable")
