# -*- coding: utf-8 -*-
"""Unit tests for Organ Supervisor & Heartbeat Watchdog (Milestone B.3 — FR-HE-01)."""
from __future__ import annotations

from pathlib import Path
import pytest

from src.gateway.events import EventBus
from src.gateway.supervisor import OrganSupervisor, OrganState


class TestOrganSupervisor:
    def test_beat_counter_persistence_and_resume(self, tmp_path: Path) -> None:
        state_file = tmp_path / "beat.txt"
        bus = EventBus()

        sup1 = OrganSupervisor(event_bus=bus, state_file=state_file, heartbeat_hz=10.0)
        assert sup1.beat_counter == 0

        sup1.tick()
        sup1.tick()
        sup1.tick()
        assert sup1.beat_counter == 3

        # Restart instance: resume harus membaca 3, bukan mulai dari 0 (FR-HE-01)
        del sup1
        sup2 = OrganSupervisor(event_bus=bus, state_file=state_file, heartbeat_hz=10.0)
        assert sup2.beat_counter == 3
        sup2.tick()
        assert sup2.beat_counter == 4

    def test_pulse_event_published_on_heartbeat(self, tmp_path: Path) -> None:
        bus = EventBus()
        pulses = []
        bus.subscribe("heart.pulse", lambda e: pulses.append(e.payload))

        sup = OrganSupervisor(event_bus=bus, state_file=tmp_path / "beat.txt")
        sup.register_organ("TestBrain", "heart")
        sup.tick()

        assert len(pulses) == 1
        assert pulses[0]["beat"] == 1
        assert pulses[0]["organs"]["TestBrain"] == "healthy"

    def test_organ_auto_recovery_on_failure(self, tmp_path: Path) -> None:
        bus = EventBus()
        sup = OrganSupervisor(event_bus=bus, state_file=tmp_path / "beat.txt")

        restart_invoked = False

        def restart_worker() -> bool:
            nonlocal restart_invoked
            restart_invoked = True
            return True

        sup.register_organ(
            "WorkerOrgan",
            "hands",
            check_fn=lambda: False,  # Selalu gagal liveness
            restart_fn=restart_worker,
        )

        # Simulasikan kegagalan bertubi-tubi hingga FAILED
        for _ in range(5):
            sup.tick()

        # Pada tick berikutnya, auto-recovery harus terpicu
        assert restart_invoked
        st = sup.status()
        assert st["organs"]["WorkerOrgan"]["restart_count"] >= 1
