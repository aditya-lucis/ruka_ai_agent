# -*- coding: utf-8 -*-
"""LoopGuard v0.3.1 — detektor pengulangan patologis pada agent loop.
Budget (Vol II, PART 13) membatasi TOTAL (iterasi/token/tool/time), tapi
tidak menangkap pola patologis DI DALAM anggaran: tool sama dipanggil
berulang dengan argumen identik, atau error yang sama diulang tanpa
perubahan konteks. LoopGuard menutup celah itu.
Kontrak:
- check(tool, args) -> raise LoopGuardError bila pola berulang terdeteksi.
- observe_error(signature) -> hitung error identik; sarankan abort.
- Bukan pengganti Budget — pelengkap. Orkestrator tetap memegang
  keputusan terminate; LoopGuard hanya memberi alasan terstruktur.
"""
from __future__ import annotations
import json
from collections import deque
from dataclasses import dataclass

class LoopGuardError(RuntimeError):
    """Pola berulang terdeteksi — loop dianggap patologis."""

@dataclass(frozen=True)
class LoopGuardConfig:
    max_identical_calls: int = 2     # panggilan identik berturut-turut
    window: int = 5                  # jendela history yang diperiksa
    max_identical_errors: int = 3    # error identik berturut-turut

@dataclass
class LoopGuardState:
    identical_calls: int = 0
    identical_errors: int = 0

class LoopGuard:
    def __init__(self, config: LoopGuardConfig | None = None) -> None:
        self._cfg = config or LoopGuardConfig()
        self._history: deque[str] = deque(maxlen=self._cfg.window)
        self._errors: deque[str] = deque(maxlen=self._cfg.window)
        self.state = LoopGuardState()

    @staticmethod
    def _fingerprint(tool: str, args: dict) -> str:
        try:
            payload = json.dumps(args, sort_keys=True, default=str)
        except (TypeError, ValueError):        # objek aneh -> repr
            payload = repr(args)
        return f"{tool}:{payload}"

    def check(self, tool: str, args: dict) -> None:
        """Panggil SEBELUM eksekusi tool. Raise bila repetitif."""
        fp = self._fingerprint(tool, args)
        self._history.append(fp)
        tail = list(self._history)[-self._cfg.max_identical_calls:]
        self.state.identical_calls = 0
        if (len(tail) == self._cfg.max_identical_calls
                and len(set(tail)) == 1):
            self.state.identical_calls = self._cfg.max_identical_calls
            raise LoopGuardError(
                f"tool '{tool}' dipanggil {self._cfg.max_identical_calls}x "
                f"berturut-turut dengan argumen identik — loop patologis. "
                f"Ubah rencana atau perbaiki tool, jangan ulangi."
            )

    def observe_error(self, error_signature: str) -> None:
        """Panggil SETELAH error. Bila identik beruntun, angkat bendera."""
        self._errors.append(error_signature)
        tail = list(self._errors)[-self._cfg.max_identical_errors:]
        self.state.identical_errors = 0
        if (len(tail) == self._cfg.max_identical_errors
                and len(set(tail)) == 1):
            self.state.identical_errors = self._cfg.max_identical_errors

    def should_abort(self) -> str | None:
        """Alasan abort terstruktur, atau None bila sehat."""
        if self.state.identical_errors >= self._cfg.max_identical_errors:
            return ("error identik beruntun — perbaikan tidak efektif; "
                    "hentikan dan eskalasi")
        return None
