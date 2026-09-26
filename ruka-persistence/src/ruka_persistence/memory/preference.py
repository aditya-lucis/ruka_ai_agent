import re
from dataclasses import field
from typing import List, Optional

from ruka_persistence.memory.types import Preference, PreferenceObservation

CANDIDATE_MIN_SUPPORT = 1
STABLE_MIN_SUPPORT = 3
STABLE_MIN_RATIO = 3.0
SUPPORT_DELTA = 0.12
CONTRA_DELTA = 0.30

def _norm_statement(statement: str) -> str:
    # Basic normalization: lower and remove punctuation
    s = statement.lower()
    s = re.sub(r'[^\w\s]', '', s)
    return s.strip()

class PreferencePipeline:
    """Mesin status preferensi dengan jejak penuh."""
    
    def __init__(self):
        self.candidate_min_support: int = CANDIDATE_MIN_SUPPORT
        self.stable_min_support: int = STABLE_MIN_SUPPORT
        self.stable_min_ratio: float = STABLE_MIN_RATIO
        self.preferences: list[Preference] = []
        self.pending: list[PreferenceObservation] = []
        self.trace: list[str] = []

    # ------------------------------------------------------------ ingest
    def _find(self, statement: str) -> Preference | None:
        target = _norm_statement(statement)
        for p in self.preferences:
            if _norm_statement(p.statement) == target:
                return p
        return None

    def observe(self, obs: PreferenceObservation) -> Preference:
        """Satu observasi masuk. Return status preferensi terkini."""
        p = self._find(obs.observed_behavior)
        if p is None:
            domain = obs.observed_behavior.split(":")[0] if ":" in obs.observed_behavior else "general"
            p = Preference(statement=obs.observed_behavior,
                           domain=domain,
                           status="candidate",
                           support=0, contradiction=0, confidence=0.0)
            self.preferences.append(p)
            self.trace.append(f"new:{p.statement[:40]}")
            
        # bukti: evidence_strength tinggi = eksplisit; rendah = implisit
        if obs.evidence_strength >= 0.5:
            p.support += 1
            p.confidence = min(1.0, p.confidence + SUPPORT_DELTA
                               * (0.5 + 0.5 * obs.evidence_strength))
        else:
            p.contradiction += 1
            p.confidence = max(0.0, p.confidence - CONTRA_DELTA)
            
        p.last_evidence = obs.observed_at
        p.sources.append(obs.observation_id)
        
        self._reclassify(p)
        return p

    # ------------------------------------------------------------ status
    def _reclassify(self, p: Preference) -> None:
        before = p.status
        ratio = (p.support / p.contradiction
                 if p.contradiction > 0 else float("inf"))
                 
        if p.support == 0 and p.contradiction >= 2:
            p.status = "retracted"
        elif (p.support >= self.stable_min_support
              and ratio >= self.stable_min_ratio
              and p.confidence >= 0.5):
            p.status = "stable"
        elif p.support >= self.candidate_min_support:
            p.status = "candidate"
        else:
            p.status = "candidate"
            
        if before != p.status:
            self.trace.append(f"reclassified:{p.preference_id}:{before}->{p.status}")

    def forget(self, statement: str) -> bool:
        """Forget total: preferensi hilang, bukan disembunyikan."""
        p = self._find(statement)
        if p is None:
            return False
        self.preferences.remove(p)
        self.trace.append(f"forget:{_norm_statement(statement)[:36]}")
        return True

    # ------------------------------------------------------------ query
    def stable(self) -> list[Preference]:
        return [p for p in self.preferences if p.status == "stable"]

    def summary(self) -> dict:
        by_status = {"candidate": 0, "stable": 0, "retracted": 0}
        for p in self.preferences:
            by_status[p.status] = by_status.get(p.status, 0) + 1
        return {"total": len(self.preferences),
                "by_status": by_status,
                "pending_observations": len(self.pending)}
