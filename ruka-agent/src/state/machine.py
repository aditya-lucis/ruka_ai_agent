"""Expression state machine — transisi eksplisit, aman async.
Enam fase; transisi tidak sah GAGAL KERAS (bukan diabaikan) supaya
bug alur ketahuan di CI, bukan di produksi sebagai wajah aneh.
Modifier emosional adalah data pipeline ekspresi (PART 6), bukan fase.
"""
from __future__ import annotations
import asyncio
from enum import Enum
from typing import Any

class Phase(str, Enum):
    IDLE = "idle"
    LISTENING = "listening"
    THINKING = "thinking"
    TOOL_EXECUTING = "tool_executing"
    WAITING = "waiting"
    RESPONDING = "responding"

VALID: dict[Phase, frozenset[Phase]] = {
    Phase.IDLE: frozenset({Phase.LISTENING}),
    Phase.LISTENING: frozenset({Phase.THINKING}),
    Phase.THINKING: frozenset({Phase.TOOL_EXECUTING, Phase.RESPONDING}),
    Phase.TOOL_EXECUTING: frozenset({Phase.THINKING, Phase.WAITING}),
    Phase.WAITING: frozenset({Phase.THINKING}),
    Phase.RESPONDING: frozenset({Phase.IDLE}),
}

class InvalidTransition(RuntimeError):
    def __init__(self, src: Phase, dst: Phase) -> None:
        super().__init__(
            f"Transisi tidak sah: {src.value} -> {dst.value}. "
            f"Sah dari {src.value}: {sorted(p.value for p in VALID[src])}."
        )

class ExpressionFSM:
    """Satu instance per sesi. Thread/async aman lewat lock."""
    def __init__(self) -> None:
        self._phase = Phase.IDLE
        self._lock = asyncio.Lock()
        self._history: list[dict[str, Any]] = []

    @property
    def phase(self) -> Phase:
        return self._phase

    @property
    def history(self) -> list[dict[str, Any]]:
        """Jejak transisi untuk replay & audit (PART 23)."""
        return list(self._history)

    async def transition_async(self, dst: Phase, cause: str = "") -> Phase:
        """Transisi aman untuk konteks async (jalur suara PART 12)."""
        async with self._lock:
            return self._transition(dst, cause)

    def transition(self, dst: Phase, cause: str = "") -> Phase:
        """Transisi sinkron — untuk jalur teks & test."""
        return self._transition(dst, cause)

    def _transition(self, dst: Phase, cause: str) -> Phase:
        src = self._phase
        if dst not in VALID[src]:
            raise InvalidTransition(src, dst)
        self._phase = dst
        self._history.append({"from": src.value, "to": dst.value, "cause": cause})
        return dst

    def is_busy(self) -> bool:
        """Fase kerja aktif — dipakai untuk gating input & ekspresi."""
        return self._phase in (Phase.THINKING, Phase.TOOL_EXECUTING)

    def reset(self, cause: str = "session-reset") -> None:
        """Kembali ke IDLE dari fase mana pun — hanya via reset eksplisit."""
        if self._phase is not Phase.IDLE:
            self._history.append({"from": self._phase.value, "to": "idle", "cause": cause})
        self._phase = Phase.IDLE
