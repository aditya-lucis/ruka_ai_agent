# -*- coding: utf-8 -*-
"""Heart Doctor & Passive Watchdog (FR-HE-17).

Memantau kesehatan organ jantung Ruka:
- Watchdog denyut hilang > 6.0 detik
- Deteksi deadlock pada simpul yang sama > 6 super-step berturut-turut
- Laporan restart transparan, tidak pernah diam-diam
"""
from __future__ import annotations

import time
from typing import Any


class HeartDoctor:
    def __init__(
        self,
        max_beat_silence_s: float = 6.0,
        max_deadlock_steps: int = 6,
    ) -> None:
        self.max_beat_silence_s = max_beat_silence_s
        self.max_deadlock_steps = max_deadlock_steps

        self._last_beat_time: float = time.time()
        self._current_step_id: str = ""
        self._step_repeat_count: int = 0
        self._restart_records: list[dict[str, Any]] = []

    def record_beat(self, beat_number: int, now: float | None = None) -> None:
        """Mencatat denyut jantung aktif."""
        self._last_beat_time = now if now is not None else time.time()

    def record_step_execution(self, step_id: str) -> bool:
        """Mencatat langkah yang sedang dieksekusi. Mengembalikan True jika terdeteksi deadlock."""
        if step_id == self._current_step_id:
            self._step_repeat_count += 1
        else:
            self._current_step_id = step_id
            self._step_repeat_count = 1

        return self._step_repeat_count > self.max_deadlock_steps

    def check_health(self, now: float | None = None) -> dict[str, Any]:
        """Memeriksa apakah jantung sehat atau memerlukan intervensi dokter."""
        current_time = now if now is not None else time.time()
        silence_duration = current_time - self._last_beat_time

        beat_lost = silence_duration > self.max_beat_silence_s
        deadlock = self._step_repeat_count > self.max_deadlock_steps

        status = "healthy"
        if beat_lost or deadlock:
            status = "critical"
            self._restart_records.append({
                "time": current_time,
                "reason": "beat_lost" if beat_lost else "deadlock",
                "silence_s": silence_duration,
                "deadlock_step": self._current_step_id if deadlock else None,
            })

        return {
            "status": status,
            "silence_duration_s": silence_duration,
            "deadlock_detected": deadlock,
            "restart_needed": (status == "critical"),
        }
