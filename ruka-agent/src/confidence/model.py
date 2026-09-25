# -*- coding: utf-8 -*-
"""Evidence-based confidence – dari bukti, bukan dari karangan.
Crimson Reflection (PART 22) dan renderer jawaban memakai level
ini untuk memilih penyajian yang jujur.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum


class EpistemicLevel(str, Enum):
    KNOW = "know"
    EVIDENCE = "retrieved_evidence"
    INFER = "infer"
    UNCERTAIN = "uncertain"
    NEED_INFO = "need_more_info"


WEIGHTS = {
    "retrieval": 0.45,
    "tool": 0.20,
    "consistency": 0.20,
    "freshness": 0.15,
}
CONFLICT_PENALTY = 0.10
TH_LOW, TH_HIGH = 0.35, 0.62          # wilayah ragu sengaja lebar


@dataclass
class Evidence:
    retrieval_top: float = 0.0         # 0..1 (rerank P16)
    tool_success: float = 0.0          # 0 / 0.5 / 1
    n_sources: int = 0
    n_conflicts: int = 0
    stale_days: float = 9999.0
    from_identity: bool = False        # fakta diri/konfig (P3)
    notes: list[str] = field(default_factory=list)

    def consistency(self) -> float:
        if self.n_sources <= 1:
            return 0.0
        pairs = self.n_sources * (self.n_sources - 1) // 2
        return max(0.0, 1.0 - self.n_conflicts / pairs)

    def freshness(self) -> float:
        return 1.0 / (1.0 + self.stale_days / 180.0)


def confidence(e: Evidence) -> float:
    if e.from_identity:
        return 1.0
    c = (WEIGHTS["retrieval"] * e.retrieval_top
         + WEIGHTS["tool"] * e.tool_success
         + WEIGHTS["consistency"] * e.consistency()
         + WEIGHTS["freshness"] * e.freshness())
    c -= CONFLICT_PENALTY * e.n_conflicts
    return round(max(0.0, min(1.0, c)), 4)


def epistemic_level(e: Evidence) -> tuple[EpistemicLevel, float]:
    """Level + angka; keputusan STRUKTURAL, bukan pilihan LLM."""
    c = confidence(e)
    if e.from_identity:
        return EpistemicLevel.KNOW, 1.0
    if e.retrieval_top < 0.20 and e.n_sources == 0 and e.tool_success < 1.0:
        return EpistemicLevel.NEED_INFO, c
    if c < TH_LOW:
        return EpistemicLevel.NEED_INFO if e.n_sources == 0 else EpistemicLevel.UNCERTAIN, c
    if c < TH_HIGH:
        return EpistemicLevel.UNCERTAIN, c
    if e.retrieval_top >= 0.62 and e.n_sources >= 1 and e.tool_success >= 0.5:
        return EpistemicLevel.EVIDENCE, c
    return EpistemicLevel.INFER, c


def disclaimer_text(level: EpistemicLevel) -> str:
    """Penyajian jujur per level – di-test, bukan diimprovisasi."""
    return {
        EpistemicLevel.KNOW: "",
        EpistemicLevel.EVIDENCE: "(berdasarkan bukti yang saya kutip di bawah)",
        EpistemicLevel.INFER: "(ini kesimpulan saya dari bukti tak langsung – mohon diverifikasi)",
        EpistemicLevel.UNCERTAIN: "(saya tidak yakin: bukti bercampur/lemah)",
        EpistemicLevel.NEED_INFO: "(saya belum punya cukup data – bisa Anda tambahkan konteks?)",
    }[level]
