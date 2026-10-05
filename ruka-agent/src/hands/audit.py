# -*- coding: utf-8 -*-
"""Shadow Hands Audit Trail (FR-HA-11).

Jejak audit tidak dapat disunting (INSERT-only) pada SQLite WAL 6 kolom:
- id: INTEGER PRIMARY KEY AUTOINCREMENT
- timestamp: REAL (epoch seconds)
- action_type: TEXT (ClickAction, TypeAction, dll)
- target: TEXT (koordinat, nama aplikasi, atau selector)
- verdict: TEXT (ALLOW, DENY, CONFIRM)
- verified: INTEGER (0 atau 1)
Retensi 7 hari dan dapat diputar ulang per langkah.
"""
from __future__ import annotations

import sqlite3
import time
from typing import Any


class AuditTrail:
    def __init__(self, db_path: str = ":memory:") -> None:
        self.db_path = db_path
        self._conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self._init_db()

    def _init_db(self) -> None:
        with self._conn:
            if self.db_path != ":memory:":
                self._conn.execute("PRAGMA journal_mode=WAL;")
            self._conn.execute(
                """
                CREATE TABLE IF NOT EXISTS shadow_audit (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp REAL NOT NULL,
                    action_type TEXT NOT NULL,
                    target TEXT NOT NULL,
                    verdict TEXT NOT NULL,
                    verified INTEGER NOT NULL DEFAULT 1
                )
                """
            )
            # Indeks timestamp untuk pembersihan retensi cepat
            self._conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_audit_time ON shadow_audit(timestamp)"
            )

    def record_action(
        self,
        action_type: str,
        target: str,
        verdict: str,
        verified: bool = True,
    ) -> int:
        """Mencatat aksi secara permanen (INSERT-only)."""
        now = time.time()
        with self._conn:
            cur = self._conn.execute(
                """
                INSERT INTO shadow_audit (timestamp, action_type, target, verdict, verified)
                VALUES (?, ?, ?, ?, ?)
                """,
                (now, action_type, target, verdict, 1 if verified else 0),
            )
            return int(cur.lastrowid or 0)

    def query_recent(self, limit: int = 50) -> list[dict[str, Any]]:
        """Mengambil rekaman audit terbaru."""
        cur = self._conn.cursor()
        cur.execute(
            """
            SELECT id, timestamp, action_type, target, verdict, verified
            FROM shadow_audit
            ORDER BY id DESC
            LIMIT ?
            """,
            (limit,),
        )
        rows = cur.fetchall()
        return [
            {
                "id": r[0],
                "timestamp": r[1],
                "action_type": r[2],
                "target": r[3],
                "verdict": r[4],
                "verified": bool(r[5]),
            }
            for r in rows
        ]

    def purge_older_than(self, retention_days: int = 7) -> int:
        """Membersihkan catatan audit yang lebih lama dari retensi."""
        cutoff = time.time() - (retention_days * 86400.0)
        with self._conn:
            cur = self._conn.execute(
                "DELETE FROM shadow_audit WHERE timestamp < ?",
                (cutoff,),
            )
            return cur.rowcount

    def close(self) -> None:
        self._conn.close()
