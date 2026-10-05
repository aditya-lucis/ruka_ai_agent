# -*- coding: utf-8 -*-
"""Notification Dosing & Curfew Engine (FR-OS-05).

Menerapkan etika penyiaran notifikasi pendamping:
- Dosis normal: Maksimal 1 notifikasi per 10 menit (600 detik)
- Jam malam (curfew) 22:00 s.d. 07:00: Hanya notifikasi URGENT yang diizinkan tembus
- Notifikasi WHISPER (bisikan): Ditampung dan digabungkan menjadi amplop rangkuman pukul 18:00
"""
from __future__ import annotations

from datetime import datetime
import time
from typing import Optional
from src.os_companion.models import NotificationItem, NotificationPriority


class NotificationDoser:
    NORMAL_COOLDOWN_S = 600.0  # 10 menit

    def __init__(self) -> None:
        self.last_normal_delivery: float = 0.0
        self.whisper_digest_queue: list[NotificationItem] = []

    def is_curfew_hours(self, dt: Optional[datetime] = None) -> bool:
        """Jam malam aktif antara pukul 22:00 malam hingga 07:00 pagi."""
        now = dt or datetime.now()
        hour = now.hour
        return hour >= 22 or hour < 7

    def can_deliver(self, item: NotificationItem, current_time: Optional[float] = None) -> tuple[bool, str]:
        """Mengevaluasi apakah notifikasi boleh dipancarkan seketika ke layar.

        Returns:
            (boleh_dikirim: bool, alasan: str)
        """
        now_ts = current_time if current_time is not None else time.time()
        now_dt = datetime.fromtimestamp(now_ts)

        # 1. Notifikasi Whisper selalu dialihkan ke antrean digest 18:00
        if item.priority == NotificationPriority.WHISPER:
            self.whisper_digest_queue.append(item)
            return False, "whisper_queued_for_digest"

        # 2. Periksa jam malam (Curfew 22:00 - 07:00)
        in_curfew = self.is_curfew_hours(now_dt)
        if in_curfew:
            if item.priority == NotificationPriority.URGENT:
                self.last_normal_delivery = now_ts
                return True, "urgent_bypasses_curfew"
            else:
                return False, "blocked_by_night_curfew"

        # 3. Notifikasi Urgent selalu lolos di luar jam malam
        if item.priority == NotificationPriority.URGENT:
            self.last_normal_delivery = now_ts
            return True, "urgent_immediate"

        # 4. Notifikasi Normal: Dosis maksimal 1 per 10 menit
        time_since_last = now_ts - self.last_normal_delivery
        if time_since_last < self.NORMAL_COOLDOWN_S:
            return False, f"cooldown_active_{int(self.NORMAL_COOLDOWN_S - time_since_last)}s_remaining"

        self.last_normal_delivery = now_ts
        return True, "normal_delivered"

    def flush_digest(self) -> list[NotificationItem]:
        """Mengambil seluruh tumpukan notifikasi whisper untuk amplop rangkuman."""
        items = list(self.whisper_digest_queue)
        self.whisper_digest_queue.clear()
        return items
