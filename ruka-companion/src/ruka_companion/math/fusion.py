"""ruka_companion.math.fusion — Multimodal Evidence Fusion with correlation discount.
Strictly follows Volume VI, Part X.
logit P' = logit P0 + Σ w_i LLR_i (1 - ρ̄_i)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Mapping, Optional, Sequence

import numpy as np

from .probability import log_odds_to_prob, prob_to_log_odds

__all__ = [
    "ModalityEvidence",
    "FusionConfig",
    "FusionResult",
    "EvidenceFuser",
    "conflict_score",
]


@dataclass
class ModalityEvidence:
    modality: str
    llr: float
    weight: float = 1.0


@dataclass
class FusionConfig:
    """ρ antar pasangan modality — diskon korelasi. 0 = independen murni."""

    correlation: Mapping[frozenset[str], float] = field(default_factory=dict)
    missing_penalty: float = 0.0  # ≥ 0: tarik log-odds menuju 0 saat bukti hilang

    def pair_rho(self, a: str, b: str) -> float:
        if a == b:
            return 1.0
        return float(self.correlation.get(frozenset((a, b)), 0.0))


@dataclass(frozen=True)
class FusionResult:
    prior_prob: float
    fused_llr: float
    posterior_prob: float
    conflict: float
    contributing: tuple[str, ...]
    missing_expected: tuple[str, ...]
    effective_contributions: dict[str, float] = field(default_factory=dict)
    posterior_logodds: float = 0.0


def conflict_score(evidences: Sequence[ModalityEvidence]) -> float:
    """Kontradiksi bukti: bukti positif dan negatif kuat bersamaan.
    c = min(Σ LLR⁺·w, |Σ LLR⁻·w|) / max(Σ|LLR|·w, ε)  ∈ [0,1]
    c besar → jangan percaya fusi netral; angkat ke manusia.
    """
    if not evidences:
        return 0.0
    pos = sum(e.llr * e.weight for e in evidences if e.llr > 0)
    neg = sum(abs(e.llr) * e.weight for e in evidences if e.llr < 0)
    denom = max(sum(abs(e.llr) * e.weight for e in evidences), 1e-9)
    return float(min(pos, neg) / denom)


class EvidenceFuser:
    """Fuser Bayesian log-odds dengan diskon korelasi + pelaporan jujur."""

    def __init__(self, config: FusionConfig | None = None) -> None:
        self.config = config or FusionConfig()

    def fuse(
        self,
        prior_prob: float,
        evidences: Sequence[ModalityEvidence],
        expected_modalities: Sequence[str] = (),
        correlation_matrix: Optional[np.ndarray] = None,
    ) -> FusionResult:
        if not 0.0 < prior_prob < 1.0:
            raise ValueError("prior harus dalam (0,1) — tak ada kepastian 0/100%")
        seen = {e.modality for e in evidences}
        missing = tuple(sorted(set(expected_modalities) - seen))
        base = prob_to_log_odds(prior_prob)
        if not evidences:
            return FusionResult(
                prior_prob=prior_prob,
                fused_llr=0.0,
                posterior_prob=prior_prob,
                conflict=0.0,
                contributing=(),
                missing_expected=missing,
                effective_contributions={},
                posterior_logodds=base,
            )

        effective: list[float] = []
        contributions: dict[str, float] = {}

        for i, e in enumerate(evidences):
            if correlation_matrix is not None:
                if correlation_matrix.shape != (len(evidences), len(evidences)):
                    raise ValueError(
                        f"Ukuran matriks korelasi harus {len(evidences)}x{len(evidences)}"
                    )
                if len(evidences) > 1:
                    rho_bar = (
                        np.sum(np.abs(correlation_matrix[i])) - 1.0
                    ) / (len(evidences) - 1.0)
                else:
                    rho_bar = 0.0
            else:
                rhos = [
                    self.config.pair_rho(e.modality, o.modality)
                    for j, o in enumerate(evidences)
                    if j != i
                ]
                rho_bar = sum(rhos) / len(rhos) if rhos else 0.0

            eff = e.weight * (1.0 - rho_bar)
            effective.append(eff)
            contributions[e.modality] = eff * e.llr

        fused_llr = sum(e.llr * eff for e, eff in zip(evidences, effective))
        shrink = 0.0
        if missing and self.config.missing_penalty > 0:
            shrink = -self.config.missing_penalty * (1.0 if base > 0 else -1.0)

        posterior = log_odds_to_prob(base + fused_llr + shrink)
        c = conflict_score(evidences)

        return FusionResult(
            prior_prob=prior_prob,
            fused_llr=fused_llr,
            posterior_prob=posterior,
            conflict=c,
            contributing=tuple(sorted(seen)),
            missing_expected=missing,
            effective_contributions=contributions,
            posterior_logodds=base + fused_llr + shrink,
        )
