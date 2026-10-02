# -*- coding: utf-8 -*-
"""RUKA Gateway — Session Manager.

Mengelola unit isolasi interaksi antar-channel (Desktop, CLI, dsb.),
konteks percakapan sementara, dan daur hidup sesi Young Lord.
"""
from __future__ import annotations

import threading
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass
class Session:
    """Unit isolasi interaksi Young Lord pada sebuah saluran komunikasi."""
    session_id: str
    channel: str                                         # "desktop" | "cli" | "telegram" | ...
    user_id: str = "young_lord"                         # Loyalitas mutlak kepada Young Lord
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    last_active: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    context: dict[str, Any] = field(default_factory=dict)
    memory_scope: str = "global"                         # "global" | "project:<path>"
    active_skills: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def touch(self) -> None:
        """Memperbarui tanda waktu aktivitas terakhir."""
        self.last_active = datetime.now(timezone.utc)

    @property
    def idle_seconds(self) -> float:
        """Menghitung waktu hening (inactivity) dalam detik."""
        return (datetime.now(timezone.utc) - self.last_active).total_seconds()


class SessionManager:
    """Pengelola siklus hidup sesi interaktif Ruka secara thread-safe."""

    def __init__(self, default_ttl_seconds: float = 86400.0) -> None:
        self.default_ttl_seconds = default_ttl_seconds
        self._sessions: dict[str, Session] = {}
        self._lock = threading.RLock()

    def create_session(
        self,
        channel: str,
        user_id: str = "young_lord",
        memory_scope: str = "global",
        session_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> Session:
        """Membuat sesi baru yang bersih untuk kanal tertentu."""
        with self._lock:
            sid = session_id or f"sess_{uuid.uuid4().hex[:12]}"
            sess = Session(
                session_id=sid,
                channel=channel,
                user_id=user_id,
                memory_scope=memory_scope,
                metadata=metadata or {},
            )
            self._sessions[sid] = sess
            return sess

    def get_session(self, session_id: str, auto_touch: bool = True) -> Session | None:
        """Mengambil sesi yang tersimpan berdasarkan session_id."""
        with self._lock:
            sess = self._sessions.get(session_id)
            if sess is not None and auto_touch:
                sess.touch()
            return sess

    def touch_session(self, session_id: str) -> bool:
        """Menyentuh sesi untuk menyegarkan batas waktu idle."""
        with self._lock:
            sess = self._sessions.get(session_id)
            if sess:
                sess.touch()
                return True
            return False

    def close_session(self, session_id: str) -> bool:
        """Menutup dan menghapus sesi dari memori kerja."""
        with self._lock:
            if session_id in self._sessions:
                del self._sessions[session_id]
                return True
            return False

    def list_active_sessions(self) -> list[Session]:
        """Mengembalikan daftar seluruh sesi yang sedang aktif."""
        with self._lock:
            return list(self._sessions.values())

    def cleanup_expired_sessions(self, max_idle_seconds: float | None = None) -> int:
        """Membersihkan sesi yang telah melewati batas inaktivitas."""
        ttl = max_idle_seconds if max_idle_seconds is not None else self.default_ttl_seconds
        with self._lock:
            now = datetime.now(timezone.utc)
            expired_ids = [
                sid
                for sid, sess in self._sessions.items()
                if (now - sess.last_active).total_seconds() > ttl
            ]
            for sid in expired_ids:
                del self._sessions[sid]
            return len(expired_ids)
