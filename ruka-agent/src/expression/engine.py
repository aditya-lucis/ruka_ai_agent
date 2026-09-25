"""Expression decision engine — deterministik, tervalidasi, murah.
Sumber keputusan: (1) sinyal emosi PART 5, (2) fase FSM PART 7,
(3) konteks sosial ringan dari intent. Usulan LLM divalidasi ketat.
Jalur panas TIDAK memanggil LLM — ekspresi adalah komputasi lokal.
"""
from __future__ import annotations
from dataclasses import dataclass
from src.emotion.appraisal import EmotionalSignal
from src.expression.params import Expression, ExpressionParameters, params_for
from src.state.core import InternalState

# Sinyal afektif -> ekspresi dasar (kandidat, belum final)
SIGNAL_TO_EXPRESSION = {
    EmotionalSignal.PROUD: Expression.PROUD,
    EmotionalSignal.HAPPY: Expression.HAPPY,
    EmotionalSignal.EXCITED: Expression.EXCITED,
    EmotionalSignal.SMUG: Expression.SMUG,
    EmotionalSignal.NEUTRAL: Expression.NEUTRAL,
    EmotionalSignal.FOCUSED: Expression.FOCUSED,
    EmotionalSignal.SERIOUS: Expression.SERIOUS,
    EmotionalSignal.CONFUSED: Expression.CONFUSED,
    EmotionalSignal.WORRIED: Expression.WORRIED,
    EmotionalSignal.COLD: Expression.COLD,
}

# Fase FSM -> ekspresi menutupi (override afektif untuk status jujur)
PHASE_OVERRIDE = {
    "thinking": [Expression.THINKING, Expression.FOCUSED, Expression.CONFUSED],
    "tool_executing": [Expression.FOCUSED, Expression.SERIOUS],
    "waiting": [Expression.NEUTRAL, Expression.SLEEPY],
    "responding": None,       # afektif berbicara bebas saat menjawab
    "listening": [Expression.NEUTRAL, Expression.THINKING],
    "idle": [Expression.NEUTRAL, Expression.SLEEPY],
}

@dataclass(frozen=True)
class SocialCue:
    user_called_name: bool = False
    praise: bool = False
    apology: bool = False
    comic_moment: bool = False   # momen lucu sopan -> flustered ringan

class ExpressionEngine:
    """Pusat keputusan ekspresi. state: InternalState (PART 4)."""
    def __init__(self, state: InternalState) -> None:
        self._state = state
        self._last_expression = Expression.NEUTRAL
        self._rejections: list[str] = []

    def decide(self, phase: str, cue: SocialCue | None = None) -> ExpressionParameters:
        """Fase + sinyal + konteks sosial -> parameter final.
        Aturan prioritas (eksplisit, bisa diaudit):
        1. fase tool/thinking menutupi afektif (status jujur proses)
        2. panggilan nama -> excited (loyal-responsif, “Yes, Sir!”)
        3. momen komik sopan -> flustered terbatas
        4. afektif dominan; 5. neutral fallback
        """
        cue = cue or SocialCue()
        signal = self._current_signal()
        override = PHASE_OVERRIDE.get(phase)

        if phase == "tool_executing":
            chosen = Expression.SERIOUS if signal in (EmotionalSignal.SERIOUS,
                                                      EmotionalSignal.WORRIED) else Expression.FOCUSED
        elif phase == "thinking":
            chosen = (SIGNAL_TO_EXPRESSION[signal]
                      if signal in (EmotionalSignal.FOCUSED,
                                    EmotionalSignal.CONFUSED,
                                    EmotionalSignal.WORRIED)
                      else Expression.THINKING)
        elif cue.user_called_name:
            chosen = Expression.EXCITED
        elif cue.comic_moment and signal in (EmotionalSignal.NEUTRAL,
                                             EmotionalSignal.HAPPY):
            chosen = Expression.FLUSTERED
        elif override is not None:
            base = SIGNAL_TO_EXPRESSION[signal]
            chosen = base if base in override else override[0]
        else:
            chosen = SIGNAL_TO_EXPRESSION[signal]

        # hysteresis: jangan ganti ekspresi hanya karena delta ambang kecil
        if (chosen != self._last_expression
            and self._similar(self._last_expression, chosen)
            and phase not in ("tool_executing", "thinking")):
            chosen = self._last_expression

        self._last_expression = chosen
        self._state.expression.expression = chosen.value
        return params_for(chosen)

    def validate_proposal(self, raw: str) -> Expression | None:
        """Usulan LLM -> enum sah atau None (ditolak, dicatat)."""
        try:
            candidate = Expression(raw.strip().lower())
        except ValueError:
            self._rejections.append(f"invalid expression label: {raw!r}")
            return None
            
        if candidate not in {e for e in Expression}:
            self._rejections.append(f"unknown expression: {raw!r}")
            return None
            
        return candidate

    def _current_signal(self) -> EmotionalSignal:
        from src.emotion.appraisal import classify
        e = self._state.emotion
        return classify(e.valence, e.arousal, e.dominance)

    @staticmethod
    def _similar(a: Expression, b: Expression) -> bool:
        near = {Expression.NEUTRAL: {Expression.CARING},
                Expression.HAPPY: {Expression.CARING, Expression.EXCITED},
                Expression.SMUG: {Expression.PROUD},
                Expression.WORRIED: {Expression.CONFUSED}}
        return b in near.get(a, set())

    @property
    def rejections(self) -> list[str]:
        return list(self._rejections)
