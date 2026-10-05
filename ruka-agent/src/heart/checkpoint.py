# -*- coding: utf-8 -*-
"""Heart Checkpointer & Crash Recovery (FR-HE-02).

Menyimpan status graf per super-step di SQLite mode WAL:
- Status langkah tersimpan per task_id dan step_id
- Pemulihan pasca crash di bawah 2 menit tanpa mengulang langkah yang telah selesai
"""
from __future__ import annotations

import json
import sqlite3
import time
from typing import Any


class HeartCheckpointer:
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
                CREATE TABLE IF NOT EXISTS heart_checkpoints (
                    task_id TEXT NOT NULL,
                    step_id TEXT NOT NULL,
                    state_json TEXT NOT NULL,
                    status TEXT NOT NULL,
                    updated_at REAL NOT NULL,
                    PRIMARY KEY (task_id, step_id)
                )
                """
            )

    def save_checkpoint(
        self,
        task_id: str,
        step_id: str,
        state_data: dict[str, Any],
        status: str = "completed",
    ) -> None:
        """Menyimpan checkpoint super-step ke SQLite."""
        now = time.time()
        payload = json.dumps(state_data)
        with self._conn:
            self._conn.execute(
                """
                INSERT INTO heart_checkpoints (task_id, step_id, state_json, status, updated_at)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(task_id, step_id) DO UPDATE SET
                    state_json = excluded.state_json,
                    status = excluded.status,
                    updated_at = excluded.updated_at
                """,
                (task_id, step_id, payload, status, now),
            )

    def load_completed_steps(self, task_id: str) -> dict[str, dict[str, Any]]:
        """Mengambil seluruh langkah yang telah sukses diselesaikan untuk task tertentu."""
        cur = self._conn.cursor()
        cur.execute(
            """
            SELECT step_id, state_json
            FROM heart_checkpoints
            WHERE task_id = ? AND status = 'completed'
            ORDER BY updated_at ASC
            """,
            (task_id,),
        )
        rows = cur.fetchall()
        return {r[0]: json.loads(r[1]) for r in rows}

    def clear_task(self, task_id: str) -> None:
        with self._conn:
            self._conn.execute("DELETE FROM heart_checkpoints WHERE task_id = ?", (task_id,))

    def close(self) -> None:
        self._conn.close()
