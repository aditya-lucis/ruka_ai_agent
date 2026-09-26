"""RUKA VI: Vision Camera Core — SensorStateMachine, Frame, and CameraSource.
Strictly follows RUKA-VI Chapter XIII (Vision).
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from enum import Enum
from typing import Any, Iterator

import numpy as np


class SensorState(str, Enum):
    OFF = "OFF"
    IDLE = "IDLE"
    ARMED = "ARMED"
    ACTIVE = "ACTIVE"
    PROCESSING = "PROCESSING"
    ERROR = "ERROR"


_SENSOR_TRANSITIONS: dict[tuple[str, str], None] = {
    ("OFF", "IDLE"): None,
    ("OFF", "ERROR"): None,
    ("IDLE", "ARMED"): None,
    ("IDLE", "OFF"): None,
    ("IDLE", "ERROR"): None,
    ("ARMED", "ACTIVE"): None,
    ("ARMED", "IDLE"): None,
    ("ARMED", "OFF"): None,
    ("ACTIVE", "PROCESSING"): None,
    ("ACTIVE", "IDLE"): None,
    ("ACTIVE", "ERROR"): None,
    ("ACTIVE", "OFF"): None,
    ("PROCESSING", "ACTIVE"): None,
    ("PROCESSING", "IDLE"): None,
    ("PROCESSING", "ERROR"): None,
    ("ERROR", "IDLE"): None,
    ("ERROR", "OFF"): None,
}


class SensorStateMachine:
    """FSM sensor + daftar transisi legal — pelanggaran = ditolak keras."""

    def __init__(self, initial: SensorState = SensorState.OFF) -> None:
        self._state = initial
        self._history: list[tuple[int, str, str]] = []

    @property
    def state(self) -> SensorState:
        return self._state

    def transition(self, event: str) -> SensorState:
        """event = nama status TUJUAN ('ACTIVE', 'OFF', ...)."""
        target = SensorState(event)
        key = (self._state.value, target.value)
        if key not in _SENSOR_TRANSITIONS:
            raise ValueError(f"transisi sensor ilegal: {self._state.value} → {target.value}")
        self._state = target
        self._history.append((int(time.time() * 1000), key[0], key[1]))
        return self._state

    def legal_transitions(self) -> list[str]:
        return sorted(t for (s, t) in _SENSOR_TRANSITIONS if s == self._state.value)

    def history(self) -> list[tuple[int, str, str]]:
        return list(self._history)


@dataclass
class Frame:
    pixels: np.ndarray  # BGR uint8 (h, w, 3) — konvensi OpenCV
    index: int
    captured_at_ms: int
    source: str = "camera"


class CameraSource:
    """Kamera OpenCV — import malas, laporan kejujuran, iterator frame."""

    def __init__(self, device_index: int = 0) -> None:
        self.device_index = device_index
        self.fsm = SensorStateMachine(SensorState.OFF)
        self._cap: Any = None
        self._frame_index = 0

    def capability(self) -> dict[str, Any]:
        info: dict[str, Any] = {
            "layer": "device",
            "kind": "camera",
            "device_index": self.device_index,
            "sensor_state": self.fsm.state.value,
        }
        try:
            import cv2  # noqa: PLC0415

            info["opencv"] = cv2.__version__
            cap = cv2.VideoCapture(self.device_index)
            opened = bool(cap.isOpened())
            cap.release()
            info.update({"available": opened})
        except Exception as exc:  # pragma: no cover
            info.update({"available": False, "reason": f"{type(exc).__name__}: {exc}"})
        return info

    def open(self) -> None:
        """OFF/IDLE → mulai ambil frame (ACTIVE)."""
        import cv2  # noqa: PLC0415

        if self._cap is None:
            self._cap = cv2.VideoCapture(self.device_index)
            if not self._cap.isOpened():
                self.fsm.transition("ERROR")
                self._cap = None
                raise RuntimeError(f"kamera {self.device_index} tak bisa dibuka")
        if self.fsm.state == SensorState.OFF:
            self.fsm.transition("IDLE")
        self.fsm.transition("ACTIVE")

    def close(self) -> None:
        if self._cap is not None:
            self._cap.release()
            self._cap = None
        if self.fsm.state not in (SensorState.OFF,):
            if self.fsm.state != SensorState.IDLE:
                self.fsm.transition("IDLE")
            self.fsm.transition("OFF")

    def frames(self, n: int | None = None) -> Iterator[Frame]:
        """Iterator frame — hanya legal saat ACTIVE. n = batas jumlah."""
        if self.fsm.state != SensorState.ACTIVE or self._cap is None:
            raise RuntimeError("kamera belum aktif — panggil open() dahulu")
        count = 0
        while n is None or count < n:
            ret, frame = self._cap.read()
            if not ret or frame is None:
                break
            self._frame_index += 1
            count += 1
            yield Frame(
                pixels=frame,
                index=self._frame_index,
                captured_at_ms=int(time.time() * 1000),
                source=f"camera:{self.device_index}",
            )
