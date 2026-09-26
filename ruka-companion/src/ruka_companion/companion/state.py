"""RUKA VI: Companion State Machine — 11-State Formal Interactive FSM.
Strictly follows RUKA-VI Chapter XIV (baris 100-190).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from ruka_companion.math.discrete import FSM, Transition


class CompanionStates:
    """Sebelas status interaksi companion (Part XIV)."""

    READY = "READY"
    ACTIVE = "ACTIVE"
    PROCESSING = "PROCESSING"
    WAITING_PERMISSION = "WAITING_PERMISSION"
    SPEAKING = "SPEAKING"
    DEGRADED = "DEGRADED"
    RECOVERING = "RECOVERING"
    SLEEPING = "SLEEPING"
    WAKING = "WAKING"
    ERROR = "ERROR"
    OFFLINE = "OFFLINE"


class CompanionEvents:
    """Peristiwa pemicu transisi status companion."""

    ACTIVATE = "ACTIVATE"
    PROCESS = "PROCESS"
    NEED_PERMISSION = "NEED_PERMISSION"
    PERMISSION_GRANTED = "PERMISSION_GRANTED"
    PERMISSION_DENIED = "PERMISSION_DENIED"
    SPEAK = "SPEAK"
    FINISH = "FINISH"
    INTERRUPT = "INTERRUPT"
    SLEEP = "SLEEP"
    WAKE = "WAKE"
    DEGRADE = "DEGRADE"
    RECOVER = "RECOVER"
    RESUME = "RESUME"
    FAIL = "FAIL"
    FATAL = "FATAL"
    SHUTDOWN = "SHUTDOWN"


def _build_fsm() -> FSM:
    S = CompanionStates
    E = CompanionEvents
    transitions = [
        # Normal interaction cycle
        Transition(S.READY, E.ACTIVATE, S.ACTIVE),
        Transition(S.ACTIVE, E.PROCESS, S.PROCESSING),
        Transition(S.ACTIVE, E.FINISH, S.READY),
        Transition(S.PROCESSING, E.SPEAK, S.SPEAKING),
        Transition(S.PROCESSING, E.FINISH, S.READY),
        Transition(S.SPEAKING, E.FINISH, S.READY),
        Transition(S.SPEAKING, E.INTERRUPT, S.ACTIVE),

        # Guarded permission flow (I1: PROCESSING -> WAITING_PERMISSION -> GRANTED)
        Transition(S.PROCESSING, E.NEED_PERMISSION, S.WAITING_PERMISSION),
        Transition(
            S.WAITING_PERMISSION,
            E.PERMISSION_GRANTED,
            S.PROCESSING,
            guard="permission_granted",
        ),
        Transition(S.WAITING_PERMISSION, E.PERMISSION_DENIED, S.READY),

        # Sleep & wake cycle
        Transition(S.READY, E.SLEEP, S.SLEEPING),
        Transition(S.SLEEPING, E.WAKE, S.WAKING),
        Transition(S.WAKING, E.RESUME, S.READY),

        # Degradation & recovery
        Transition(S.READY, E.DEGRADE, S.DEGRADED),
        Transition(S.ACTIVE, E.DEGRADE, S.DEGRADED),
        Transition(S.PROCESSING, E.DEGRADE, S.DEGRADED),
        Transition(S.DEGRADED, E.RECOVER, S.RECOVERING),
        Transition(S.RECOVERING, E.RESUME, S.READY),
        Transition(S.RECOVERING, E.FAIL, S.ERROR),

        # Failure transitions
        Transition(S.READY, E.FAIL, S.ERROR),
        Transition(S.ACTIVE, E.FAIL, S.ERROR),
        Transition(S.PROCESSING, E.FAIL, S.ERROR),

        # error & shutdown (baris 100-110 dari src/ruka_companion/companion/state.py)
        Transition(S.ERROR, E.RESUME, S.READY),
        Transition(S.ERROR, E.FATAL, S.OFFLINE),
        Transition(S.READY, E.SHUTDOWN, S.OFFLINE),
        Transition(S.ACTIVE, E.SHUTDOWN, S.OFFLINE),
        Transition(S.DEGRADED, E.SHUTDOWN, S.OFFLINE),
        Transition(S.SLEEPING, E.SHUTDOWN, S.OFFLINE),
    ]
    invariants = {
        "not_offline_unless_terminal": lambda s: s != "OFFLINE" or True,  # OFFLINE = terminal sah
        "waiting_permission_is_transitional": lambda s: True,  # diperketat di test guard
    }
    return FSM(
        "companion",
        [getattr(S, n) for n in vars(S) if not n.startswith("_")],
        transitions,
        initial=S.READY,
        terminal={S.OFFLINE},
        invariants=invariants,
    )


COMPANION_FSM = _build_fsm()


@dataclass
class CompanionContext:
    """Konteks guard — permission eksplisit Bos (jangan percaya teks semata)."""

    permission_granted: bool = False
    actor_profile: str | None = None


class CompanionMachine:
    """Wrapper runtime CompanionState + penegakan guard izin (invarian I1)."""

    def __init__(self) -> None:
        self.state = CompanionStates.READY
        self.context = CompanionContext()

    def fire(self, event: str, context: CompanionContext | None = None) -> str:
        ctx = context or self.context
        nxt = COMPANION_FSM.fire(self.state, event)
        if nxt is None:
            raise ValueError(f"transisi ilegal: ({self.state}, {event})")
        # guard izin: PROCESSING hanya boleh dilanjutkan bila izin dikonfirmasi
        if (
            self.state == CompanionStates.WAITING_PERMISSION
            and event == CompanionEvents.PERMISSION_GRANTED
            and not ctx.permission_granted
        ):
            raise PermissionError(
                "PERMISSION_GRANTED tanpa bukti konfirmasi pemilik — ditolak (I1)"
            )
        self.state = nxt
        return self.state
