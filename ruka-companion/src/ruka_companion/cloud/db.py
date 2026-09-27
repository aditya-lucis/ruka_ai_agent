"""RUKA VI: Cloud Database — SQLite / Multi-Writer Schema & Hash-Linked Audit Chain.
Strictly follows RUKA-VI Chapter XVII (baris 28-205).
"""

from __future__ import annotations

from contextlib import contextmanager
import hashlib
import json
import sqlite3
import time
from typing import Any, Iterator

from ruka_companion.security.redaction import redact_dict

SCHEMA_VERSION = 1

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS devices (
    device_id       TEXT PRIMARY KEY,
    owner           TEXT NOT NULL,
    fingerprint     TEXT NOT NULL,
    verify_token    TEXT NOT NULL,
    generation      INTEGER NOT NULL DEFAULT 1,
    revoked         INTEGER NOT NULL DEFAULT 0,
    registered_at_ms INTEGER NOT NULL,
    last_seen_ms    INTEGER
);
CREATE TABLE IF NOT EXISTS tasks (
    task_id         TEXT PRIMARY KEY,
    correlation_id  TEXT NOT NULL,
    requester       TEXT NOT NULL,
    device_id       TEXT NOT NULL,
    capability      TEXT NOT NULL,
    payload_json    TEXT NOT NULL,
    status          TEXT NOT NULL,
    created_at_ms   INTEGER NOT NULL,
    expires_at_ms   INTEGER NOT NULL,
    result_json     TEXT,
    error           TEXT
);
CREATE INDEX IF NOT EXISTS idx_tasks_status   ON tasks(status);
CREATE INDEX IF NOT EXISTS idx_tasks_expires  ON tasks(expires_at_ms);
CREATE INDEX IF NOT EXISTS idx_tasks_corr     ON tasks(correlation_id);
CREATE TABLE IF NOT EXISTS sync_events (
    event_id        TEXT PRIMARY KEY,
    memory_system   TEXT NOT NULL,
    object_id       TEXT NOT NULL,
    op              TEXT NOT NULL,
    origin_node     TEXT NOT NULL,
    vv_json         TEXT NOT NULL,
    payload_json    TEXT NOT NULL,
    classification  TEXT NOT NULL,
    applied         INTEGER NOT NULL DEFAULT 0,
    received_at_ms  INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_sync_object ON sync_events(memory_system, object_id);
CREATE TABLE IF NOT EXISTS audit_chain (
    seq             INTEGER PRIMARY KEY AUTOINCREMENT,
    at_ms           INTEGER NOT NULL,
    actor           TEXT NOT NULL,
    action          TEXT NOT NULL,
    subject         TEXT NOT NULL,
    detail_json     TEXT NOT NULL,
    prev_hash       TEXT NOT NULL,
    hash            TEXT NOT NULL UNIQUE
);
CREATE TABLE IF NOT EXISTS event_log (
    event_id        TEXT PRIMARY KEY,
    at_ms           INTEGER NOT NULL,
    type            TEXT NOT NULL,
    source          TEXT NOT NULL,
    actor           TEXT NOT NULL,
    correlation_id  TEXT,
    payload_json    TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_event_type ON event_log(type);
CREATE INDEX IF NOT EXISTS idx_event_corr ON event_log(correlation_id);
"""


class CloudDB:
    """Database adapter in-proses SQLite / PostgreSQL production mirror (Part XVII)."""

    def __init__(self, db_path: str = ":memory:") -> None:
        self.db_path = db_path
        self._conn = sqlite3.connect(
            db_path,
            check_same_thread=False,
            isolation_level=None,  # autocommit mode, manual BEGIN IMMEDIATE
        )
        self._conn.row_factory = sqlite3.Row
        self._init_db()

    def _init_db(self) -> None:
        self._conn.executescript(SCHEMA_SQL)

    @contextmanager
    def tx(self) -> Iterator[sqlite3.Cursor]:
        """Disiplin transaksi BEGIN IMMEDIATE — mengunci tulis sejak awal."""
        cur = self._conn.cursor()
        cur.execute("BEGIN IMMEDIATE")
        try:
            yield cur
            cur.execute("COMMIT")
        except Exception:
            try:
                cur.execute("ROLLBACK")
            except sqlite3.OperationalError:
                pass
            raise
        finally:
            cur.close()

    # ---------------------------------------------------------------- devices
    def register_device(
        self,
        device_id: str,
        owner: str,
        fingerprint: str,
        verify_token: str,
        generation: int = 1,
    ) -> None:
        now = int(time.time() * 1000)
        with self.tx() as cur:
            cur.execute(
                "INSERT OR REPLACE INTO devices("
                " device_id, owner, fingerprint, verify_token, generation,"
                " revoked, registered_at_ms, last_seen_ms)"
                " VALUES (?, ?, ?, ?, ?, 0, ?, ?)",
                (
                    device_id,
                    owner,
                    fingerprint,
                    verify_token,
                    generation,
                    now,
                    now,
                ),
            )
        self.audit(
            owner,
            "device.register",
            device_id,
            {"generation": generation, "fingerprint": fingerprint[:12]},
        )

    def revoke_device(self, device_id: str) -> bool:
        with self.tx() as cur:
            cur.execute(
                "UPDATE devices SET revoked = 1 WHERE device_id = ?",
                (device_id,),
            )
            ok = cur.rowcount > 0
        if ok:
            self.audit("cloud", "device.revoke", device_id, {"revoked": True})
        return ok

    def device(self, device_id: str) -> dict[str, Any] | None:
        row = self._conn.execute(
            "SELECT * FROM devices WHERE device_id = ?", (device_id,)
        ).fetchone()
        if row is None:
            return None
        d = dict(row)
        d["revoked"] = bool(d["revoked"])
        return d

    def touch_device(self, device_id: str) -> None:
        with self.tx() as cur:
            cur.execute(
                "UPDATE devices SET last_seen_ms = ? WHERE device_id = ?",
                (int(time.time() * 1000), device_id),
            )

    # ----------------------------------------------------------------- tasks
    def insert_task(self, t: dict[str, Any]) -> None:
        with self.tx() as cur:
            cur.execute(
                "INSERT INTO tasks(task_id, correlation_id, requester, device_id,"
                " capability, payload_json, status, created_at_ms, expires_at_ms)"
                " VALUES(?,?,?,?,?,?,?,?,?)",
                (
                    t["task_id"],
                    t["correlation_id"],
                    t["requester"],
                    t["device_id"],
                    t["capability"],
                    json.dumps(t["payload"]),
                    t["status"],
                    t["created_at_ms"],
                    t["expires_at_ms"],
                ),
            )

    def update_task_status(
        self,
        task_id: str,
        status: str,
        result: dict | None = None,
        error: str | None = None,
    ) -> bool:
        with self.tx() as cur:
            cur.execute(
                "UPDATE tasks SET status=?, result_json=?, error=? WHERE task_id=?",
                (
                    status,
                    json.dumps(result) if result else None,
                    error,
                    task_id,
                ),
            )
            return cur.rowcount > 0

    def task(self, task_id: str) -> dict[str, Any] | None:
        row = self._conn.execute(
            "SELECT * FROM tasks WHERE task_id=?", (task_id,)
        ).fetchone()
        if row is None:
            return None
        d = dict(row)
        d["payload"] = json.loads(d.pop("payload_json"))
        d["result"] = (
            json.loads(d["result_json"]) if d.get("result_json") else None
        )
        return d

    def pending_tasks(self, device_id: str, now_ms: int) -> list[dict[str, Any]]:
        rows = self._conn.execute(
            "SELECT * FROM tasks WHERE device_id=? AND status='QUEUED' AND"
            " expires_at_ms > ? ORDER BY created_at_ms LIMIT 100",
            (device_id, now_ms),
        ).fetchall()
        out = []
        for row in rows:
            d = dict(row)
            d["payload"] = json.loads(d.pop("payload_json"))
            d["result"] = (
                json.loads(d["result_json"]) if d.get("result_json") else None
            )
            out.append(d)
        return out

    def expire_stale_tasks(self, now_ms: int) -> int:
        with self.tx() as cur:
            cur.execute(
                "UPDATE tasks SET status='EXPIRED', error='expired at cloud'"
                " WHERE status IN ('CREATED','QUEUED','DELIVERED') AND expires_at_ms <= ?",
                (now_ms,),
            )
            return cur.rowcount

    get_task = task

    def submit_task(
        self,
        task_id: str,
        capability: str,
        payload_json: str,
        requester: str,
        device_id: str,
        nonce: str = "",
        now_ms: int | None = None,
        ttl_ms: int = 120_000,
    ) -> None:
        now = now_ms if now_ms is not None else int(time.time() * 1000)
        self.insert_task(
            {
                "task_id": task_id,
                "correlation_id": nonce or task_id,
                "requester": requester,
                "device_id": device_id,
                "capability": capability,
                "payload": (
                    json.loads(payload_json)
                    if isinstance(payload_json, str)
                    else payload_json
                ),
                "status": "QUEUED",
                "created_at_ms": now,
                "expires_at_ms": now + ttl_ms,
            }
        )

    # ------------------------------------------------------------- audit chain

    def audit(
        self, actor: str, action: str, subject: str, detail: dict[str, Any]
    ) -> str:
        """Tambahkan entri ke rantai audit hash-linked (dengan redaksi)."""
        now = int(time.time() * 1000)
        redacted = redact_dict(detail)
        detail_json = json.dumps(redacted, sort_keys=True)

        with self.tx() as cur:
            last = cur.execute(
                "SELECT hash FROM audit_chain ORDER BY seq DESC LIMIT 1"
            ).fetchone()
            prev_hash = last["hash"] if last else "0" * 64

            h = hashlib.sha256(
                f"{prev_hash}|{now}|{actor}|{action}|{subject}|{detail_json}".encode()
            ).hexdigest()

            cur.execute(
                "INSERT INTO audit_chain("
                " at_ms, actor, action, subject, detail_json, prev_hash, hash)"
                " VALUES (?, ?, ?, ?, ?, ?, ?)",
                (now, actor, action, subject, detail_json, prev_hash, h),
            )
        return h

    def verify_chain(self) -> tuple[bool, int]:
        """Verifikasi integritas penuh rantai audit. Sabotase terdeteksi seketika."""
        rows = self._conn.execute(
            "SELECT * FROM audit_chain ORDER BY seq ASC"
        ).fetchall()
        if not rows:
            return True, 0

        prev_hash = "0" * 64
        for row in rows:
            if row["prev_hash"] != prev_hash:
                return False, len(rows)

            expected = hashlib.sha256(
                f"{prev_hash}|{row['at_ms']}|{row['actor']}|{row['action']}|{row['subject']}|{row['detail_json']}".encode()
            ).hexdigest()

            if expected != row["hash"]:
                return False, len(rows)

            prev_hash = row["hash"]

        return True, len(rows)

    def audit_entries(self, limit: int = 50) -> list[dict[str, Any]]:
        rows = self._conn.execute(
            "SELECT * FROM audit_chain ORDER BY seq DESC LIMIT ?", (limit,)
        ).fetchall()
        out = []
        for r in rows:
            d = dict(r)
            d["detail"] = json.loads(d.pop("detail_json"))
            out.append(d)
        return out

    # ------------------------------------------------------------- events
    def emit_event(
        self,
        event_type: str,
        source: str,
        actor: str,
        correlation_id: str | None,
        payload: dict[str, Any],
    ) -> str:
        now = int(time.time() * 1000)
        import uuid as _uuid

        eid = f"evt-{_uuid.uuid4().hex}"
        redacted = redact_dict(payload)
        with self.tx() as cur:
            cur.execute(
                "INSERT INTO event_log("
                " event_id, at_ms, type, source, actor, correlation_id, payload_json)"
                " VALUES (?, ?, ?, ?, ?, ?, ?)",
                (
                    eid,
                    now,
                    event_type,
                    source,
                    actor,
                    correlation_id,
                    json.dumps(redacted),
                ),
            )
        return eid

    def events(self, event_type: str | None = None, limit: int = 50) -> list[dict[str, Any]]:
        """Query event_log (Part XXIII page 172-173)."""
        if event_type:
            rows = self._conn.execute(
                "SELECT * FROM event_log WHERE type=? ORDER BY at_ms DESC LIMIT ?",
                (event_type, limit),
            ).fetchall()
        else:
            rows = self._conn.execute(
                "SELECT * FROM event_log ORDER BY at_ms DESC LIMIT ?",
                (limit,),
            ).fetchall()
        out = []
        for r in rows:
            d = dict(r)
            d["payload"] = json.loads(d.pop("payload_json"))
            out.append(d)
        return out


    # ------------------------------------------------------------- sync events
    def insert_sync_event(self, ev: dict[str, Any]) -> None:
        now = int(time.time() * 1000)
        with self.tx() as cur:
            cur.execute(
                "INSERT OR REPLACE INTO sync_events("
                " event_id, memory_system, object_id, op, origin_node,"
                " vv_json, payload_json, classification, applied, received_at_ms)"
                " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    ev["event_id"],
                    ev["memory_system"],
                    ev["object_id"],
                    ev["op"],
                    ev["origin_node"],
                    json.dumps(ev.get("vv", {})),
                    json.dumps(ev.get("payload", {})),
                    ev.get("classification", "PRIVATE"),
                    int(ev.get("applied", 0)),
                    int(ev.get("received_at_ms", now)),
                ),
            )

    def pull_sync_events(
        self, since_ms: int = 0, limit: int = 100
    ) -> list[dict[str, Any]]:
        rows = self._conn.execute(
            "SELECT * FROM sync_events WHERE received_at_ms > ? ORDER BY received_at_ms ASC LIMIT ?",
            (since_ms, limit),
        ).fetchall()
        out = []
        for r in rows:
            d = dict(r)
            d["vv"] = json.loads(d.pop("vv_json"))
            d["payload"] = json.loads(d.pop("payload_json"))
            out.append(d)
        return out
