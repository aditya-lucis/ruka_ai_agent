# -*- coding: utf-8 -*-
"""NOCTIS Sleep Consolidator & Decay Scheduler (FR-ME-06 s/d FR-ME-11, SAD 4.1).

Konsolidasi memori malam hari dalam 3 tahap beranggaran:
- Tahap 1 (Abstraksi): Mengabstraksi catatan harian (Daily) menjadi wawasan tingkat tinggi (Dream)
- Tahap 2 (Resolusi Konflik): Menyelesaikan fakta yang kontradiktif (update/soft-delete fakta usang)
- Tahap 3 (Peluruhan Waktu / Decay Scheduler): Menerapkan fungsi peluruhan eksponensial pada bobot memori lama
- Menerbitkan event 'palace.consolidate' pada namespace OrganNamespace.PALACE
"""
from __future__ import annotations

import logging
import math
import time
from dataclasses import dataclass
from typing import Any

from src.gateway.events import Event, EventBus, OrganNamespace
from src.memory.palace.models import MemoryWing
from src.memory.palace.palace import MemoryPalace

log = logging.getLogger("ruka.memory.palace.consolidator")


@dataclass(frozen=True)
class ConsolidationReport:
    timestamp: float
    daily_summaries_processed: int
    dreams_generated: int
    conflicts_resolved: int
    decayed_memories_count: int
    duration_ms: float


class SleepConsolidator:
    def __init__(
        self,
        palace: MemoryPalace,
        event_bus: EventBus | None = None,
        half_life_days: float = 30.0,
    ) -> None:
        self.palace = palace
        self.event_bus = event_bus
        self.half_life_days = half_life_days

    def run_consolidation(self, current_time: float | None = None) -> ConsolidationReport:
        """Menjalankan siklus konsolidasi tidur 3 tahap."""
        start_t = time.perf_counter()
        now = current_time if current_time is not None else time.time()

        # 1. Tahap 1: Abstraksi Catatan Harian -> Dream Wing
        processed_daily, dreams_gen = self._stage_1_abstract_daily(now)

        # 2. Tahap 2: Resolusi Konflik Fakta
        conflicts = self._stage_2_resolve_conflicts()

        # 3. Tahap 3: Peluruhan Bobot Waktu (Decay Scheduler)
        decayed = self._stage_3_decay_scheduler(now)

        duration_ms = (time.perf_counter() - start_t) * 1000.0
        report = ConsolidationReport(
            timestamp=now,
            daily_summaries_processed=processed_daily,
            dreams_generated=dreams_gen,
            conflicts_resolved=conflicts,
            decayed_memories_count=decayed,
            duration_ms=duration_ms,
        )

        # Terbitkan event ke EventBus V3
        if self.event_bus:
            self.event_bus.publish(
                Event(
                    namespace=OrganNamespace.PALACE.value,
                    event_type="palace.consolidate",
                    source="sleep_consolidator",
                    payload={
                        "daily_processed": processed_daily,
                        "dreams_generated": dreams_gen,
                        "conflicts_resolved": conflicts,
                        "decayed_count": decayed,
                        "duration_ms": duration_ms,
                    },
                )
            )

        log.info(
            "Konsolidasi tidur selesai dalam %.2f ms (Daily=%d, Dream=%d, Konflik=%d, Decay=%d)",
            duration_ms,
            processed_daily,
            dreams_gen,
            conflicts,
            decayed,
        )
        return report

    def _stage_1_abstract_daily(self, now: float) -> tuple[int, int]:
        """Mengabstraksi daily digest menjadi entri reflektif dream."""
        with self.palace._lock, self.palace._get_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                SELECT id, summary, highlights_json
                FROM palace_daily
                WHERE is_deleted = 0
                ORDER BY timestamp DESC
                LIMIT 5
                """
            )
            rows = cur.fetchall()

        if not rows:
            return 0, 0

        # Buat mimpi abstraksi
        summaries = [r["summary"] for r in rows if r["summary"]]
        combined_text = "; ".join(summaries[:3])
        dream_id = self.palace.remember(
            MemoryWing.DREAM,
            {
                "topic": "Sintesis Harian Noctis",
                "reflection": f"Refleksi atas interaksi terkini: {combined_text}",
            },
            abstraction_level=2,
        )

        return len(rows), (1 if dream_id else 0)

    def _stage_2_resolve_conflicts(self) -> int:
        """Mendeteksi konflik atau entri yang perlu diselesaikan dalam sayap preferensi/relasi."""
        # Pada palace_preference, key bersifat UNIQUE. Bila ada update nilai baru,
        # signal_count bertambah atau nilai diupdate langsung oleh remember().
        # Kita memeriksa relasi duplikat dengan confidence rendah.
        resolved = 0
        with self.palace._lock, self.palace._get_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                SELECT subject, predicate, object, count(*) as c
                FROM palace_relationship
                WHERE is_deleted = 0
                GROUP BY subject, predicate, object
                HAVING c > 1
                """
            )
            duplicate_triples = cur.fetchall()

            for trip in duplicate_triples:
                cur.execute(
                    """
                    SELECT id FROM palace_relationship
                    WHERE subject = ? AND predicate = ? AND object = ? AND is_deleted = 0
                    ORDER BY created_at DESC
                    """,
                    (trip["subject"], trip["predicate"], trip["object"]),
                )
                ids = [r[0] for r in cur.fetchall()]
                for old_id in ids[1:]:
                    self.palace.forget(old_id, reason="Resolusi duplikat relasi pada konsolidasi tidur")
                    resolved += 1

        return resolved

    def _stage_3_decay_scheduler(self, now: float) -> int:
        """Meluruhkan confidence relasi lama menggunakan peluruhan eksponensial."""
        half_life_s = self.half_life_days * 86400.0
        decay_lambda = math.log(2.0) / half_life_s

        decayed_count = 0
        with self.palace._lock, self.palace._get_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                SELECT id, confidence, created_at
                FROM palace_relationship
                WHERE is_deleted = 0
                """
            )
            rows = cur.fetchall()

            for r in rows:
                age_s = max(0.0, now - r["created_at"])
                # Formula decay: C(t) = C0 * exp(-lambda * t)
                new_conf = r["confidence"] * math.exp(-decay_lambda * age_s)
                # Update jika ada perubahan signifikan
                if abs(new_conf - r["confidence"]) > 0.05:
                    conn.execute(
                        "UPDATE palace_relationship SET confidence = ? WHERE id = ?",
                        (round(new_conf, 4), r["id"]),
                    )
                    decayed_count += 1

        return decayed_count
