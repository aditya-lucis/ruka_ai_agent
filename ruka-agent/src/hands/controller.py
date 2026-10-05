# -*- coding: utf-8 -*-
"""Shadow Hands Automation Controller (FR-HA).

Pengendali terpadu modul otomasi desktop Ruka / Project Noctis:
- Satu gerbang izin (ActionGate) dengan kebijakan gagal-tertutup
- Jalur pekerja single-writer (antrean 64, rate-limit 8 aksi/detik)
- Trajektori mouse Bezier kuadratik berjitter dan keyboard unicode aman
- Gerbang konfirmasi interaktif 60 detik
- Kill switch tiga pintu (< 200 ms)
- Jejak audit SQLite INSERT-only
- Terintegrasi dengan EventBus V3 pada OrganNamespace.HANDS
"""
from __future__ import annotations

import time
from typing import Any

from src.gateway.events import Event, EventBus, OrganNamespace
from src.hands.audit import AuditTrail
from src.hands.bezier import HumanMouseTrajectory
from src.hands.confirm import ConfirmGate, ConfirmTicket
from src.hands.gate import ActionGate
from src.hands.input_os import SafeInputOS
from src.hands.models import (
    ClickAction,
    KeyAction,
    PermissionVerdict,
    RiskLevel,
    ScrollAction,
    ShadowAction,
    TypeAction,
    WaitAction,
    validate_action,
)
from src.hands.worker import SingleWriterWorker


class ShadowHands:
    def __init__(
        self,
        event_bus: EventBus | None = None,
        audit_db_path: str = ":memory:",
        simulate_input: bool = True,
        policy_healthy: bool = True,
    ) -> None:
        self.event_bus = event_bus
        self.gate = ActionGate(policy_healthy=policy_healthy)
        self.mouse = HumanMouseTrajectory()
        self.keyboard = SafeInputOS(simulate=simulate_input)
        self.confirm_gate = ConfirmGate()
        self.worker = SingleWriterWorker(queue_capacity=64, max_rate_per_sec=8.0)
        self.audit = AuditTrail(db_path=audit_db_path)
        self.current_cursor_pos: tuple[int, int] = (0, 0)

    def request_confirmation(self, action: ShadowAction, description: str) -> ConfirmTicket:
        """Membuat tiket konfirmasi untuk aksi tingkat risiko RED."""
        validate_action(action)
        ticket = self.confirm_gate.request_confirmation(action, description)
        if self.event_bus:
            self.event_bus.publish(
                Event(
                    namespace=OrganNamespace.HANDS.value,
                    event_type="hands.confirm_request",
                    source="shadow_hands",
                    payload={
                        "ticket_id": ticket.ticket_id,
                        "action": type(action).__name__,
                        "description": description,
                    },
                )
            )
        return ticket

    def resolve_confirmation(self, ticket_id: str, approved: bool) -> bool:
        """Menyelesaikan tiket konfirmasi."""
        ok = self.confirm_gate.resolve_ticket(ticket_id, approved)
        if self.event_bus:
            self.event_bus.publish(
                Event(
                    namespace=OrganNamespace.HANDS.value,
                    event_type="hands.confirm_result",
                    source="shadow_hands",
                    payload={"ticket_id": ticket_id, "approved": approved, "success": ok},
                )
            )
        return ok

    def kill_all(self) -> float:
        """Memicu kill switch darurat (< 200 ms)."""
        latency_ms = self.worker.trigger_kill_switch()
        if self.event_bus:
            self.event_bus.publish(
                Event(
                    namespace=OrganNamespace.HANDS.value,
                    event_type="hands.kill",
                    source="shadow_hands",
                    payload={"latency_ms": latency_ms, "status": "quiescent"},
                )
            )
        return latency_ms

    def _execute_low_level(self, action: ShadowAction) -> dict[str, Any]:
        """Eksekutor fisik input desktop yang aman."""
        if isinstance(action, ClickAction):
            path = self.mouse.generate_path(self.current_cursor_pos, (action.x, action.y))
            self.current_cursor_pos = (action.x, action.y)
            return {
                "action": "click",
                "x": action.x,
                "y": action.y,
                "path_points": len(path),
                "button": action.button,
            }
        elif isinstance(action, TypeAction):
            typed = self.keyboard.type_unicode(action.text, interval_ms=action.interval_ms)
            return {"action": "type", "chars": typed}
        elif isinstance(action, KeyAction):
            ok = self.keyboard.press_key_combination(action.key, modifiers=action.modifiers)
            return {"action": "key", "key": action.key, "success": ok}
        elif isinstance(action, ScrollAction):
            return {"action": "scroll", "dx": action.dx, "dy": action.dy}
        elif isinstance(action, WaitAction):
            return {"action": "wait", "duration_ms": action.duration_ms}
        return {"action": "unknown"}

    def execute_action(
        self,
        action: ShadowAction,
        target_context: str = "",
        risk_level: RiskLevel = RiskLevel.GREEN,
        ticket_id: str | None = None,
    ) -> dict[str, Any]:
        """Mengevaluasi izin, memasukkan ke antrean worker, dan mencatat audit trail."""
        validate_action(action)
        action_name = type(action).__name__

        # 1. Evaluasi Izin Gerbang
        verdict = self.gate.evaluate(
            action=action, target_context=target_context, risk_level=risk_level
        )

        # 2. Penanganan Aksi yang Membutuhkan Konfirmasi (RED)
        if verdict == PermissionVerdict.CONFIRM:
            if not ticket_id or not self.confirm_gate.is_ticket_valid(ticket_id):
                self.audit.record_action(action_name, target_context, verdict.value, verified=False)
                return {
                    "verdict": verdict.value,
                    "status": "awaiting_or_invalid_confirmation",
                    "action": action_name,
                }

        # 3. Penolakan Keras (DENY)
        if verdict == PermissionVerdict.DENY:
            self.audit.record_action(action_name, target_context, verdict.value, verified=False)
            return {
                "verdict": verdict.value,
                "status": "denied",
                "action": action_name,
            }

        # 4. Enqueue ke Worker Single-Writer
        enqueued = self.worker.enqueue(action, self._execute_low_level)
        if not enqueued:
            return {
                "verdict": verdict.value,
                "status": "worker_killed_or_rejected",
                "action": action_name,
            }

        # 5. Jalankan langkah worker
        result = self.worker.step()

        # 6. Catat Audit Trail INSERT-only
        self.audit.record_action(action_name, target_context, verdict.value, verified=True)

        if self.event_bus:
            self.event_bus.publish(
                Event(
                    namespace=OrganNamespace.HANDS.value,
                    event_type="hands.action",
                    source="shadow_hands",
                    payload={
                        "action": action_name,
                        "verdict": verdict.value,
                        "result": result,
                    },
                )
            )

        return {
            "verdict": verdict.value,
            "status": "success",
            "action": action_name,
            "result": result,
        }
