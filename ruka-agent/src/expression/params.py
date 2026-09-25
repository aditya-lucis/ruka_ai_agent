"""Kosakata visual Ruka — 18 ekspresi sebagai struktur data.
Parameter, bukan file: renderer mana pun mengonsumsi struktur ini.
Nama mengikuti Official Character Visual Reference (ruka_square.jpg).
"""
from __future__ import annotations
from enum import Enum
from pydantic import BaseModel, Field

class Expression(str, Enum):
    NEUTRAL = "neutral"
    HAPPY = "happy"
    PROUD = "proud"
    SMUG = "smug"
    THINKING = "thinking"
    CONFUSED = "confused"
    SURPRISED = "surprised"
    ANNOYED = "annoyed"
    EMBARRASSED = "embarrassed"
    WORRIED = "worried"
    SERIOUS = "serious"
    FOCUSED = "focused"
    SLEEPY = "sleepy"
    EXCITED = "excited"
    FLUSTERED = "flustered"
    COLD = "cold"
    CARING = "caring"
    DRAMATIC = "dramatic"

class EyeMood(str, Enum):
    CALM = "calm"        # mata setengah, tenang
    WIDE = "wide"        # terbuka penuh (surprised/excited)
    NARROW = "narrow"    # menyipit (smug/annoyed)
    CLOSED_SOFT = "closed_soft"

class EarPose(str, Enum):
    UP = "up"            # waspada / senang
    TILTED = "tilted"    # penasaran / bingung
    FLAT = "flat"        # tidak setuju / waspada negatif
    RELAXED = "relaxed"

class ExpressionParameters(BaseModel):
    """Dekonstruksi ekspresi — kontrak antara engine dan renderer."""
    expression: Expression = Expression.NEUTRAL
    eyes: EyeMood = EyeMood.CALM
    ears: EarPose = EarPose.RELAXED
    fangs_visible: float = Field(default=0.2, ge=0.0, le=1.0)
    blush: float = Field(default=0.0, ge=0.0, le=1.0)     # comic relief sopan
    posture_openness: float = Field(default=0.6, ge=0.0, le=1.0)
    cape_flow: float = Field(default=0.3, ge=0.0, le=1.0) # dramatis Marquis
    voice_tone: str = "calm, neutral"
    motion_energy: float = Field(default=0.3, ge=0.0, le=1.0)
    hold_ms: int = Field(default=1200, ge=200)            # durasi tampil

# Resep parameter per ekspresi — satu-satunya tempat angka visual hidup.
# Mengubah “rasa” ekspresi = mengubah baris ini, bukan kode engine.
RECIPES: dict[Expression, ExpressionParameters] = {
    Expression.NEUTRAL: ExpressionParameters(),
    Expression.HAPPY: ExpressionParameters(
        expression=Expression.HAPPY, eyes=EyeMood.CALM, ears=EarPose.UP,
        posture_openness=0.8, voice_tone="warm, light", motion_energy=0.4),
    Expression.PROUD: ExpressionParameters(
        expression=Expression.PROUD, eyes=EyeMood.NARROW, ears=EarPose.UP,
        cape_flow=0.7, posture_openness=0.9,
        voice_tone="measured, dignified", motion_energy=0.25),
    Expression.SMUG: ExpressionParameters(
        expression=Expression.SMUG, eyes=EyeMood.NARROW, ears=EarPose.TILTED,
        fangs_visible=0.5, voice_tone="dry, amused", motion_energy=0.2),
    Expression.THINKING: ExpressionParameters(
        expression=Expression.THINKING, eyes=EyeMood.CLOSED_SOFT,
        ears=EarPose.TILTED, motion_energy=0.1, hold_ms=2000),
    Expression.CONFUSED: ExpressionParameters(
        expression=Expression.CONFUSED, ears=EarPose.TILTED,
        voice_tone="hesitant", motion_energy=0.2),
    Expression.SURPRISED: ExpressionParameters(
        expression=Expression.SURPRISED, eyes=EyeMood.WIDE,
        ears=EarPose.UP, motion_energy=0.7, hold_ms=800),
    Expression.ANNOYED: ExpressionParameters(
        expression=Expression.ANNOYED, ears=EarPose.FLAT,
        eyes=EyeMood.NARROW, voice_tone="flat", motion_energy=0.15),
    Expression.EMBARRASSED: ExpressionParameters(
        expression=Expression.EMBARRASSED, ears=EarPose.FLAT,
        blush=0.7, voice_tone="soft, trailing", motion_energy=0.35),
    Expression.WORRIED: ExpressionParameters(
        expression=Expression.WORRIED, eyes=EyeMood.WIDE,
        ears=EarPose.TILTED, voice_tone="careful"),
    Expression.SERIOUS: ExpressionParameters(
        expression=Expression.SERIOUS, eyes=EyeMood.NARROW,
        ears=EarPose.UP, cape_flow=0.5, voice_tone="low, steady"),
    Expression.FOCUSED: ExpressionParameters(
        expression=Expression.FOCUSED, eyes=EyeMood.NARROW,
        ears=EarPose.UP, motion_energy=0.05, hold_ms=2400),
    Expression.SLEEPY: ExpressionParameters(
        expression=Expression.SLEEPY, eyes=EyeMood.CLOSED_SOFT,
        ears=EarPose.RELAXED, motion_energy=0.05, hold_ms=3000),
    Expression.EXCITED: ExpressionParameters(
        expression=Expression.EXCITED, eyes=EyeMood.WIDE,
        ears=EarPose.UP, posture_openness=0.95,
        voice_tone="quick, bright", motion_energy=0.85, hold_ms=700),
    Expression.FLUSTERED: ExpressionParameters(
        expression=Expression.FLUSTERED, eyes=EyeMood.WIDE,
        ears=EarPose.FLAT, blush=0.8, motion_energy=0.6, hold_ms=900),
    Expression.COLD: ExpressionParameters(
        expression=Expression.COLD, eyes=EyeMood.NARROW,
        ears=EarPose.RELAXED, posture_openness=0.2,
        voice_tone="distant", motion_energy=0.1),
    Expression.CARING: ExpressionParameters(
        expression=Expression.CARING, eyes=EyeMood.CALM,
        posture_openness=0.85, voice_tone="gentle, warm"),
    Expression.DRAMATIC: ExpressionParameters(
        expression=Expression.DRAMATIC, cape_flow=1.0,
        fangs_visible=0.8, posture_openness=1.0,
        voice_tone="theatrical, grand", motion_energy=0.8),
}

def params_for(expression: Expression) -> ExpressionParameters:
    return RECIPES[expression].model_copy(deep=True)
