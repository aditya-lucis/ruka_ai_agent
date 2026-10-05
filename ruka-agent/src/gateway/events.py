# -*- coding: utf-8 -*-
"""RUKA Gateway — EventBus V3 (PROJECT NOCTIS Architecture).

Menyediakan tulang punggung pesan Pub/Sub asinkron, ter-decouple, dan aman:
- Namespace isolation per organ (presence, ear, eyes, voice, heart, hands, memory, system).
- Disiplin Single-Writer per namespace/kanal.
- Antrean Bounded Buffer dengan kebijakan Drop-Oldest (anti memory leak).
- Publish-Only semantics (nol panggilan langsung antar-organ).
- Kompatibilitas mundur 100% untuk event_type dan pattern subscribe lama.
"""
from __future__ import annotations

from collections import deque
from enum import Enum
import fnmatch
import logging
import threading
import time
from typing import Any, Callable
import uuid
from dataclasses import dataclass, field

log = logging.getLogger("ruka.gateway.events")


class OrganNamespace(str, Enum):
    """Namespace resmi organ-organ PROJECT NOCTIS."""
    PRESENCE = "presence"
    EAR = "ear"
    EYES = "eyes"
    VOICE = "voice"
    HEART = "heart"
    HANDS = "hands"
    MEMORY = "memory"
    CONVERSE = "converse"
    SYSTEM = "system"
    DEFAULT = "default"


@dataclass
class Event:
    """Peristiwa internal yang dipancarkan dalam ekosistem Gateway & Organ Noctis."""
    event_type: str                                     # "session.created", "heart.pulse", dsb.
    source: str                                         # Komponen/organ pemancar
    payload: dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)
    session_id: str | None = None
    event_id: str = field(default_factory=lambda: f"evt_{uuid.uuid4().hex[:8]}")
    namespace: str = OrganNamespace.DEFAULT.value
    provenance: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        # Jika namespace masih default tapi event_type berbentuk "namespace.topic", otomatis ekstrak namespace
        if self.namespace == OrganNamespace.DEFAULT.value and "." in self.event_type:
            prefix = self.event_type.split(".", 1)[0].lower()
            valid_namespaces = {ns.value for ns in OrganNamespace}
            if prefix in valid_namespaces:
                self.namespace = prefix


class ChannelBuffer:
    """Antrean berkapasitas tetap dengan disiplin Drop-Oldest (SAD 2.3 & FR-HA-02)."""

    def __init__(self, capacity: int = 64) -> None:
        self.capacity = max(1, capacity)
        self._queue: deque[Event] = deque(maxlen=self.capacity)
        self._dropped_count = 0
        self._lock = threading.Lock()

    def push(self, event: Event) -> bool:
        """Memasukkan event. Jika kapasitas penuh, event terlama dibuang (drop-oldest)."""
        with self._lock:
            if len(self._queue) >= self.capacity:
                self._dropped_count += 1
            self._queue.append(event)
            return True

    def pop(self) -> Event | None:
        """Mengambil event tertua dari antrean."""
        with self._lock:
            if self._queue:
                return self._queue.popleft()
            return None

    def peek_all(self) -> list[Event]:
        """Melihat seluruh isi antrean saat ini tanpa membuang."""
        with self._lock:
            return list(self._queue)

    def drain(self, limit: int = 64) -> list[Event]:
        """Mengambil hingga limit event tertua dari antrean."""
        with self._lock:
            items: list[Event] = []
            while self._queue and len(items) < limit:
                items.append(self._queue.popleft())
            return items

    @property
    def dropped_count(self) -> int:
        with self._lock:
            return self._dropped_count

    def __len__(self) -> int:
        with self._lock:
            return len(self._queue)


