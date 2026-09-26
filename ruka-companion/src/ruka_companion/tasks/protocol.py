"""RUKA VI: Real-Time Remote Execution — Task Protocol & 10-Status Formal FSM.
Strictly follows RUKA-VI Chapter XVI (baris 52-215).
"""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import time
from typing import Any
import uuid

from ruka_companion.math.discrete import FSM, Transition


class TaskStates:
    """Status formal task remote (Part XVI)."""

    CREATED = "CREATED"
    AUTHENTICATING = "AUTHENTICATING"
    QUEUED = "QUEUED"
    DELIVERED = "DELIVERED"
    RECEIVED = "RECEIVED"
    POLICY_CHECK = "POLICY_CHECK"
    WAITING_PERMISSION = "WAITING_PERMISSION"
    EXECUTING = "EXECUTING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    EXPIRED = "EXPIRED"
    CANCELLED = "CANCELLED"


class TaskEvents:
    """Peristiwa pemicu transisi status task remote."""

    START_AUTH = "START_AUTH"
    AUTH_OK = "AUTH_OK"
    AUTH_FAIL = "AUTH_FAIL"
    DELIVER = "DELIVER"
    RECEIVE = "RECEIVE"
    BEGIN_POLICY = "BEGIN_POLICY"
    POLICY_PASS = "POLICY_PASS"
    POLICY_NEEDS_HUMAN = "POLICY_NEEDS_HUMAN"
    POLICY_DENY = "POLICY_DENY"
    GRANTED = "GRANTED"
    DENIED = "DENIED"
    EXECUTE = "EXECUTE"
    SUCCEED = "SUCCEED"
    FAIL = "FAIL"
    EXPIRE = "EXPIRE"
    CANCEL = "CANCEL"


def _build_fsm() -> FSM:
    T, E = TaskStates, TaskEvents
    transitions = [
        Transition(T.CREATED, E.START_AUTH, T.AUTHENTICATING),
        Transition(T.AUTHENTICATING, E.AUTH_OK, T.QUEUED),
        Transition(T.AUTHENTICATING, E.AUTH_FAIL, T.FAILED),
        Transition(T.QUEUED, E.DELIVER, T.DELIVERED),
        Transition(T.QUEUED, E.EXPIRE, T.EXPIRED),
        Transition(T.QUEUED, E.CANCEL, T.CANCELLED),
        Transition(T.DELIVERED, E.RECEIVE, T.RECEIVED),
        Transition(T.DELIVERED, E.EXPIRE, T.EXPIRED),
        Transition(T.DELIVERED, E.CANCEL, T.CANCELLED),
        Transition(T.RECEIVED, E.BEGIN_POLICY, T.POLICY_CHECK),
        Transition(T.RECEIVED, E.EXPIRE, T.EXPIRED),
        Transition(T.POLICY_CHECK, E.POLICY_PASS, T.EXECUTING),
        Transition(T.POLICY_CHECK, E.POLICY_NEEDS_HUMAN, T.WAITING_PERMISSION),
        Transition(T.POLICY_CHECK, E.POLICY_DENY, T.FAILED),
        Transition(T.POLICY_CHECK, E.EXPIRE, T.EXPIRED),
        Transition(
            T.WAITING_PERMISSION,
            E.GRANTED,
            T.EXECUTING,
            guard="owner_confirmation",
        ),
        Transition(T.WAITING_PERMISSION, E.DENIED, T.FAILED),
        Transition(T.WAITING_PERMISSION, E.EXPIRE, T.EXPIRED),
        Transition(T.EXECUTING, E.SUCCEED, T.COMPLETED),
        Transition(T.EXECUTING, E.FAIL, T.FAILED),
        Transition(T.EXECUTING, E.EXPIRE, T.EXPIRED),
    ]
    terminal = {T.COMPLETED, T.FAILED, T.EXPIRED, T.CANCELLED}
    return FSM(
        "remote-task",
        [getattr(T, n) for n in vars(T) if not n.startswith("_")],
        transitions,
        initial=T.CREATED,
        terminal=terminal,
    )


TASK_FSM = _build_fsm()
TERMINAL_STATES = frozenset(
    {
        TaskStates.COMPLETED,
        TaskStates.FAILED,
        TaskStates.EXPIRED,
        TaskStates.CANCELLED,
    }
)

# Kapabilitas yang boleh dirutekan remote (default-deny: yang tak terdaftar = tolak)
REMOTE_CAPABILITIES: frozenset[str] = frozenset(
    {
        "filesystem.read",
        "filesystem.write",
        "terminal.execute",
        "vscode.read",
        "vscode.write",
        "excel.read",
        "excel.write",
        "word.read",
        "word.write",
        "pdf.read",
        "memory.read",
        "presence.query",
        "task.status",
    }
)

