"""Complexity gate — murah, deterministik, sebelum LLM berat.
Sinyal leksikal + riwayat; bukan kecerdasan. Salah klasifikasi
aman: jalur lebih tinggi hanya lebih lambat, bukan salah.
"""
from __future__ import annotations
import re
from dataclasses import dataclass
from enum import Enum

class Complexity(str, Enum):
    DIRECT = "direct"          # jawab langsung
    SIMPLE_TOOL = "simple_tool"  # 1 tool, tanpa rencana
    PLANNED = "planned"         # dekomposisi + dependensi (PART 18)

COMPOUND_VERBS = re.compile(
    r"\b(dan juga|kemudian|setelah itu|lalu|secara berurutan|"
    r"bandingkan|untuk setiap|semua)", re.IGNORECASE
)

DEPENDENCE_HINT = re.compile(
    r"\b(hasilnya|dari data itu|berdasarkan temuan|setelah menganalisis)",
    re.IGNORECASE
)

@dataclass(frozen=True)
class ComplexityVerdict:
    level: Complexity
    signals: list[str]
    estimated_steps: int

class ComplexityEstimator:
    def estimate(self, goal: str, similar_history: int = 0) -> ComplexityVerdict:
        signals: list[str] = []
        steps = 1
        for m in COMPOUND_VERBS.finditer(goal):
            signals.append(f"verba majemuk: {m.group()}")
            steps += 1
        for m in DEPENDENCE_HINT.finditer(goal):
            signals.append(f"dependensi: {m.group()}")
            steps += 1
        if similar_history >= 3:
            signals.append(f"riwayat serupa x{similar_history}")
            steps = max(1, steps - 1)     # familiaritas menurunkan kelas
        if steps == 1:
            return ComplexityVerdict(Complexity.DIRECT, signals, 1)
        if steps <= 2 and not DEPENDENCE_HINT.search(goal):
            return ComplexityVerdict(Complexity.SIMPLE_TOOL, signals, steps)
        return ComplexityVerdict(Complexity.PLANNED, signals, steps)
