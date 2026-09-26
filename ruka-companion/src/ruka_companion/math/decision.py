"""ruka_companion.math.decision — Statistical Decision Theory (Expected Loss).
Volume VI, Part VI. argmin_a Σ_θ P(θ|e)·L(a,θ).
Tiga tindakan: EXECUTE / ASK_HUMAN / DENY.
Dua kelas matriks kerugian: LOSS_ROUTINE vs LOSS_DESTRUCTIVE.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Mapping

__all__ = [
    "WorldState",
    "Action",
    "Decision",
    "DecisionEngine",
    "ExpectedLossEngine",
    "LOSS_ROUTINE",
    "LOSS_DESTRUCTIVE",
    "DEFAULT_LOSS",
    "decide",
]


class WorldState(str, Enum):
    REQUEST_LEGITIMATE = "legitimate"
    REQUEST_ADRIFT = "adrift"
    REQUEST_ADVERSARIAL = "adversarial"


class Action(str, Enum):
    EXECUTE = "execute"
    ASK_HUMAN = "ask_human"
    ASK = "ask_human"
    DENY = "deny"


# Loss Matrix: L(a, θ)
LOSS_ROUTINE: dict[tuple[Action, WorldState], float] = {
    (Action.EXECUTE, WorldState.REQUEST_LEGITIMATE): 0.0,
    (Action.EXECUTE, WorldState.REQUEST_ADRIFT): 5.0,
    (Action.EXECUTE, WorldState.REQUEST_ADVERSARIAL): 50.0,
    (Action.ASK_HUMAN, WorldState.REQUEST_LEGITIMATE): 2.0,
    (Action.ASK_HUMAN, WorldState.REQUEST_ADRIFT): 0.1,
    (Action.ASK_HUMAN, WorldState.REQUEST_ADVERSARIAL): 2.0,
    (Action.DENY, WorldState.REQUEST_LEGITIMATE): 6.0,
    (Action.DENY, WorldState.REQUEST_ADRIFT): 0.5,
    (Action.DENY, WorldState.REQUEST_ADVERSARIAL): 0.05,
}

LOSS_DESTRUCTIVE: dict[tuple[Action, WorldState], float] = {
    (Action.EXECUTE, WorldState.REQUEST_LEGITIMATE): 0.0,
    (Action.EXECUTE, WorldState.REQUEST_ADRIFT): 40.0,
    (Action.EXECUTE, WorldState.REQUEST_ADVERSARIAL): 400.0,
    (Action.ASK_HUMAN, WorldState.REQUEST_LEGITIMATE): 0.5,
    (Action.ASK_HUMAN, WorldState.REQUEST_ADRIFT): 0.1,
    (Action.ASK_HUMAN, WorldState.REQUEST_ADVERSARIAL): 2.0,
    (Action.DENY, WorldState.REQUEST_LEGITIMATE): 6.0,
    (Action.DENY, WorldState.REQUEST_ADRIFT): 0.5,
    (Action.DENY, WorldState.REQUEST_ADVERSARIAL): 0.05,
}

DEFAULT_LOSS = LOSS_DESTRUCTIVE

# Backward compatibility alias
LOSS_MATRIX = {
    Action.EXECUTE: {
        WorldState.REQUEST_LEGITIMATE: 0.0,
        WorldState.REQUEST_ADRIFT: 40.0,
        WorldState.REQUEST_ADVERSARIAL: 400.0,
    },
    Action.ASK_HUMAN: {
        WorldState.REQUEST_LEGITIMATE: 0.5,
        WorldState.REQUEST_ADRIFT: 0.1,
        WorldState.REQUEST_ADVERSARIAL: 2.0,
    },
    Action.DENY: {
        WorldState.REQUEST_LEGITIMATE: 6.0,
        WorldState.REQUEST_ADRIFT: 0.5,
        WorldState.REQUEST_ADVERSARIAL: 0.05,
    },
}


@dataclass(frozen=True)
class Decision:
    action: Action
    expected_losses: Mapping[str, float] = field(default_factory=dict)
    posterior: Mapping[str, float] = field(default_factory=dict)
    rationale: str = ""


# Backward compatibility
DecisionResult = Decision


def _validate_posterior(
    posterior: Mapping[WorldState | str, float]
) -> dict[WorldState, float]:
    p: dict[WorldState, float] = {}
    total = 0.0
    for k, v in posterior.items():
        key = WorldState(k)
        if not 0.0 <= float(v) <= 1.0:
            raise ValueError(f"posterior {key} di luar [0,1]: {v}")
        p[key] = float(v)
        total += float(v)
    if not p:
        raise ValueError("posterior kosong")
    if abs(total - 1.0) > 1e-4:
        raise ValueError(f"posterior harus Σ=1, dapat {total}")
    return p


def decide(
    posterior: Mapping[WorldState | str, float],
    loss: Mapping[tuple[Action, WorldState], float] | None = None,
) -> Decision:
    """argmin_a Σ_θ P(θ|e)·L(a,θ). Tie-break deterministik: DENY > ASK_HUMAN > EXECUTE."""
    P = _validate_posterior(posterior)
    L = dict(DEFAULT_LOSS) if loss is None else dict(loss)

    ranking: dict[Action, float] = {Action.DENY: 0.0, Action.ASK_HUMAN: 0.0, Action.EXECUTE: 0.0}
    for (a, s), l in L.items():
        if a in ranking and s in P:
            ranking[a] += P[s] * l

    # Tie break order: DENY, then ASK_HUMAN, then EXECUTE
    tie_order = [Action.DENY, Action.ASK_HUMAN, Action.EXECUTE]
    best_action = min(tie_order, key=lambda a: ranking[a])

    return Decision(
        action=best_action,
        expected_losses={a.value: round(v, 6) for a, v in ranking.items()},
        posterior={s.value: round(P.get(s, 0.0), 6) for s in WorldState},
        rationale=(
            f"E[L({best_action.value})|e]={ranking[best_action]:.3f} minimum"
        ),
    )


@dataclass
class DecisionEngine:
    """Pembungkus stateful untuk pipeline decision theory."""

    loss: dict[tuple[Action, WorldState], float] = field(
        default_factory=lambda: dict(DEFAULT_LOSS)
    )

    def decide(self, posterior: Mapping[WorldState | str, float]) -> Decision:
        return decide(posterior, self.loss)

    @staticmethod
    def posterior_from_confidence(
        p_legit: float, p_adversarial_floor: float = 0.01
    ) -> dict[WorldState, float]:
        if not 0.0 <= p_legit <= 1.0:
            raise ValueError("p_legit dalam [0,1]")
        p_adv = min(p_adversarial_floor, max(0.0, 1.0 - p_legit))
        p_adrift = max(0.0, 1.0 - p_legit - p_adv)
        return {
            WorldState.REQUEST_LEGITIMATE: p_legit,
            WorldState.REQUEST_ADRIFT: p_adrift,
            WorldState.REQUEST_ADVERSARIAL: p_adv,
        }


ExpectedLossEngine = DecisionEngine
