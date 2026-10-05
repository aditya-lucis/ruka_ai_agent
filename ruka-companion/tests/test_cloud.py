"""RUKA VI: Tests for Ruka Cloud FastAPI Application & Audit Chain.
Strictly follows RUKA-VI Chapter XVII & XXV.
"""

from __future__ import annotations

import hmac
import pytest
from fastapi.testclient import TestClient

from ruka_companion.cloud.app import CloudConfig, create_app
from ruka_companion.cloud.db import CloudDB
from ruka_companion.security.envelope import sha256_hex


@pytest.fixture
def cloud_env():
    db = CloudDB(":memory:")
    # Register device local-01
    dev_secret = "dev_secret_" + "a" * 50
    verify_token = "verify_token_" + "b" * 40
    db.register_device(
        device_id="local-01",
        owner="bos",
        fingerprint=sha256_hex(dev_secret),
        verify_token=verify_token,
        generation=1,
    )
    admin_token = "adm_" + "x" * 32
    config = CloudConfig(admin_token=admin_token, node_id="cloud-01")
    app = create_app(config=config, db=db)
    client = TestClient(app)
    return {
        "db": db,
        "config": config,
        "app": app,
        "client": client,
        "verify_token": verify_token,
        "admin_token": admin_token,
    }


class TestCloudApp:
    """Uji antarmuka publik Ruka Cloud via TestClient (Part XVII)."""

    def test_health_no_auth_required(self, cloud_env):
        client = cloud_env["client"]
        resp = client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert data["audit_chain"]["valid"] is True
        assert data["node"] == "cloud-01"

    def test_device_handshake_flow(self, cloud_env):
        client = cloud_env["client"]
        verify_token = cloud_env["verify_token"]

        # 1. Hello unknown device -> 404
        r = client.post("/v1/link/hello", json={"device_id": "unknown-device"})
        assert r.status_code == 404

        # 2. Hello valid device -> issues challenge
        r = client.post("/v1/link/hello", json={"device_id": "local-01"})
        assert r.status_code == 200
        data = r.json()
        challenge = data["challenge"]
        assert challenge

        # 3. Auth with wrong HMAC -> 401
        r_fail = client.post(
            "/v1/link/auth",
            json={"device_id": "local-01", "response": "wrong_signature"},
        )
        assert r_fail.status_code == 401

        # 4. Hello again to get fresh challenge
        r2 = client.post("/v1/link/hello", json={"device_id": "local-01"})
        challenge2 = r2.json()["challenge"]

        # 5. Auth with correct HMAC -> 200 AUTHENTICATED
        expected_resp = hmac.new(
            verify_token.encode(), challenge2.encode(), "sha256"
        ).hexdigest()
        r_ok = client.post(
            "/v1/link/auth",
            json={"device_id": "local-01", "response": expected_resp},
        )
        assert r_ok.status_code == 200
        assert r_ok.json()["status"] == "AUTHENTICATED"

    def test_revoked_device_rejected(self, cloud_env):
        client = cloud_env["client"]
        db = cloud_env["db"]
        db.revoke_device("local-01")

        r = client.post("/v1/link/hello", json={"device_id": "local-01"})
        assert r.status_code == 403
        assert "revoked" in r.json()["detail"]

    def test_tasks_require_admin_token(self, cloud_env):
        client = cloud_env["client"]
        # No token -> 401
        r = client.post(
            "/v1/tasks",
            json={
                "capability": "filesystem.read",
                "payload": {},
                "requester": "telegram:BOS",
                "device_id": "local-01",
            },
        )
        assert r.status_code == 401

    def test_tasks_local_only_capability_rejected(self, cloud_env):
        client = cloud_env["client"]
        admin_token = cloud_env["admin_token"]
        r = client.post(
            "/v1/tasks",
            json={
                "capability": "camera.capture",
                "payload": {},
                "requester": "telegram:BOS",
                "device_id": "local-01",
            },
            headers={"X-Admin-Token": admin_token},
        )
        assert r.status_code == 422
        assert "local-only" in r.json()["detail"]

    def test_tasks_idempotent_submission(self, cloud_env):
        client = cloud_env["client"]
        admin_token = cloud_env["admin_token"]
        payload = {
            "task_id": "task-test-idempotent-01",
            "capability": "filesystem.read",
            "payload": {"path": "test.txt"},
            "requester": "telegram:BOS",
            "device_id": "local-01",
        }
        # First submission -> 201, duplicate == False
        r1 = client.post(
            "/v1/tasks", json=payload, headers={"X-Admin-Token": admin_token}
        )
        assert r1.status_code == 201
        assert r1.json()["duplicate"] is False

        # Second submission -> duplicate == True
        r2 = client.post(
            "/v1/tasks", json=payload, headers={"X-Admin-Token": admin_token}
        )
        assert r2.status_code == 201
        assert r2.json()["duplicate"] is True

    def test_sync_push_never_sync_rejected(self, cloud_env):
        client = cloud_env["client"]
        admin_token = cloud_env["admin_token"]
        payload = {
            "event_id": "ev-01",
            "memory_system": "vault",
            "object_id": "pass-01",
            "op": "upsert",
            "origin_node": "local-01",
            "vv": {"local-01": 1},
            "payload": {"secret": "super_secret"},
            "classification": "NEVER_SYNC",
        }
        r = client.post(
            "/v1/sync/push",
            json=payload,
            headers={"X-Admin-Token": admin_token},
        )
        assert r.status_code == 422
        assert "NEVER_SYNC" in r.json()["detail"]

    def test_audit_chain_sabotage_detection(self, cloud_env):
        db = cloud_env["db"]
        # Make an audit entry
        db.audit("bos", "action.test", "subject-01", {"data": "test"})
        valid, n = db.verify_chain()
        assert valid is True
        assert n > 0

        # Sabotage directly in the database
        with db.tx() as cur:
            cur.execute("UPDATE audit_chain SET action='sabotaged' WHERE seq=1")

        valid_after, _ = db.verify_chain()
        assert valid_after is False

    def test_audit_redaction_in_chain(self, cloud_env):
        db = cloud_env["db"]
        sample_key = f"{'AIza'}{'SyDummyKeyForGoogleAuth12345678'}"
        db.audit(
            "admin",
            "config.update",
            "keys",
            {"api_key": sample_key, "normal": "val"},
        )
        entries = db.audit_entries(limit=1)
        assert entries[0]["detail"]["api_key"] == "<redacted>"
        assert entries[0]["detail"]["normal"] == "val"

    def test_sync_push_and_pull(self, cloud_env):
        client = cloud_env["client"]
        admin_token = cloud_env["admin_token"]
        # Push valid event
        payload = {
            "event_id": "ev-sync-01",
            "memory_system": "preferences",
            "object_id": "p-01",
            "op": "upsert",
            "origin_node": "local-01",
            "vv": {"local-01": 1},
            "payload": {"theme": "dark"},
            "classification": "PERSONAL",
        }
        r_push = client.post(
            "/v1/sync/push",
            json=payload,
            headers={"X-Admin-Token": admin_token},
        )
        assert r_push.status_code == 200
        assert r_push.json()["status"] == "APPLIED"

        # Pull events
        r_pull = client.get(
            "/v1/sync/pull?since_ms=0&limit=10",
            headers={"X-Admin-Token": admin_token},
        )
        assert r_pull.status_code == 200
        events = r_pull.json()
        assert len(events) >= 1
        assert events[0]["event_id"] == "ev-sync-01"

    def test_audit_endpoint_auth_and_listing(self, cloud_env):
        client = cloud_env["client"]
        admin_token = cloud_env["admin_token"]
        db = cloud_env["db"]
        db.audit("operator", "deploy.check", "node", {"check": "pass"})

        # No token -> 401
        r_unauth = client.get("/v1/audit")
        assert r_unauth.status_code == 401

        # With token -> 200
        r_auth = client.get("/v1/audit", headers={"X-Admin-Token": admin_token})
        assert r_auth.status_code == 200
        entries = r_auth.json()
        assert len(entries) >= 1

    def test_health_reflects_audit_tampering(self, cloud_env):
        client = cloud_env["client"]
        db = cloud_env["db"]

        # Cause audit entry
        db.audit("sec", "probe", "target", {})
        assert client.get("/health").json()["audit_chain"]["valid"] is True

        # Sabotage DB directly
        with db.tx() as cur:
            cur.execute("UPDATE audit_chain SET prev_hash='bad_hash' WHERE seq=1")

        r_health = client.get("/health")
        assert r_health.status_code == 200
        assert r_health.json()["audit_chain"]["valid"] is False

    def test_expire_stale_tasks(self, cloud_env):
        db = cloud_env["db"]
        now = 1_000_000
        # Insert task created at now - 200_000
        db.submit_task(
            task_id="stale-task-01",
            capability="filesystem.read",
            payload_json="{}",
            requester="telegram:BOS",
            device_id="local-01",
            nonce="nonce-stale-01",
            now_ms=now - 200_000,
        )
        # Sweep with now_ms=now
        n_expired = db.expire_stale_tasks(now_ms=now)
        assert n_expired >= 1
        task = db.get_task("stale-task-01")
        assert task["status"] == "EXPIRED"

    def test_emit_and_query_event_log(self, cloud_env):
        db = cloud_env["db"]
        evt_id = db.emit_event(
            event_type="ruka.test.event",
            source="cloud_suite",
            actor="admin",
            correlation_id="corr-1234",
            payload={"msg": "hello", "token": "secret_token_123"},
        )
        assert evt_id.startswith("evt-")
        events = db.events(event_type="ruka.test.event", limit=5)
        assert len(events) >= 1
        assert events[0]["correlation_id"] == "corr-1234"
        assert events[0]["payload"]["token"] == "<redacted>"

    def test_admin_token_invalid_header(self, cloud_env):
        client = cloud_env["client"]
        r = client.post(
            "/v1/tasks",
            json={"capability": "filesystem.read", "payload": {}, "requester": "BOS", "device_id": "local-01"},
            headers={"X-Admin-Token": "wrong_token_here"},
        )
        assert r.status_code == 401
        assert "admin token invalid" in r.json()["detail"]

    def test_link_auth_no_pending_challenge(self, cloud_env):
        client = cloud_env["client"]
        r = client.post(
            "/v1/link/auth",
            json={"device_id": "local-01", "response": "fake_response"},
        )
        assert r.status_code == 400
        assert "no pending challenge" in r.json()["detail"]

    def test_link_auth_challenge_replay_rejected(self, cloud_env):
        client = cloud_env["client"]
        verify_token = cloud_env["verify_token"]
        r_hello = client.post("/v1/link/hello", json={"device_id": "local-01"})
        ch = r_hello.json()["challenge"]
        expected_resp = hmac.new(verify_token.encode(), ch.encode(), "sha256").hexdigest()

        # First auth succeeds
        r_auth1 = client.post("/v1/link/auth", json={"device_id": "local-01", "response": expected_resp})
        assert r_auth1.status_code == 200

        # Second auth with same challenge is rejected because nonce was popped
        r_auth2 = client.post("/v1/link/auth", json={"device_id": "local-01", "response": expected_resp})
        assert r_auth2.status_code == 400
        assert "no pending challenge" in r_auth2.json()["detail"]

    def test_task_submit_unknown_capability_rejected(self, cloud_env):
        client = cloud_env["client"]
        admin_token = cloud_env["admin_token"]
        r = client.post(
            "/v1/tasks",
            json={"capability": "destroy.world", "payload": {}, "requester": "BOS", "device_id": "local-01"},
            headers={"X-Admin-Token": admin_token},
        )
        assert r.status_code == 422
        assert "tak dikenal" in r.json()["detail"]

    def test_task_submit_payload_too_large(self, cloud_env):
        client = cloud_env["client"]
        admin_token = cloud_env["admin_token"]
        config = cloud_env["config"]
        huge_payload = {"data": "A" * (config.max_payload_bytes + 100)}
        r = client.post(
            "/v1/tasks",
            json={"capability": "filesystem.read", "payload": huge_payload, "requester": "BOS", "device_id": "local-01"},
            headers={"X-Admin-Token": admin_token},
        )
        assert r.status_code == 413
        assert "payload too large" in r.json()["detail"]

    def test_task_submit_unknown_device_rejected(self, cloud_env):
        client = cloud_env["client"]
        admin_token = cloud_env["admin_token"]
        r = client.post(
            "/v1/tasks",
            json={"capability": "filesystem.read", "payload": {}, "requester": "BOS", "device_id": "unknown-ghost-dev"},
            headers={"X-Admin-Token": admin_token},
        )
        assert r.status_code == 404
        assert "device unknown" in r.json()["detail"]

    def test_task_submit_revoked_device_rejected(self, cloud_env):
        client = cloud_env["client"]
        admin_token = cloud_env["admin_token"]
        db = cloud_env["db"]
        db.revoke_device("local-01")

        r = client.post(
            "/v1/tasks",
            json={"capability": "filesystem.read", "payload": {}, "requester": "BOS", "device_id": "local-01"},
            headers={"X-Admin-Token": admin_token},
        )
        assert r.status_code == 403
        assert "device revoked" in r.json()["detail"]

    def test_get_task_not_found_404(self, cloud_env):
        client = cloud_env["client"]
        admin_token = cloud_env["admin_token"]
        r = client.get("/v1/tasks/nonexistent-task-999", headers={"X-Admin-Token": admin_token})
        assert r.status_code == 404
        assert "task not found" in r.json()["detail"]

    def test_get_task_success(self, cloud_env):
        client = cloud_env["client"]
        admin_token = cloud_env["admin_token"]
        r_sub = client.post(
            "/v1/tasks",
            json={
                "task_id": "task-fetch-01",
                "capability": "filesystem.read",
                "payload": {"p": "file.txt"},
                "requester": "telegram:BOS",
                "device_id": "local-01",
            },
            headers={"X-Admin-Token": admin_token},
        )
        assert r_sub.status_code == 201

        r_get = client.get("/v1/tasks/task-fetch-01", headers={"X-Admin-Token": admin_token})
        assert r_get.status_code == 200
        data = r_get.json()
        assert data["task_id"] == "task-fetch-01"
        assert data["status"] == "QUEUED"
        assert data["capability"] == "filesystem.read"

    def test_sync_push_without_admin_token_401(self, cloud_env):
        client = cloud_env["client"]
        r = client.post(
            "/v1/sync/push",
            json={
                "event_id": "ev-01",
                "memory_system": "vault",
                "object_id": "p-01",
                "op": "upsert",
                "origin_node": "local-01",
                "vv": {"local-01": 1},
                "payload": {},
            },
        )
        assert r.status_code == 401

    def test_sync_pull_since_ms_filtering(self, cloud_env):
        client = cloud_env["client"]
        admin_token = cloud_env["admin_token"]
        db = cloud_env["db"]

        # Insert events directly into db with distinct timestamps
        t1 = 10_000
        t2 = 20_000
        db.insert_sync_event({
            "event_id": "ev-old",
            "memory_system": "mem",
            "object_id": "o1",
            "op": "upsert",
            "origin_node": "n1",
            "vv": "{}",
            "payload": "{}",
            "classification": "PERSONAL",
            "received_at_ms": t1,
        })
        db.insert_sync_event({
            "event_id": "ev-new",
            "memory_system": "mem",
            "object_id": "o2",
            "op": "upsert",
            "origin_node": "n1",
            "vv": "{}",
            "payload": "{}",
            "classification": "PERSONAL",
            "received_at_ms": t2,
        })

        # Pull since t1 + 1 -> only ev-new
        r_pull = client.get(f"/v1/sync/pull?since_ms={t1 + 1}", headers={"X-Admin-Token": admin_token})
        assert r_pull.status_code == 200
        events = r_pull.json()
        assert len(events) == 1
        assert events[0]["event_id"] == "ev-new"


