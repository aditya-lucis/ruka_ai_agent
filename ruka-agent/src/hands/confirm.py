# -*- coding: utf-8 -*-
"""Confirmation Gate for High-Risk Actions (FR-HA-06, FR-HA-07).

Mengelola kartu konfirmasi interaktif untuk aksi berisiko tinggi (RED):
- Batas waktu 60 detik mutlak.
- Jika waktu habis tanpa konfirmasi, otomatis ditolak (fail-closed).
- Menolak keras aksi jika token konfirmasi tidak cocok.
"""
from __future__ import annotations

import time
import uuid
from typing import Any
from src.hands.models import ShadowAction


class ConfirmTicket:
    def __init__(self, action: ShadowAction, description: str, timeout_s: float = 60.0) -> None:
        self.ticket_id: str = f"CONFIRM-{uuid.uuid4().hex[:8]}"
        self.action = action
        self.description = description
        self.created_at: float = time.time()
        self.timeout_s = timeout_s
        self._status: str = "pending"  # pending, approved, denied, timed_out

    @property
    def status(self) -> str:
        if self._status == "pending":
            if time.time() - self.created_at >= self.timeout_s:
                self._status = "timed_out"
        return self._status

    def approve(self) -> bool:
        if self.status == "pending":
            self._status = "approved"
            return True
        return False

    def deny(self) -> bool:
        if self.status == "pending":
            self._status = "denied"
            return True
        return False


class ConfirmGate:
    def __init__(self, default_timeout_s: float = 60.0) -> None:
        self.default_timeout_s = default_timeout_s
        self._tickets: dict[str, ConfirmTicket] = {}

    def request_confirmation(self, action: ShadowAction, description: str) -> ConfirmTicket:
        """Membuat tiket konfirmasi baru untuk aksi berisiko."""
        ticket = ConfirmTicket(action, description, timeout_s=self.default_timeout_s)
        self._tickets[ticket.ticket_id] = ticket
        return ticket

    def resolve_ticket(self, ticket_id: str, approved: bool) -> bool:
        """Menyelesaikan tiket konfirmasi oleh Young Lord."""
        ticket = self._tickets.get(ticket_id)
        if not ticket:
            return False

        if approved:
            return ticket.approve()
        else:
            return ticket.deny()

    def is_ticket_valid(self, ticket_id: str) -> bool:
        """Memeriksa apakah tiket telah disetujui secara sah sebelum eksekusi."""
        ticket = self._tickets.get(ticket_id)
        if not ticket:
            return False
        return ticket.status == "approved"
