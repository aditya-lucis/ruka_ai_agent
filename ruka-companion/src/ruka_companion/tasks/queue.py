"""RUKA VI: Offline-Resilient Task Queue — Re-evaluation, Expiration, and Deduplication.
Strictly follows RUKA-VI Chapter XVI (baris 42-120).
"""

from __future__ import annotations

from dataclasses import dataclass
import time
from typing import Any, Callable

from ruka_companion.math.distributed import IdempotencyCache
from .protocol import (
    REMOTE_CAPABILITIES,
    RemoteTask,
    TaskStates,
    TaskValidationError,
)


@dataclass
class QueuePolicy:
    """Kebijakan re-evaluasi antrean task offline."""

    max_age_ms: int = 600_000  # 10 menit
    revalidate_device: Callable[[str], bool] | None = None
    revalidate_capability: bool = True


class TaskQueue:
    """Antrean offline-resilient: tahan banting, anti-eksekusi-buta (Part XVI)."""

    def __init__(
        self,
        policy: QueuePolicy | None = None,
        clock_ms: Callable[[], int] | None = None,
    ) -> None:
        self.policy = policy or QueuePolicy()
        self._now = clock_ms or (lambda: int(time.time() * 1000))
        self._queue: list[RemoteTask] = []
        self._idem = IdempotencyCache(max_entries=8192)

    # ---------------------------------------------------------------- masuk
    def enqueue(self, task: RemoteTask) -> bool:
        """True bila diterima; False bila duplikat task_id (replay/double-send)."""
        if task.capability not in REMOTE_CAPABILITIES:
            raise TaskValidationError(f"kapabilitas {task.capability} tak dirutekan")
        now = self._now()
        if self._idem.seen(task.task_id, now):
            return False  # duplikat — JANGAN eksekusi ulang
        self._idem.record(task.task_id, now, task.status)
        if task.status == TaskStates.CREATED:
            task.status = TaskStates.QUEUED

        self._queue.append(task)
        return True

    # ----------------------------------------------------------- reconnect
    def on_reconnect(self) -> dict[str, int]:
        """Re-evaluasi seluruh antrean non-terminal → laporan keputusan.
        Task STALE dibuang dengan EXPIRED — bukan dieksekusi "karena sudah
        menunggu lama". Inilah anti-blind-execution.
        """
        now = self._now()
        outcome = {
            "expired": 0,
            "cancelled": 0,
            "kept": 0,
            "terminal_skipped": 0,
        }
        for task in self._queue:
            if task.status in (
                TaskStates.COMPLETED,
                TaskStates.FAILED,
                TaskStates.EXPIRED,
                TaskStates.CANCELLED,
            ):
                outcome["terminal_skipped"] += 1
                continue
            # 1. kedaluwarsa?
            if (
                task.is_expired(now)
                or (now - task.created_at_ms) > self.policy.max_age_ms
            ):
                task.status = TaskStates.EXPIRED
                task.error = "stale at reconnect — NOT blindly executed"
                outcome["expired"] += 1
                continue
            # 2. perangkat masih terpercaya?
            if (
                self.policy.revalidate_device is not None
                and not self.policy.revalidate_device(task.device_id)
            ):
                task.status = TaskStates.CANCELLED
                task.error = "device revoked at reconnect"
                outcome["cancelled"] += 1
                continue
            # 3. kapabilitas masih valid?
            if (
                self.policy.revalidate_capability
                and task.capability not in REMOTE_CAPABILITIES
            ):
                task.status = TaskStates.CANCELLED
                task.error = "capability revoked at reconnect"
                outcome["cancelled"] += 1
                continue
            outcome["kept"] += 1
        return outcome

    # ---------------------------------------------------------------- keluar
    def take_ready(self) -> RemoteTask | None:
        """Ambil task non-terminal tertua untuk diproses (RECEIVED)."""
        now = self._now()
        for i, task in enumerate(self._queue):
            if task.status in (TaskStates.QUEUED, TaskStates.DELIVERED):
                if task.is_expired(now):
                    task.status = TaskStates.EXPIRED
                    task.error = "expired at take"
                    continue
                task.status = TaskStates.RECEIVED
                return self._queue.pop(i)
        return None

    def pending(self) -> list[dict[str, Any]]:
        now = self._now()
        return [
            t.as_public()
            for t in self._queue
            if t.status
            not in (
                TaskStates.COMPLETED,
                TaskStates.FAILED,
                TaskStates.EXPIRED,
                TaskStates.CANCELLED,
            )
            or now < t.expires_at_ms
        ]

    def stats(self) -> dict[str, int]:
        out: dict[str, int] = {}
        for t in self._queue:
            out[t.status] = out.get(t.status, 0) + 1
        return out
