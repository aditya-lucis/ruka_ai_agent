# -*- coding: utf-8 -*-
"""RUKA Gateway — Internal Event Bus.

Menyediakan mekanisme Pub/Sub asinkron dan ter-decouple untuk
observability, audit jejak langkah agen, dan koordinasi antar-komponen.
"""
from __future__ import annotations

import fnmatch
import logging
import threading
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Callable

log = logging.getLogger("ruka.gateway.events")


@dataclass
class Event:
    """Peristiwa internal yang dipancarkan dalam ekosistem Gateway."""
    event_type: str                                     # "session.created", "skill.executed", dsb.
    source: str                                         # Komponen pemancar
    payload: dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)
    session_id: str | None = None
    event_id: str = field(default_factory=lambda: f"evt_{uuid.uuid4().hex[:8]}")


class EventBus:
    """Event Bus internal dengan dukungan pola wildcard (fnmatch) dan riwayat audit."""

    def __init__(self, max_history: int = 500) -> None:
        self.max_history = max_history
        self._subscribers: dict[str, tuple[str, Callable[[Event], None]]] = {}
        self._history: list[Event] = []
        self._lock = threading.RLock()

    def subscribe(self, pattern: str, handler: Callable[[Event], None]) -> str:
        """Mendaftarkan pendengar untuk pola jenis event tertentu (contoh: 'skill.*', '*')."""
        with self._lock:
            sub_id = f"sub_{uuid.uuid4().hex[:8]}"
            self._subscribers[sub_id] = (pattern, handler)
            return sub_id

    def unsubscribe(self, subscription_id: str) -> bool:
        """Membatalkan pendaftaran langganan event."""
        with self._lock:
            if subscription_id in self._subscribers:
                del self._subscribers[subscription_id]
                return True
            return False

    def publish(self, event: Event) -> None:
        """Memancarkan event ke semua pendengar yang cocok secara aman."""
        with self._lock:
            self._history.append(event)
            if len(self._history) > self.max_history:
                self._history.pop(0)
            matching_handlers = [
                handler
                for pattern, handler in self._subscribers.values()
                if fnmatch.fnmatch(event.event_type, pattern)
            ]

        for handler in matching_handlers:
            try:
                handler(event)
            except Exception as e:
                log.warning("Gagal mengeksekusi handler untuk event %s: %s", event.event_type, e)

    def history(self, limit: int = 100, event_type: str | None = None) -> list[Event]:
        """Mengambil riwayat event terbaru untuk keperluan observability."""
        with self._lock:
            filtered = [
                e
                for e in self._history
                if event_type is None or fnmatch.fnmatch(e.event_type, event_type)
            ]
            return filtered[-limit:]
