from __future__ import annotations
from enum import Enum
from typing import Literal
from pydantic import BaseModel, Field

class Intent(str, Enum):
    CHAT = "chat"
    TASK_REQUEST = "task_request"
    QUESTION_KB = "question_kb" # butuh knowledge base
    AMBIGUOUS = "ambiguous"

class IntentResult(BaseModel):
    """Kontrak klasifikasi maksud — titik keputusan pertama."""
    intent: Intent
    confidence: float = Field(ge=0.0, le=1.0)
    reason: str = Field(min_length=1, description="alasan singkat")

class ToolDecision(BaseModel):
    """Kontrak keputusan tool: pakai tool atau jawab langsung."""
    action: Literal["use_tool", "answer_directly"]
    tool_name: str | None = Field(
        default=None,
        description="nama tool; wajib bila action=use_tool",
    )
    tool_arguments: dict | None = None
    direct_answer: str | None = Field(
        default=None,
        description="wajib bila action=answer_directly",
    )

class PlanStep(BaseModel):
    step_id: int
    description: str
    requires_tool: str | None = None

class TaskPlan(BaseModel):
    """Kontrak output planner (PART XVIII)."""
    goal: str
    steps: list[PlanStep] = Field(min_length=1, max_length=12)
    notes: str = ""
