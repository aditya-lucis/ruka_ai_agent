"""Emotional simulation — appraisal rule-based, deterministic.
Output adalah DATA untuk modul lain (ekspresi, suara, prioritas).
Modul ini TIDAK mengklaim dan TIDAK merepresentasikan emosi nyata.
"""
from __future__ import annotations
import math
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from enum import Enum

class EventKind(str, Enum):
    TASK_COMPLETED = "task_completed"
    TASK_FAILED = "task_failed"
    TOOL_ERROR = "tool_error"
    PRAISE = "praise"
    USER_CALLED_NAME = "user_called_name"
    AMBIGUOUS_REQUEST = "ambiguous_request"
    BUDGET_WARNING = "budget_warning"
    INJECTION_SUSPECTED = "injection_suspected"

@dataclass(frozen=True)
class Rule:
    kind: EventKind
    dv: float             # delta valence
    da: float             # delta arousal
    dd: float             # delta dominance
    weight: float = 1.0
    note: str = ""

RULES: dict[EventKind, Rule] = {
    EventKind.TASK_COMPLETED: Rule(EventKind.TASK_COMPLETED, +0.6, +0.5, +0.2, note="hasil tervalidasi"),
    EventKind.PRAISE: Rule(EventKind.PRAISE, +0.4, +0.3, -0.1),
    EventKind.USER_CALLED_NAME: Rule(EventKind.USER_CALLED_NAME, +0.2, +0.8, 0.0, note="responsif"),
    EventKind.TOOL_ERROR: Rule(EventKind.TOOL_ERROR, -0.5, +0.6, +0.3),
    EventKind.TASK_FAILED: Rule(EventKind.TASK_FAILED, -0.5, +0.4, +0.2),
    EventKind.AMBIGUOUS_REQUEST: Rule(EventKind.AMBIGUOUS_REQUEST, -0.3, +0.4, -0.2),
    EventKind.BUDGET_WARNING: Rule(EventKind.BUDGET_WARNING, -0.2, +0.7, +0.4),
    EventKind.INJECTION_SUSPECTED: Rule(EventKind.INJECTION_SUSPECTED, -0.4, +0.5, +0.6, note="waspada"),
}

class EmotionalSignal(str, Enum):
    """Kategori diskrit untuk konsumen ekspresi (PART 6)."""
    PROUD = "proud"
    HAPPY = "happy"
    EXCITED = "excited"
    SMUG = "smug"
    NEUTRAL = "neutral"
    FOCUSED = "focused"
    SERIOUS = "serious"
    CONFUSED = "confused"
    WORRIED = "worried"
    COLD = "cold"

def classify(v: float, a: float, d: float) -> EmotionalSignal:
    """Peta dimensi → kategori. Deterministik, tanpa LLM."""
    if v > 0.4 and d > 0.6:
        return EmotionalSignal.PROUD if a > 0.4 else EmotionalSignal.SMUG
    if v > 0.3:
        return EmotionalSignal.EXCITED if a > 0.6 else EmotionalSignal.HAPPY
    if a > 0.5 and d > 0.5:
        return EmotionalSignal.FOCUSED if v > -0.1 else EmotionalSignal.SERIOUS
    if a > 0.5 and v < -0.2:
        return EmotionalSignal.WORRIED
    if a > 0.3 and v < 0.0 and d < 0.45:
        return EmotionalSignal.CONFUSED
    if v < -0.3 and a < 0.3:
        return EmotionalSignal.COLD
    return EmotionalSignal.NEUTRAL

class AppraisalEngine:
    """Nilai event → perbarui EmotionalSimState → kembalikan jejak."""
    DECAY_PER_MIN = 0.3   # λ
    def __init__(self, state) -> None:  # state: EmotionalSimState (PART 4)
        self._state = state

    def _decay_to_now(self, now: datetime) -> None:
        minutes = max(0.0, (now - self._state.updated_at).total_seconds() / 60)
        factor = math.exp(-self.DECAY_PER_MIN * minutes)
        for f in ("valence", "arousal", "dominance"):
            cur = getattr(self._state, f)
            target = 0.0 if f != "dominance" else 0.6
            setattr(self._state, f, target + (cur - target) * factor)
        self._state.updated_at = now

    def appraise(self, kind: EventKind | str, now: datetime | None = None) -> dict:
        now = now or datetime.now(timezone.utc)
        self._decay_to_now(now)
        
        if isinstance(kind, str):
            try:
                kind = EventKind(kind)
            except ValueError:
                raise KeyError(f"Event tak dikenal: {kind}")
            
        rule = RULES[kind]
        s = self._state
        s.valence = max(-1.0, min(1.0, s.valence + rule.dv * rule.weight))
        s.arousal = max(0.0, min(1.0, s.arousal + rule.da * rule.weight))
        s.dominance = max(0.0, min(1.0, s.dominance + rule.dd * rule.weight))
        s.updated_at = now
        return {
            "event": kind.value,
            "rule": rule.note or kind.value,
            "v": round(s.valence, 3),
            "a": round(s.arousal, 3),
            "d": round(s.dominance, 3),
            "signal": classify(s.valence, s.arousal, s.dominance).value,
        }

def audio_tone_hint(signal: EmotionalSignal) -> str:
    """Peta sinyal → petunjuk vokal untuk kartu suara TTS (PART 12)."""
    return {
        EmotionalSignal.PROUD: "measured, dignified, slight smile",
        EmotionalSignal.HAPPY: "warm, light",
        EmotionalSignal.EXCITED: "quick, bright",
        EmotionalSignal.SMUG: "dry, amused",
        EmotionalSignal.FOCUSED: "even, precise",
        EmotionalSignal.SERIOUS: "low, steady",
        EmotionalSignal.CONFUSED: "hesitant, rising end",
        EmotionalSignal.WORRIED: "soft, careful",
        EmotionalSignal.COLD: "distant, minimal",
        EmotionalSignal.NEUTRAL: "calm, neutral",
    }[signal]
