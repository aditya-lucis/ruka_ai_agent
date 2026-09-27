"""RUKA VI: Ruka Cloud — FastAPI Application Factory.
Strictly follows RUKA-VI Chapter XVII (baris 60-175).
"""

from __future__ import annotations

from dataclasses import dataclass
import hmac as _hmac
import json
import secrets as _secrets
import time
from typing import Any

from fastapi import Depends, FastAPI, Header, HTTPException
from pydantic import BaseModel, Field

from ruka_companion.tasks.protocol import (
    LOCAL_ONLY_CAPABILITIES,
    REMOTE_CAPABILITIES,
    TaskValidationError,
    validate_task,
)
from .db import CloudDB


@dataclass
class CloudConfig:
    node_id: str = "cloud-01"
    admin_token: str = ""
    max_payload_bytes: int = 8192


class LinkHello(BaseModel):
    device_id: str
    generation: int = 1
    fingerprint: str = ""


class LinkAuth(BaseModel):
    device_id: str
    response: str


class TaskSubmit(BaseModel):
    capability: str
    payload: dict[str, Any]
    requester: str
    device_id: str
    task_id: str | None = None
    correlation_id: str | None = None
    ttl_ms: int = Field(default=120_000, ge=1_000, le=600_000)


class SyncPush(BaseModel):
    event_id: str
    memory_system: str
    object_id: str
    op: str = Field(pattern="^(upsert|delete)$")
    origin_node: str
    vv: dict[str, int]
    payload: dict[str, Any]
    classification: str = "PRIVATE"


