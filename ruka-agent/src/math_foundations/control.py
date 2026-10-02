# -*- coding: utf-8 -*-
"""Mathematical Foundations — Control Theory and Loop Stability.

Menyediakan pengatur kestabilan siklus agen (agent loop stability):
pengontrol anggaran (budget controller), sinyal kesehatan loop (loop health),
dan mekanisme pencegahan osilasi kegagalan rekursif.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any


def loop_health(
    repeated_errors: int,
    max_allowed_errors: int,
    iterations: int,
    budget_iterations: int,
) -> float:
    """Menghitung sinyal kesehatan siklus otonom (health score):
    Health = 1.0 - (repeated_errors / max_errors + iterations / budget).

    Jika Health < threshold (misal 0.3) -> agen harus memohon konfirmasi Young Lord
    atau menghentikan loop dengan hormat sebelum membuang kuota komputasi.
    """
    safe_max_err = max(1, max_allowed_errors)
    safe_budget = max(1, budget_iterations)

    error_penalty = repeated_errors / safe_max_err
    iteration_penalty = iterations / safe_budget

    raw_health = 1.0 - (error_penalty * 0.6 + iteration_penalty * 0.4)
    return float(max(0.0, min(1.0, raw_health)))


@dataclass
class BudgetController:
    """Pengendali anggaran multi-dimensi (token, iterasi, waktu, dan pemanggilan tool)."""
    max_tokens: int = 100_000
    max_iterations: int = 30
    max_time_seconds: float = 120.0
    max_tool_calls: int = 50

    used_tokens: int = 0
    used_iterations: int = 0
    used_tool_calls: int = 0
    start_time: float = field(default_factory=time.time)

    def record_step(self, tokens: int = 0, tool_calls: int = 1, elapsed_seconds: float = 0.0) -> None:
        """Mencatat kemajuan 1 langkah eksekusi loop."""
        self.used_iterations += 1
        self.used_tokens += max(0, tokens)
        self.used_tool_calls += max(0, tool_calls)

    @property
    def elapsed_seconds(self) -> float:
        return time.time() - self.start_time

    def is_exhausted(self) -> bool:
        """Memeriksa apakah salah satu batas anggaran telah terlampaui."""
        if self.used_iterations >= self.max_iterations:
            return True
        if self.used_tokens >= self.max_tokens:
            return True
        if self.used_tool_calls >= self.max_tool_calls:
            return True
        if self.elapsed_seconds >= self.max_time_seconds:
            return True
        return False

    def remaining_ratio(self) -> float:
        """Mengembalikan rasio anggaran terkecil yang tersisa (0.0 jika habis, 1.0 jika utuh)."""
        r_iter = max(0.0, 1.0 - (self.used_iterations / max(1, self.max_iterations)))
        r_tok = max(0.0, 1.0 - (self.used_tokens / max(1, self.max_tokens)))
        r_call = max(0.0, 1.0 - (self.used_tool_calls / max(1, self.max_tool_calls)))
        r_time = max(0.0, 1.0 - (self.elapsed_seconds / max(0.1, self.max_time_seconds)))
        return float(min(r_iter, r_tok, r_call, r_time))

    def summary(self) -> dict[str, Any]:
        """Memberikan ringkasan penggunaan sumber daya terkini."""
        return {
            "iterations": f"{self.used_iterations}/{self.max_iterations}",
            "tokens": f"{self.used_tokens}/{self.max_tokens}",
            "tool_calls": f"{self.used_tool_calls}/{self.max_tool_calls}",
            "elapsed_seconds": f"{self.elapsed_seconds:.2f}/{self.max_time_seconds:.1f}",
            "exhausted": self.is_exhausted(),
            "remaining_ratio": round(self.remaining_ratio(), 4),
        }
