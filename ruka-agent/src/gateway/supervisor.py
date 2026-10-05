# -*- coding: utf-8 -*-
"""Organ Supervisor & Heartbeat Watchdog for PROJECT NOCTIS (FR-HE-01 & FR-OS-01).

Menjalankan pengawasan kesehatan organ, detak jantung (Heartbeat) 0.5 Hz
(periode 2.0 detik), pencatatan denyut tak-terhapus, dan pemulihan otonom (auto-recovery).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
import logging
from pathlib import Path
import threading
import time
from typing import Any, Callable

from src.gateway.events import Event, EventBus, OrganNamespace

log = logging.getLogger("ruka.gateway.supervisor")


class OrganState(str, Enum):
    INITIALIZING = "initializing"
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    FAILED = "failed"
    STOPPED = "stopped"


@dataclass
class OrganHealth:
    name: str
    namespace: OrganNamespace
    state: OrganState = OrganState.INITIALIZING
    last_beat: float = field(default_factory=time.time)
    error_count: int = 0
    restart_count: int = 0
    check_fn: Callable[[], bool] | None = None
    restart_fn: Callable[[], bool] | None = None


class OrganSupervisor:
    """Pengawas kesehatan seluruh organ PROJECT NOCTIS dengan detak jantung 0.5 Hz."""

    def __init__(
        self,
        event_bus: EventBus | None = None,
        state_file: str | Path | None = None,
        heartbeat_hz: float = 0.5,
    ) -> None:
        self.event_bus = event_bus
        self.heartbeat_period = 1.0 / max(0.1, heartbeat_hz)  # 2.0 detik untuk 0.5 Hz (FR-HE-01)
        self.state_file = Path(state_file).resolve() if state_file else None
        self._organs: dict[str, OrganHealth] = {}
        self._beat_counter = self._load_beat_counter()
        self._running = False
        self._thread: threading.Thread | None = None
        self._lock = threading.RLock()
        self._start_time = time.time()

    def _load_beat_counter(self) -> int:
        """Memuat nomor denyut terakhir dari disk agar resume tidak mulai dari 0 (FR-HE-01)."""
        if self.state_file and self.state_file.exists():
            try:
                data = self.state_file.read_text(encoding="utf-8").strip()
                return int(data)
            except Exception:
                return 0
        return 0

    def _save_beat_counter(self) -> None:
        if self.state_file:
            try:
                self.state_file.parent.mkdir(parents=True, exist_ok=True)
                self.state_file.write_text(str(self._beat_counter), encoding="utf-8")
            except Exception:
                pass

    @property
    def beat_counter(self) -> int:
        with self._lock:
            return self._beat_counter

    def register_organ(
        self,
        name: str,
        namespace: OrganNamespace | str,
        check_fn: Callable[[], bool] | None = None,
        restart_fn: Callable[[], bool] | None = None,
    ) -> None:
        """Mendaftarkan organ untuk diawasi kesehatannya."""
        if isinstance(namespace, OrganNamespace):
            ns = namespace
        else:
            try:
                ns = OrganNamespace(str(namespace).lower())
            except ValueError:
                ns = OrganNamespace.DEFAULT
        with self._lock:
            self._organs[name] = OrganHealth(
                name=name,
                namespace=ns,
                state=OrganState.HEALTHY,
                check_fn=check_fn,
                restart_fn=restart_fn,
            )

    def report_organ_error(self, name: str, error_msg: str = "") -> None:
        """Melaporkan kegagalan pada organ tertentu."""
        with self._lock:
            organ = self._organs.get(name)
            if organ:
                organ.error_count += 1
                if organ.error_count >= 3:
                    organ.state = OrganState.DEGRADED
                if organ.error_count >= 5:
                    organ.state = OrganState.FAILED
                log.warning("Organ '%s' melaporkan error #%d: %s", name, organ.error_count, error_msg)

    def tick(self) -> dict[str, Any]:
        """Eksekusi satu siklus detak jantung (tick) 0.5 Hz."""
        with self._lock:
            self._beat_counter += 1
            self._save_beat_counter()
            current_beat = self._beat_counter

            # Periksa kesehatan organ
            health_summary: dict[str, str] = {}
            for name, organ in self._organs.items():
                if organ.check_fn is not None:
                    try:
                        ok = organ.check_fn()
                        if ok:
                            if organ.state != OrganState.HEALTHY:
                                organ.state = OrganState.HEALTHY
                                organ.error_count = 0
                        else:
                            self.report_organ_error(name, "Liveness check returned False")
                    except Exception as ex:
                        self.report_organ_error(name, f"Liveness check exception: {ex}")

                # Auto-recovery jika organ FAILED dan memiliki restart_fn
                if organ.state == OrganState.FAILED and organ.restart_fn is not None:
                    log.info("Memicu auto-recovery untuk organ '%s' pasca kegagalan...", name)
                    try:
                        restarted = organ.restart_fn()
                        if restarted:
                            organ.restart_count += 1
                            organ.state = OrganState.HEALTHY
                            organ.error_count = 0
                            log.info("Auto-recovery organ '%s' BERHASIL (restart #%d).", name, organ.restart_count)
                    except Exception as rx:
                        log.error("Gagal melakukan auto-recovery organ '%s': %s", name, rx)

                health_summary[name] = organ.state.value

        # Pancarkan detak jantung ke EventBus V3
        pulse_data = {
            "beat": current_beat,
            "timestamp": time.time(),
            "uptime_seconds": round(time.time() - self._start_time, 2),
            "organs": health_summary,
        }
        if self.event_bus:
            self.event_bus.publish(
                Event(
                    event_type="heart.pulse",
                    source="organ_supervisor",
                    namespace=OrganNamespace.HEART.value,
                    payload=pulse_data,
                )
            )

        return pulse_data

    def start(self) -> None:
        """Memulai loop pengawasan di background thread."""
        with self._lock:
            if self._running:
                return
            self._running = True
            self._thread = threading.Thread(target=self._run_loop, daemon=True)
            self._thread.start()

    def stop(self) -> None:
        """Menghentikan loop supervisor."""
        with self._lock:
            self._running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=3.0)

    def _run_loop(self) -> None:
        while self._running:
            start_t = time.time()
            try:
                self.tick()
            except Exception as e:
                log.error("Kesalahan pada supervisor tick: %s", e)

            elapsed = time.time() - start_t
            sleep_time = max(0.05, self.heartbeat_period - elapsed)
            time.sleep(sleep_time)

    def status(self) -> dict[str, Any]:
        """Audit status pengawasan organ terkini."""
        with self._lock:
            return {
                "running": self._running,
                "beat_counter": self._beat_counter,
                "period_seconds": self.heartbeat_period,
                "uptime": round(time.time() - self._start_time, 1),
                "organs": {
                    name: {
                        "state": o.state.value,
                        "error_count": o.error_count,
                        "restart_count": o.restart_count,
                    }
                    for name, o in self._organs.items()
                },
            }
