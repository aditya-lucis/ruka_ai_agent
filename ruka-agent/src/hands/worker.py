# -*- coding: utf-8 -*-
"""Single-Writer Worker & Rate Limiter (FR-HA-02, FR-HA-05).

Pekerja eksekusi input tunggal (single-writer) dengan disiplin ketat:
- Antrean berbatas kapasitas 64 pekerjaan (Drop-Oldest bila penuh)
- Pembatas laju global 8 aksi per detik (interval minimal 125 ms)
- Kill Switch tiga pintu dengan penghentian total < 200 ms
"""
from __future__ import annotations

import collections
import threading
import time
from typing import Any, Callable

from src.hands.models import ShadowAction, validate_action


class SingleWriterWorker:
    def __init__(
        self,
        queue_capacity: int = 64,
        max_rate_per_sec: float = 8.0,
    ) -> None:
        self.queue_capacity = queue_capacity
        self.min_interval_s = 1.0 / max_rate_per_sec  # 125 ms
        self.queue: collections.deque[tuple[ShadowAction, Callable[[ShadowAction], Any]]] = collections.deque(
            maxlen=queue_capacity
        )
        self._killed: bool = False
        self._last_execution_time: float = 0.0
        self._lock = threading.Lock()

    @property
    def is_killed(self) -> bool:
        return self._killed

    @property
    def queue_size(self) -> int:
        with self._lock:
            return len(self.queue)

    def trigger_kill_switch(self) -> float:
        """Mengaktifkan kill switch seketika. Menghapus antrean dan mengunci eksekusi (< 200 ms)."""
        start_t = time.perf_counter()
        with self._lock:
            self._killed = True
            self.queue.clear()
        latency_ms = (time.perf_counter() - start_t) * 1000.0
        return latency_ms

    def reset_kill_switch(self) -> None:
        """Mereset status kill switch setelah inspeksi pengamanan selesai."""
        with self._lock:
            self._killed = False

    def enqueue(
        self,
        action: ShadowAction,
        executor_func: Callable[[ShadowAction], Any],
    ) -> bool:
        """Memasukkan aksi ke dalam antrean pekerja tunggal."""
        validate_action(action)
        with self._lock:
            if self._killed:
                return False
            self.queue.append((action, executor_func))
            return True

    def step(self, now: float | None = None) -> Any | None:
        """Menjalankan satu langkah eksekusi dengan penegakan rate limit 8 aksi/detik."""
        current_time = now if now is not None else time.time()

        with self._lock:
            if self._killed or not self.queue:
                return None

            # Cek pembatas laju 8 aksi/detik
            time_since_last = current_time - self._last_execution_time
            if time_since_last < self.min_interval_s:
                return None  # Tunggu interval pembatas laju

            action, executor = self.queue.popleft()
            self._last_execution_time = current_time

        # Eksekusi di luar lock
        try:
            return executor(action)
        except Exception as ex:
            return {"error": str(ex), "action": type(action).__name__}