# TIDAK PERNAH dirutekan remote (keputusan kebijakan — lokal murni):
LOCAL_ONLY_CAPABILITIES: frozenset[str] = frozenset(
    {
        "camera.capture",
        "microphone.capture",
        "memory.delete",
        "permission.grant",
        "plugin.install",
        "identity.enroll",
    }
)


class TaskValidationError(ValueError):
    pass


def validate_task(capability: str, payload: dict[str, Any], ttl_ms: int) -> None:
    """Validasi ENVELOPE (bukan isi): kapabilitas dikenal, payload JSON-able kecil, TTL positif."""
    if capability in LOCAL_ONLY_CAPABILITIES:
        raise TaskValidationError(
            f"kapabilitas {capability} TIDAK dirutekan remote (local-only)"
        )
    if capability not in REMOTE_CAPABILITIES:
        raise TaskValidationError(f"kapabilitas tak dikenal: {capability}")
    if len(str(payload)) > 8_192:
        raise TaskValidationError("payload melebihi 8 KB")
    if ttl_ms <= 0:
        raise TaskValidationError("ttl_ms > 0")


@dataclass
class RemoteTask:
    """Satu perintah remote — identitas task = task_id (UUID).
    Field anti-serangan:
        nonce        — angka acak 128-bit unik per task (replay)
        correlation  — ID ujung-ke-ujung (observabilitas, event log)
        expires_at   — kedaluwarsa mutlak (ms epoch)
    """

    capability: str
    payload: dict[str, Any]
    requester: str  # 'telegram:BOS_ID' | 'cloud:relay'
    device_id: str = "local-01"
    task_id: str = field(default_factory=lambda: f"task-{uuid.uuid4().hex}")
    correlation_id: str = field(default_factory=lambda: uuid.uuid4().hex[:16])
    nonce: str = field(default_factory=lambda: uuid.uuid4().hex)
    created_at_ms: int = field(default_factory=lambda: int(time.time() * 1000))
    ttl_ms: int = 120_000  # 2 menit default
    status: str = TaskStates.CREATED
    result: dict[str, Any] | None = None
    error: str | None = None
    owner_confirmed: bool = False  # bukti konfirmasi manusia (guard)
    _now: Any = field(
        default_factory=lambda: int(time.time() * 1000), repr=False, compare=False
    )

    def __post_init__(self) -> None:
        validate_task(self.capability, self.payload, self.ttl_ms)
        self.expires_at_ms = self.created_at_ms + self.ttl_ms

    # --------------------------------------------------------------- lifecycle
    def fire(self, event: str) -> str:
        """δ(status, event) dengan pemeriksaan kedaluwarsa + guard pemilik."""
        now = int(time.time() * 1000)
        # kedaluwarsa: hanya kecuali sudah terminal
        if self.status not in TERMINAL_STATES and now >= self.expires_at_ms:
            nxt = TASK_FSM.fire(self.status, TaskEvents.EXPIRE)
            if nxt is not None:
                self.status = nxt
                self.error = "expired before execution"
                return self.status
        nxt = TASK_FSM.fire(self.status, event)
        if nxt is None:
            raise ValueError(f"transisi task ilegal: ({self.status}, {event})")
        # guard: GRANTED hanya valid dengan konfirmasi pemilik
        if (
            self.status == TaskStates.WAITING_PERMISSION
            and event == TaskEvents.GRANTED
            and not self.owner_confirmed
        ):
            raise PermissionError("GRANTED tanpa owner_confirmed — replay? ditolak")
        self.status = nxt
        return self.status

    def is_expired(self, now_ms: int | None = None) -> bool:
        now = now_ms if now_ms is not None else int(time.time() * 1000)
        return now >= self.expires_at_ms

    def mark_completed(self, result: dict[str, Any]) -> None:
        self.fire(TaskEvents.SUCCEED)
        self.result = result

    def mark_failed(self, error: str) -> None:
        self.fire(TaskEvents.FAIL)
        self.error = error

    # --------------------------------------------------------------- metadata
    def digest(self) -> str:
        """Sidik jari task (id + nonce + capability) — untuk audit & dedupe."""
        h = hashlib.sha256()
        h.update(self.task_id.encode())
        h.update(self.nonce.encode())
        h.update(self.capability.encode())
        h.update(str(sorted(self.payload.items())).encode())
        return h.hexdigest()

    def as_public(self) -> dict[str, Any]:
        """Proyeksi aman untuk pengiriman (nonce TIDAK dibocorkan utuh)."""
        return {
            "task_id": self.task_id,
            "capability": self.capability,
            "requester": self.requester,
            "status": self.status,
            "correlation_id": self.correlation_id,
            "created_at_ms": self.created_at_ms,
            "expires_at_ms": self.expires_at_ms,
        }