class EventBus:
    """EventBus V3: Tulang punggung komunikasi antar-organ PROJECT NOCTIS."""

    def __init__(self, max_history: int = 500, default_channel_capacity: int = 64) -> None:
        self.max_history = max_history
        self.default_channel_capacity = default_channel_capacity
        self._subscribers: dict[str, tuple[str, Callable[[Event], None]]] = {}
        self._history: list[Event] = []
        self._channel_buffers: dict[str, ChannelBuffer] = {}
        self._writers: dict[str, str] = {}  # namespace -> writer_id
        self._lock = threading.RLock()

    def _get_channel_buffer(self, namespace: str) -> ChannelBuffer:
        if namespace not in self._channel_buffers:
            self._channel_buffers[namespace] = ChannelBuffer(capacity=self.default_channel_capacity)
        return self._channel_buffers[namespace]

    def claim_writer(self, namespace: str | OrganNamespace, writer_id: str) -> bool:
        """Menetapkan single-writer eksklusif untuk namespace tertentu (disiplin Single-Writer)."""
        ns_str = namespace.value if isinstance(namespace, OrganNamespace) else str(namespace)
        with self._lock:
            current = self._writers.get(ns_str)
            if current and current != writer_id:
                log.warning("Klaim writer gagal: %s sudah dikuasai oleh %s", ns_str, current)
                return False
            self._writers[ns_str] = writer_id
            return True

    def release_writer(self, namespace: str | OrganNamespace, writer_id: str) -> bool:
        """Melepaskan klaim single-writer dari sebuah namespace."""
        ns_str = namespace.value if isinstance(namespace, OrganNamespace) else str(namespace)
        with self._lock:
            if self._writers.get(ns_str) == writer_id:
                del self._writers[ns_str]
                return True
            return False

    def subscribe(self, pattern: str, handler: Callable[[Event], None]) -> str:
        """Mendaftarkan pendengar untuk pola jenis event tertentu (contoh: 'skill.*', 'presence.*', '*')."""
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

    def publish(self, event: Event, writer_id: str | None = None) -> bool:
        """Memancarkan event ke antrean kanal dan semua pendengar yang cocok secara aman."""
        with self._lock:
            # Validasi single-writer jika namespace telah diklaim
            claimed_writer = self._writers.get(event.namespace)
            if claimed_writer is not None and writer_id != claimed_writer:
                log.warning(
                    "Penolakan publish ke namespace '%s': pengirim '%s' bukan pemilik sah '%s'",
                    event.namespace,
                    writer_id or event.source,
                    claimed_writer,
                )
                return False

            # Masukkan ke bounded buffer kanal (Drop-Oldest)
            buf = self._get_channel_buffer(event.namespace)
            buf.push(event)

            # Catat ke riwayat global (observability)
            self._history.append(event)
            if len(self._history) > self.max_history:
                self._history.pop(0)

            # Cocokkan subscriber berdasarkan event_type atau namespace.event_type
            matching_handlers = [
                handler
                for pattern, handler in self._subscribers.values()
                if fnmatch.fnmatch(event.event_type, pattern)
                or fnmatch.fnmatch(f"{event.namespace}.{event.event_type}", pattern)
            ]

        # Eksekusi handler di luar lock agar tidak memblokir bus
        for handler in matching_handlers:
            try:
                handler(event)
            except Exception as e:
                log.warning("Gagal mengeksekusi handler untuk event %s: %s", event.event_type, e)

        return True

    def channel_queue(self, namespace: str | OrganNamespace) -> ChannelBuffer:
        """Mengakses antrean bounded buffer dari sebuah namespace."""
        ns_str = namespace.value if isinstance(namespace, OrganNamespace) else str(namespace)
        with self._lock:
            return self._get_channel_buffer(ns_str)

    def history(self, limit: int = 100, event_type: str | None = None, namespace: str | None = None) -> list[Event]:
        """Mengambil riwayat event terbaru untuk keperluan audit jejak langkah."""
        with self._lock:
            filtered = [
                e
                for e in self._history
                if (event_type is None or fnmatch.fnmatch(e.event_type, event_type))
                and (namespace is None or e.namespace == namespace)
            ]
            return filtered[-limit:]

    def drain(self, namespace: str | None = None, limit: int = 64) -> list[Event]:
        """Menguras (drain) event dari buffer kanal untuk pemrosesan per frame (SAD 4.3)."""
        with self._lock:
            if namespace:
                buf = self._channel_buffers.get(namespace)
                return buf.drain(limit) if buf else []
            drained = []
            for buf in self._channel_buffers.values():
                drained.extend(buf.drain(limit))
            return drained