def create_app(config: CloudConfig, db: CloudDB | None = None) -> FastAPI:
    """App factory — lifespan mengelola DB; DI lewat app.state."""
    db = db or CloudDB(":memory:")
    started_at = time.time()
    app = FastAPI(title="Ruka Cloud", version="0.1.0")

    app.state.config = config
    app.state.db = db
    app.state.node_id = config.node_id
    app.state.pending_challenges = {}

    def require_admin(x_admin_token: str = Header(default="")) -> None:
        if not x_admin_token or x_admin_token != config.admin_token:
            raise HTTPException(status_code=401, detail="admin token invalid")

    def device_authed(device_id: str) -> dict[str, Any]:
        d = db.device(device_id)
        if d is None:
            raise HTTPException(status_code=404, detail="device unknown")
        if d["revoked"]:
            raise HTTPException(status_code=403, detail="device revoked")
        return d

    # ---------------------------------------------------------------- health
    @app.get("/health")
    def health() -> dict[str, Any]:
        ok, n = db.verify_chain()
        return {
            "status": "ok",
            "version": "0.1.0",
            "uptime_s": round(time.time() - started_at, 1),
            "audit_chain": {"valid": ok, "entries": n},
            "node": config.node_id,
        }

    # -------------------------------------------------------------- link auth
    @app.post("/v1/link/hello")
    def link_hello(body: LinkHello) -> dict[str, Any]:
        d = db.device(body.device_id)
        if d is None:
            db.audit(
                "cloud",
                "link.hello",
                body.device_id,
                {"result": "unknown_device"},
            )
            raise HTTPException(status_code=404, detail="device unknown")
        if d["revoked"]:
            db.audit(
                "cloud",
                "link.hello",
                body.device_id,
                {"result": "revoked"},
            )
            raise HTTPException(status_code=403, detail="device revoked")
        challenge = _secrets.token_hex(16)
        app.state.pending_challenges[body.device_id] = challenge
        db.audit(
            "cloud",
            "link.hello",
            body.device_id,
            {"result": "challenge_issued", "generation": body.generation},
        )
        db.emit_event(
            "ruka.device.challenge_issued",
            "cloud",
            body.device_id,
            body.device_id,
            {},
        )
        return {"challenge": challenge, "expires_in_ms": 30_000}

    @app.post("/v1/link/auth")
    def link_auth(body: LinkAuth) -> dict[str, Any]:
        challenge = app.state.pending_challenges.pop(body.device_id, None)
        if challenge is None:
            db.audit(
                "cloud", "link.auth", body.device_id, {"result": "no_challenge"}
            )
            raise HTTPException(status_code=400, detail="no pending challenge")

        entry = device_authed(body.device_id)
        expected = _hmac.new(
            entry["verify_token"].encode(), challenge.encode(), "sha256"
        ).hexdigest()
        if not _hmac.compare_digest(expected, body.response):
            db.audit(
                "cloud", "link.auth", body.device_id, {"result": "auth_failed"}
            )
            db.emit_event(
                "ruka.device.auth_failed",
                "cloud",
                body.device_id,
                body.device_id,
                {},
            )
            raise HTTPException(status_code=401, detail="auth failed")

        db.touch_device(body.device_id)
        db.audit("cloud", "link.auth", body.device_id, {"result": "auth_ok"})
        db.emit_event(
            "ruka.device.online",
            "cloud",
            body.device_id,
            body.device_id,
            {"generation": entry["generation"]},
        )
        return {"status": "AUTHENTICATED", "node": config.node_id}

    # ------------------------------------------------------------------ tasks
    @app.post("/v1/tasks", status_code=201)
    def submit_task(
        body: TaskSubmit, _: None = Depends(require_admin)
    ) -> dict[str, Any]:
        if len(str(body.payload)) > config.max_payload_bytes:
            raise HTTPException(status_code=413, detail="payload too large")

        try:
            validate_task(body.capability, body.payload, body.ttl_ms)
        except TaskValidationError as exc:
            raise HTTPException(status_code=422, detail=str(exc))

        device = device_authed(body.device_id)
        task_id = (
            body.task_id
            or f"task-{int(time.time() * 1000):013d}-{body.device_id}"
        )
        existing = db.task(task_id)
        if existing is not None:
            # IDEMPOTENT submit — bukan duplikasi eksekusi
            return {
                "task_id": task_id,
                "status": existing["status"],
                "duplicate": True,
            }

        now = int(time.time() * 1000)
        corr = body.correlation_id or _secrets.token_hex(8)
        record = {
            "task_id": task_id,
            "correlation_id": corr,
            "requester": body.requester,
            "device_id": body.device_id,
            "capability": body.capability,
            "payload": body.payload,
            "status": "QUEUED",
            "created_at_ms": now,
            "expires_at_ms": now + body.ttl_ms,
        }
        db.insert_task(record)
        db.audit(
            body.requester,
            "task.submit",
            task_id,
            {"capability": body.capability, "device_id": body.device_id},
        )
        db.emit_event(
            "ruka.task.created",
            "cloud",
            body.requester,
            corr,
            {"task_id": task_id, "capability": body.capability},
        )
        return {"task_id": task_id, "status": "QUEUED", "duplicate": False}

    @app.get("/v1/tasks/{task_id}")
    def get_task(
        task_id: str, _: None = Depends(require_admin)
    ) -> dict[str, Any]:
        t = db.task(task_id)
        if t is None:
            raise HTTPException(status_code=404, detail="task not found")
        return t

    # ------------------------------------------------------------------ sync
    @app.post("/v1/sync/push")
    def sync_push(
        body: SyncPush, _: None = Depends(require_admin)
    ) -> dict[str, Any]:
        if body.classification == "NEVER_SYNC":
            raise HTTPException(
                status_code=422,
                detail="klasifikasi NEVER_SYNC tidak boleh disinkronkan ke cloud",
            )
        db.insert_sync_event(body.model_dump())
        return {"status": "APPLIED", "event_id": body.event_id}

    @app.get("/v1/sync/pull")
    def sync_pull(
        since_ms: int = 0, limit: int = 100, _: None = Depends(require_admin)
    ) -> list[dict[str, Any]]:
        return db.pull_sync_events(since_ms, limit)

    # ------------------------------------------------------------------ audit
    @app.get("/v1/audit")
    def get_audit(
        limit: int = 50, _: None = Depends(require_admin)
    ) -> list[dict[str, Any]]:
        return db.audit_entries(limit)

    return app
