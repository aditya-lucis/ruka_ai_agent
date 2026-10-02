# -*- coding: utf-8 -*-
"""Mathematical Foundations — Data Types and Uncertainty Structures.

Mendefinisikan tipe data formal untuk probabilitas, keyakinan (belief),
dan skor tertimbang dengan metrik confidence.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Mapping


@dataclass(frozen=True)
class Score:
    """Representasi nilai berskor yang membawa derajat kepastian (confidence)
    serta rincian komponen penyusunnya.

    Mendukung operator perbandingan dan aritmatika dasar sehingga kompatibel
    secara transparan dengan nilai numerik float biasa.
    """
    value: float
    confidence: float = 1.0
    components: dict[str, float] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "value", float(self.value))
        clamped_conf = max(0.0, min(1.0, float(self.confidence)))
        object.__setattr__(self, "confidence", clamped_conf)

    def __float__(self) -> float:
        return self.value

    def __int__(self) -> int:
        return int(self.value)

    def __repr__(self) -> str:
        if self.components:
            return f"Score(value={self.value:.4f}, confidence={self.confidence:.2f}, components={self.components})"
        return f"Score(value={self.value:.4f}, confidence={self.confidence:.2f})"

    # Perbandingan numerik
    def __eq__(self, other: Any) -> bool:
        if isinstance(other, Score):
            return self.value == other.value and self.confidence == other.confidence
        if isinstance(other, (int, float)):
            return self.value == float(other)
        return False

    def __lt__(self, other: Any) -> bool:
        return self.value < float(other)

    def __le__(self, other: Any) -> bool:
        return self.value <= float(other)

    def __gt__(self, other: Any) -> bool:
        return self.value > float(other)

    def __ge__(self, other: Any) -> bool:
        return self.value >= float(other)

    # Aritmatika dasar
    def __add__(self, other: Any) -> float:
        return self.value + float(other)

    def __radd__(self, other: Any) -> float:
        return float(other) + self.value

    def __sub__(self, other: Any) -> float:
        return self.value - float(other)

    def __rsub__(self, other: Any) -> float:
        return float(other) - self.value

    def __mul__(self, other: Any) -> float:
        return self.value * float(other)

    def __rmul__(self, other: Any) -> float:
        return float(other) * self.value

    def __truediv__(self, other: Any) -> float:
        return self.value / float(other)

    def __rtruediv__(self, other: Any) -> float:
        return float(other) / self.value


@dataclass
class Belief:
    """Representasi keyakinan epistemik terhadap sebuah hipotesis atau proposisi."""
    hypothesis: str
    probability: float
    evidence: list[str] = field(default_factory=list)
    last_updated: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.probability = max(0.0, min(1.0, float(self.probability)))


@dataclass
class BeliefState:
    """Agregasi kumpulan keyakinan (belief distribution) sistem pada satu waktu."""
    beliefs: dict[str, Belief] = field(default_factory=dict)
    entropy: float = 0.0
    last_update: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def set_belief(self, hypothesis: str, probability: float, evidence: list[str] | None = None) -> Belief:
        """Membuat atau memperbarui keyakinan atas sebuah hipotesis."""
        b = Belief(
            hypothesis=hypothesis,
            probability=probability,
            evidence=evidence or [],
            last_updated=datetime.now(timezone.utc),
        )
        self.beliefs[hypothesis] = b
        self.last_update = datetime.now(timezone.utc)
        return b

    def get_probability(self, hypothesis: str, default: float = 0.0) -> float:
        """Mengambil probabilitas hipotesis tertentu."""
        b = self.beliefs.get(hypothesis)
        return b.probability if b else default
