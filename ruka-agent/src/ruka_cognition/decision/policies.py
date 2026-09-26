# -*- coding: utf-8 -*-
"""Decision policies: turning subsystem scores into accountable actions.
A score is a number; a decision is a commitment with consequences.
This module keeps the four decision families of Part VIII explicit:
- deterministic  : threshold rules on normalized scores (fast, testable);
- probabilistic  : expected-utility choice under a cost matrix;
- hybrid         : deterministic fast-path + LLM escalation band;
- guardrails     : inviolable caps that outrank every other signal.
Guardrails are checked LAST and can only veto — a policy layer that a
high score can talk its way past is not a guardrail, it is a
suggestion.
"""
from __future__ import annotations
from dataclasses import dataclass
from enum import Enum
from typing import Sequence
_EPS = 1e-9

class Decision(Enum):
    EXECUTE = "execute"
    ASK_USER = "ask_user"
    REJECT = "reject"
    ESCALATE_LLM = "escalate_llm"

@dataclass(frozen=True)
class ScoredAction:
    """Candidate action with the signals that produced it."""
    name: str
    score: float                # 0..1 normalized composite
    risk: float                 # 0..1 (1 = irreversible damage possible)
    cost: float                 # 0..1 relative resource burden
    payload: str = ""

@dataclass(frozen=True)
class PolicyVerdict:
    decision: Decision
    action: ScoredAction | None
    reasons: tuple[str, ...]

class ThresholdPolicy:
    """Deterministic: score >= accept -> EXECUTE; <= reject -> REJECT;
    between -> ASK_USER (the uncertainty band)."""
    def __init__(self, accept: float = 0.75, reject: float = 0.35) -> None:
        if not 0.0 <= reject < accept <= 1.0:
            raise ValueError("need 0 <= reject < accept <= 1")
        self.accept, self.reject = accept, reject

    def decide(self, action: ScoredAction) -> PolicyVerdict:
        if action.score >= self.accept:
            return PolicyVerdict(Decision.EXECUTE, action,
                                 (f"score {action.score:.3f} >= {self.accept}",))
        if action.score <= self.reject:
            return PolicyVerdict(Decision.REJECT, action,
                                 (f"score {action.score:.3f} <= {self.reject}",))
        return PolicyVerdict(Decision.ASK_USER, action,
                             (f"score {action.score:.3f} in uncertainty band",))

class RiskGuardrail:
    """Hard veto: risk or cost caps and permission requirements."""
    def __init__(self, max_risk: float = 0.7, max_cost: float = 0.9,
                 required_permission: str | None = None,
                 granted_permissions: set[str] | None = None) -> None:
        self.max_risk = max_risk
        self.max_cost = max_cost
        self.required_permission = required_permission
        self.granted = set(granted_permissions or ())

    def check(self, action: ScoredAction) -> tuple[bool, str | None]:
        if action.risk > self.max_risk + _EPS:
            return False, f"risk {action.risk:.2f} exceeds cap {self.max_risk}"
        if action.cost > self.max_cost + _EPS:
            return False, f"cost {action.cost:.2f} exceeds cap {self.max_cost}"
        if self.required_permission and self.required_permission not in self.granted:
            return False, (f"missing permission '{self.required_permission}'")
        return True, None

class ExpectedUtility:
    """Probabilistic: act only when acting beats abstaining.
       E[act]     = p * reward_tp - (1 - p) * cost_fp
       E[abstain] = -p * cost_fn       (missing a needed action)
       act iff  p*(reward_tp + cost_fn) - (1 - p)*cost_fp > 0
       threshold p* = cost_fp / (reward_tp + cost_fn + cost_fp)
    The closed form is the pedagogical payoff: costlier false
    negatives *lower* the confidence needed to act — exactly the
    asymmetry a production policy must encode deliberately.
    """
    def __init__(self, cost_false_positive: float = 1.0,
                 cost_false_negative: float = 4.0,
                 reward_true_positive: float = 3.0) -> None:
        self.c_fp, self.c_fn, self.r_tp = (cost_false_positive,
                                           cost_false_negative,
                                           reward_true_positive)

    def utility_of_acting(self, confidence: float) -> float:
        p = min(max(confidence, 0.0), 1.0)
        return p * self.r_tp - (1.0 - p) * self.c_fp

    def act_threshold(self) -> float:
        denom = self.r_tp + self.c_fn + self.c_fp
        return self.c_fp / denom if denom > 0 else 1.0

    def should_act(self, confidence: float) -> bool:
        p = min(max(confidence, 0.0), 1.0)
        return p * (self.r_tp + self.c_fn) - (1.0 - p) * self.c_fp > 0.0

class HybridPolicy:
    """Deterministic fast path + LLM escalation + hard guardrails."""
    def __init__(self, threshold: ThresholdPolicy | None = None,
                 guardrail: RiskGuardrail | None = None,
                 llm_band: tuple[float, float] = (0.45, 0.75)) -> None:
        self.threshold = threshold or ThresholdPolicy()
        self.guardrail = guardrail or RiskGuardrail()
        self.llm_low, self.llm_high = llm_band

    def decide(self, action: ScoredAction) -> PolicyVerdict:
        ok, why = self.guardrail.check(action)
        if not ok:
            return PolicyVerdict(Decision.REJECT, action,
                                 (f"GUARDRAIL: {why}",))
        
        if self.llm_low <= action.score < self.llm_high:
            return PolicyVerdict(Decision.ESCALATE_LLM, action,
                                 (f"ambiguous band [{self.llm_low}, "
                                  f"{self.llm_high}) — LLM weighs context",))
                                  
        return self.threshold.decide(action)

def rank_actions(actions: Sequence[ScoredAction]) -> list[ScoredAction]:
    """Monotonic ranking by score (ties broken by lower risk, then name)."""
    return sorted(actions, key=lambda a: (-a.score, a.risk, a.name))
