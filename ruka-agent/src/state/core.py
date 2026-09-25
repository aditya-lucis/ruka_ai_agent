"""Internal state — sembilan model ter-typed, mutasi terkontrol.
Prinsip: TIDAK ADA mutasi bebas dari luar. Semua perubahan lewat
metode ter-nama yang (1) memvalidasi, (2) mencatat jejak, (3)
mereturn event agar komponen lain bisa bereaksi (PART 7).
"""
from __future__ import annotations
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable
from pydantic import BaseModel, Field

def utcnow() -> datetime:
    return datetime.now(timezone.utc)

class Activity(str, Enum):
    NORMAL = "normal"
    REDUCED = "reduced"
    DORMANT = "dormant"

class IdentityState(BaseModel):
    name: str = "Ruka"
    model_version: str = "0.3.0"

class InteractionState(BaseModel):
    turn: int = 0
    last_modality: str = "text"   # text | audio | image
    session_active: bool = True

class TaskState(BaseModel):
    goal: str | None = None
    plan_id: str | None = None
    current_step: int = 0
    partial_results: list[str] = Field(default_factory=list)
    status: str = "idle"         # idle|running|waiting|done|failed

class EmotionalSimState(BaseModel):
    valence: float = 0.0          # -1..1 (negatif..positif)
    arousal: float = 0.2          # 0..1 (tenang..terbangun)
    dominance: float = 0.6        # 0..1 (rendah diri..percaya diri)
    updated_at: datetime = Field(default_factory=utcnow)

class ExpressionState(BaseModel):
    expression: str = "neutral"
    since: datetime = Field(default_factory=utcnow)
    parameters: dict[str, Any] = Field(default_factory=dict)

class MemoryContextState(BaseModel):
    episodic_ids: list[int] = Field(default_factory=list)
    semantic_keys: list[str] = Field(default_factory=list)
    working_summary: str = ""

class AttentionState(BaseModel):
    focus_topic: str | None = None
    mentioned_entities: list[str] = Field(default_factory=list)

class ConfidenceState(BaseModel):
    level: str = "low"            # low|medium|high (PART 21)
    evidence: list[str] = Field(default_factory=list)

class EnergyState(BaseModel):
    activity: Activity = Activity.NORMAL
    since: datetime = Field(default_factory=utcnow)

class InternalState(BaseModel):
    """Agregat — KONTAINER, bukan peti mutasi bebas."""
    identity: IdentityState = Field(default_factory=IdentityState)
    interaction: InteractionState = Field(default_factory=InteractionState)
    task: TaskState = Field(default_factory=TaskState)
    emotion: EmotionalSimState = Field(default_factory=EmotionalSimState)
    expression: ExpressionState = Field(default_factory=ExpressionState)
    memory_context: MemoryContextState = Field(default_factory=MemoryContextState)
    attention: AttentionState = Field(default_factory=AttentionState)
    confidence: ConfidenceState = Field(default_factory=ConfidenceState)
    energy: EnergyState = Field(default_factory=EnergyState)

    # -- kanal mutasi terkontrol (contoh dua; pola sama untuk lainnya) --
    def begin_task(self, goal: str) -> None:
        if self.task.status == "running":
            raise RuntimeError(
                "Tidak boleh memulai task baru saat task berjalan — "
                "selesaikan atau batalkan dulu (budget PART 13)."
            )
        self.task.goal = goal
        self.task.status = "running"
        self.task.current_step = 0
        self.task.partial_results.clear()

    def advance_step(self, partial: str) -> None:
        if self.task.status != "running":
            raise RuntimeError("advance_step hanya valid saat task running")
        self.task.current_step += 1
        self.task.partial_results.append(partial)

    # -- observability --
    def snapshot(self) -> dict[str, Any]:
        """Proyeksi rata untuk log/trace (PART 23). Tanpa data rahasia."""
        return {
            "task": {"goal": self.task.goal, "status": self.task.status,
                     "step": self.task.current_step},
            "emotion": {"v": self.emotion.valence,
                        "a": self.emotion.arousal,
                        "d": self.emotion.dominance},
            "expression": self.expression.expression,
            "confidence": self.confidence.level,
            "turn": self.interaction.turn,
        }
