# -*- coding: utf-8 -*-
"""Crimson Heart V3 Engine & Heartbeat Loop (FR-HE).

Pengendali terpadu organ jantung Ruka / Project Noctis:
- Detak jantung 0.5 Hz (periode 2.0 detik)
- Siklus 4-tahap: Perceive -> Feel -> Think -> Act
- Integrasi dengan EventBus V3 pada OrganNamespace.HEART
- Terhubung dengan Memory Palace (recall 6 potongan sebelum berpikir, after-act remember)
- Integrasi Kontrak Darah (BloodRegistry), Matriks Eskalasi, dan HeartDoctor
"""
from __future__ import annotations

import threading
import time
from typing import Any

from src.gateway.events import Event, EventBus, OrganNamespace
from src.heart.blood import BloodRegistry
from src.heart.budget import HeartBudget
from src.heart.checkpoint import HeartCheckpointer
from src.heart.doctor import HeartDoctor
from src.heart.matrix import EscalationMatrix
from src.heart.models import DAGPlan
from src.heart.supervisor import SupervisorGraph


class CrimsonHeart:
    def __init__(
        self,
        event_bus: EventBus | None = None,
        memory_palace: Any | None = None,
        initial_beat: int = 0,
        autonomy_level: int = 2,
    ) -> None:
        self.event_bus = event_bus
        self.memory_palace = memory_palace
        self.beat_count = initial_beat
        self.is_running = False

        self.budget = HeartBudget()
        self.checkpointer = HeartCheckpointer()
        self.blood_registry = BloodRegistry()
        self.escalation = EscalationMatrix(default_autonomy_level=autonomy_level)
        self.supervisor = SupervisorGraph(checkpointer=self.checkpointer, budget=self.budget)
        self.doctor = HeartDoctor()

        self._lock = threading.Lock()
        self._current_task: DAGPlan | None = None

    def step_beat(self, now: float | None = None) -> dict[str, Any]:
        """Satu siklus detak jantung 0.5 Hz (Perceive -> Feel -> Think -> Act)."""
        current_time = now if now is not None else time.time()
        with self._lock:
            self.beat_count += 1
            beat_num = self.beat_count

        # 1. Catat ke dokter
        self.doctor.record_beat(beat_num, now=current_time)

        # 2. Phase 1: PERCEIVE (membaca konteks lingkungan)
        perceive_data = {"beat": beat_num, "timestamp": current_time}

        # 3. Phase 2: FEEL (mengunci suasana hati untuk denyut ini)
        current_mood = "loyal"

        # 4. Phase 3: THINK (kait istana memori: ambil 6 potongan memori sebelum berpikir)
        recalled_memories = []
        if self.memory_palace:
            try:
                # Ambil 6 potongan memori (proyek dulu, baru preferensi/harian)
                rec = self.memory_palace.recall("status proyek terkini", top_k=6)
                recalled_memories = rec.get("results", [])
            except Exception:
                pass

        # 5. Phase 4: ACT (menjalankan tugas jika ada di antrean)
        action_result = None
        if self._current_task:
            try:
                action_result = self.supervisor.execute_plan(self._current_task)
                self._current_task = None
            except Exception as ex:
                action_result = {"error": str(ex)}

        # Publikasikan denyut ke EventBus
        if self.event_bus:
            self.event_bus.publish(
                Event(
                    namespace=OrganNamespace.HEART.value,
                    event_type="heart.beat",
                    source="crimson_heart",
                    payload={
                        "beat_number": beat_num,
                        "mood": current_mood,
                        "recalled_count": len(recalled_memories),
                        "remaining_tokens": self.budget.remaining_tokens,
                    },
                )
            )

        return {
            "beat_number": beat_num,
            "phase": "act_completed",
            "mood": current_mood,
            "recalled_memories": recalled_memories,
            "action_result": action_result,
        }

    def assign_task(self, plan: DAGPlan) -> None:
        """Menugaskan rencana kerja ke jantung."""
        self._current_task = plan
        if self.event_bus:
            self.event_bus.publish(
                Event(
                    namespace=OrganNamespace.HEART.value,
                    event_type="heart.plan",
                    source="crimson_heart",
                    payload={
                        "task_id": plan.task_id,
                        "objective": plan.objective,
                        "steps_count": len(plan.steps),
                    },
                )
            )
