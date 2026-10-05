# -*- coding: utf-8 -*-
"""Heart Budget Controller (FR-HE-08).

Mengelola anggaran napas per tugas:
- Maksimal 180.000 token per tugas
- Maksimal 1.800 detik (30 menit) durasi kerja
- Pemutus sirkuit (circuit breaker) setelah 3 kali limpasan 5% (189.000 token / 1.890s)
"""
from __future__ import annotations

import time


class HeartBudgetExceeded(Exception):
    """Dilempar ketika tugas kehabisan napas (token atau waktu habis)."""
    pass


class HeartBudget:
    def __init__(
        self,
        max_tokens: int = 180000,
        max_duration_s: float = 1800.0,
        overflow_threshold_ratio: float = 1.05,
    ) -> None:
        self.max_tokens = max_tokens
        self.max_duration_s = max_duration_s
        self.overflow_tokens = int(max_tokens * overflow_threshold_ratio)
        self.overflow_duration_s = max_duration_s * overflow_threshold_ratio

        self.used_tokens: int = 0
        self.start_time: float = time.time()
        self.overflow_strikes: int = 0
        self.circuit_tripped: bool = False

    def reset(self) -> None:
        self.used_tokens = 0
        self.start_time = time.time()
        self.circuit_tripped = False

    @property
    def elapsed_seconds(self) -> float:
        return time.time() - self.start_time

    @property
    def remaining_tokens(self) -> int:
        return max(0, self.max_tokens - self.used_tokens)

    @property
    def remaining_seconds(self) -> float:
        return max(0.0, self.max_duration_s - self.elapsed_seconds)

    def consume(self, tokens: int) -> None:
        """Mencatat konsumsi token dan memeriksa batas anggaran."""
        if self.circuit_tripped:
            raise HeartBudgetExceeded("Sirkuit jantung terputus (Circuit Breaker Tripped) akibat limpasan berulang.")

        self.used_tokens += tokens
        elapsed = self.elapsed_seconds

        # Pengecekan limpasan 5%
        if self.used_tokens > self.overflow_tokens or elapsed > self.overflow_duration_s:
            self.overflow_strikes += 1
            if self.overflow_strikes >= 3:
                self.circuit_tripped = True
                raise HeartBudgetExceeded("Tugas dihentikan permanen: 3 kali melimpas batas toleransi 5%!")
            raise HeartBudgetExceeded(
                f"Tugas melimpas batas toleransi! Tokens: {self.used_tokens}/{self.overflow_tokens}, Waktu: {elapsed:.1f}/{self.overflow_duration_s:.1f}s"
            )

        # Pengecekan batas normal
        if self.used_tokens > self.max_tokens:
            raise HeartBudgetExceeded(f"Kehabisan napas token: {self.used_tokens} > {self.max_tokens}")
        if elapsed > self.max_duration_s:
            raise HeartBudgetExceeded(f"Kehabisan napas waktu: {elapsed:.1f}s > {self.max_duration_s}s")
