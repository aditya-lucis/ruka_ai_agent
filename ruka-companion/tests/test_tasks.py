"""RUKA VI: Tests for Remote Task Protocol and Queue.
Strictly follows RUKA-VI Chapter XVI.
"""

from __future__ import annotations

import pytest

from ruka_companion.tasks.protocol import (
    LOCAL_ONLY_CAPABILITIES,
    REMOTE_CAPABILITIES,
    TASK_FSM,
    TERMINAL_STATES,
    RemoteTask,
    TaskEvents,
    TaskStates,
    TaskValidationError,
    validate_task,
)
from ruka_companion.tasks.queue import (
    QueuePolicy,
    TaskQueue,
)


class TestTaskProtocol:
    """Uji protokol task remote & formal FSM 10-status/12-status (Part XVI)."""

    def test_happy_path_to_completion(self):
        task = RemoteTask(
            capability="filesystem.read",
            payload={"path": "C:/docs/notes.txt"},
            requester="telegram:BOS",
        )
        assert task.status == TaskStates.CREATED

        task.fire(TaskEvents.START_AUTH)
        assert task.status == TaskStates.AUTHENTICATING

        task.fire(TaskEvents.AUTH_OK)
        assert task.status == TaskStates.QUEUED

        task.fire(TaskEvents.DELIVER)
        assert task.status == TaskStates.DELIVERED

        task.fire(TaskEvents.RECEIVE)
        assert task.status == TaskStates.RECEIVED

        task.fire(TaskEvents.BEGIN_POLICY)
        assert task.status == TaskStates.POLICY_CHECK

        task.fire(TaskEvents.POLICY_PASS)
        assert task.status == TaskStates.EXECUTING

        task.mark_completed({"bytes": 1024})
        assert task.status == TaskStates.COMPLETED
        assert task.result == {"bytes": 1024}

    def test_guard_granted_rejects_without_owner_confirmed(self):
        task = RemoteTask(
            capability="terminal.execute",
            payload={"cmd": "git pull"},
            requester="telegram:BOS",
            owner_confirmed=False,
        )
        task.fire(TaskEvents.START_AUTH)
        task.fire(TaskEvents.AUTH_OK)
        task.fire(TaskEvents.DELIVER)
        task.fire(TaskEvents.RECEIVE)
        task.fire(TaskEvents.BEGIN_POLICY)
        task.fire(TaskEvents.POLICY_NEEDS_HUMAN)
        assert task.status == TaskStates.WAITING_PERMISSION

        # Guard harus menolak bila belum ada konfirmasi pemilik
        with pytest.raises(PermissionError, match="owner_confirmed"):
            task.fire(TaskEvents.GRANTED)

        # Setelah dikonfirmasi pemilik, lolos ke EXECUTING
        task.owner_confirmed = True
        task.fire(TaskEvents.GRANTED)
        assert task.status == TaskStates.EXECUTING

    def test_denied_leads_to_failed(self):
        task = RemoteTask(
            capability="terminal.execute",
            payload={"cmd": "rm -rf /"},
            requester="telegram:UNKNOWN",
        )
        task.fire(TaskEvents.START_AUTH)
        task.fire(TaskEvents.AUTH_OK)
        task.fire(TaskEvents.DELIVER)
        task.fire(TaskEvents.RECEIVE)
        task.fire(TaskEvents.BEGIN_POLICY)
        task.fire(TaskEvents.POLICY_DENY)
        assert task.status == TaskStates.FAILED

    def test_local_only_capability_rejected_at_validation(self):
        for cap in LOCAL_ONLY_CAPABILITIES:
            with pytest.raises(TaskValidationError, match="local-only"):
                validate_task(cap, {}, ttl_ms=10_000)

            with pytest.raises(TaskValidationError, match="local-only"):
                RemoteTask(
                    capability=cap,
                    payload={},
                    requester="telegram:BOS",
                )

    def test_unknown_capability_rejected(self):
        with pytest.raises(TaskValidationError, match="tak dikenal"):
            validate_task("unknown.capability", {}, ttl_ms=10_000)

    def test_payload_size_limit_8kb(self):
        big_payload = {"data": "x" * 9_000}
        with pytest.raises(TaskValidationError, match="8 KB"):
            validate_task("filesystem.read", big_payload, ttl_ms=10_000)

    def test_fsm_invariants_and_coverage(self):
        # 12 status legal, 0 unreachable
        assert len(TASK_FSM.states) == 12
        assert TASK_FSM.unreachable_states() == set()
        assert len(TERMINAL_STATES) == 4

        # Transisi ilegal melempar ValueError
        task = RemoteTask(
            capability="filesystem.read",
            payload={},
            requester="telegram:BOS",
        )
        with pytest.raises(ValueError, match="transisi task ilegal"):
            task.fire(TaskEvents.SUCCEED)

    def test_digest_and_public_projection(self):
        task = RemoteTask(
            capability="filesystem.read",
            payload={"path": "a.txt"},
            requester="telegram:BOS",
        )
        d = task.digest()
        assert len(d) == 64  # SHA-256
        pub = task.as_public()
        assert "nonce" not in pub
        assert pub["task_id"] == task.task_id
        assert pub["correlation_id"] == task.correlation_id


class TestTaskQueue:
    """Uji antrean offline-resilient & anti-eksekusi-buta saat reconnect (Part XVI)."""

    def test_deduplication_via_idempotency(self):
        clock = 1_000_000
        q = TaskQueue(clock_ms=lambda: clock)
        task = RemoteTask(
            capability="filesystem.read",
            payload={"path": "a.txt"},
            requester="telegram:BOS",
        )
        # Enqueue pertama sukses
        assert q.enqueue(task) is True
        assert task.status == TaskStates.QUEUED

        # Enqueue kedua dengan task_id yang sama ditolak (replay / double-delivery)
        assert q.enqueue(task) is False

    def test_reconnect_evaluates_stale_tasks(self):
        base = 1_000_000
        clock = base
        q = TaskQueue(clock_ms=lambda: clock)

        # Task dengan TTL 120s
        task = RemoteTask(
            capability="filesystem.read",
            payload={"path": "a.xlsx"},
            requester="telegram:BOS",
            ttl_ms=120_000,
            created_at_ms=base,
        )
        q.enqueue(task)

        # 1. Laptop hidup setelah 1 detik: task masih fresh (kept)
        clock = base + 1_000
        outcome = q.on_reconnect()
        assert outcome["kept"] == 1
        assert outcome["expired"] == 0

        # 2. Laptop tidur lama: jam melompat 200 detik kemudian
        clock = base + 200_000
        outcome = q.on_reconnect()
        assert outcome["expired"] == 1
        assert task.status == TaskStates.EXPIRED
        assert "stale at reconnect — NOT blindly executed" in (task.error or "")

    def test_reconnect_revoked_device(self):
        base = 1_000_000
        policy = QueuePolicy(revalidate_device=lambda dev_id: dev_id == "trusted-device")
        q = TaskQueue(policy=policy, clock_ms=lambda: base)

        task = RemoteTask(
            capability="filesystem.read",
            payload={},
            requester="telegram:BOS",
            device_id="revoked-device",
            created_at_ms=base,
        )
        q.enqueue(task)

        outcome = q.on_reconnect()
        assert outcome["cancelled"] == 1
        assert task.status == TaskStates.CANCELLED
        assert "device revoked" in (task.error or "")

    def test_take_ready_returns_received_task(self):
        base = 1_000_000
        q = TaskQueue(clock_ms=lambda: base)
        task = RemoteTask(
            capability="filesystem.read",
            payload={},
            requester="telegram:BOS",
            created_at_ms=base,
        )
        q.enqueue(task)

        taken = q.take_ready()
        assert taken is not None
        assert taken.task_id == task.task_id
        assert taken.status == TaskStates.RECEIVED

        # Antrean sekarang kosong
        assert q.take_ready() is None
