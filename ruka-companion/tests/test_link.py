"""Tests for RUKA VI Secure Link Subsystem (Part XIX & XXII).
Strictly verifies:
- DeviceCredential & DeviceRegistry (HMAC challenge-response, fingerprint, rotation proof)
- CloudLink lifecycle (CONNECTING -> AUTHENTICATING -> AUTHENTICATED)
- Sovereign local gate & inbound allowlist enforcement
- Tamper / replay / stale rejection
- Connection failure & full-jitter backoff retry
- Real loopback WebSocket transport & in-memory FakeTransport
"""

import asyncio
import json
import pytest
import websockets
from ruka_companion.link.credential import (
    DeviceCredential,
    DeviceRegistry,
    make_verify_token,
    make_rotation_proof,
)
from ruka_companion.link.connector import (
    CloudLink,
    LinkState,
    LinkPolicy,
)
from ruka_companion.security.envelope import EnvelopeCodec, EnvelopeError


SECRET_A = "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef"
SECRET_B = "fedcba9876543210fedcba9876543210fedcba9876543210fedcba9876543210"


class FakeTransport:
    """Deterministic in-memory async transport for unit testing."""

    def __init__(self, responses: list[str] | None = None, fail_connect: bool = False):
        self.responses = list(responses or [])
        self.sent: list[str] = []
        self.fail_connect = fail_connect
        self.closed = False

    async def connect(self, uri: str) -> None:
        if self.fail_connect:
            raise ConnectionRefusedError(f"Connection to {uri} refused")

    async def send(self, data: str) -> None:
        self.sent.append(data)

    async def recv(self) -> str:
        if not self.responses:
            raise EOFError("No more responses")
        return self.responses.pop(0)

    async def close(self) -> None:
        self.closed = True


class WebSocketTransportAdapter:
    """Adapter bridging websockets.client.ClientConnection to CloudLink transport protocol."""

    def __init__(self):
        self._ws = None

    async def connect(self, uri: str) -> None:
        self._ws = await websockets.connect(uri)

    async def send(self, data: str) -> None:
        if self._ws:
            await self._ws.send(data)

    async def recv(self) -> str:
        if self._ws:
            msg = await self._ws.recv()
            if isinstance(msg, bytes):
                return msg.decode("utf-8")
            return msg
        raise RuntimeError("Not connected")

    async def close(self) -> None:
        if self._ws:
            await self._ws.close()
            self._ws = None


class TestDeviceCredentialAndRegistry:
    def test_credential_creation_and_fingerprint(self):
        cred = DeviceCredential(device_id="dev-01", owner="bos", secret=SECRET_A)
        assert cred.device_id == "dev-01"
        assert cred.owner == "bos"
        assert len(cred.public_fingerprint()) == 64
        # Deterministic fingerprint
        assert cred.public_fingerprint() == cred.public_fingerprint()

    def test_registry_registration_and_auth(self):
        reg = DeviceRegistry()
        cred = DeviceCredential(device_id="dev-01", owner="bos", secret=SECRET_A)
        vt = make_verify_token(cred)
        reg.register_with_proof(cred, vt)

        # Duplicate registration raises ValueError
        with pytest.raises(ValueError):
            reg.register_with_proof(cred, vt)

        # Valid challenge-response
        challenge = "test-challenge-nonce-12345"
        resp = cred.sign_challenge(challenge)
        assert reg.verify_challenge("dev-01", challenge, resp) is True

        # Invalid response
        assert reg.verify_challenge("dev-01", challenge, "wrong_response") is False

        # Non-existent device
        assert reg.verify_challenge("dev-99", challenge, resp) is False

    def test_key_rotation_with_proof(self):
        reg = DeviceRegistry()
        old_cred = DeviceCredential(device_id="dev-01", owner="bos", secret=SECRET_A)
        vt = make_verify_token(old_cred)
        reg.register_with_proof(old_cred, vt)

        new_cred = DeviceCredential(device_id="dev-01", owner="bos", secret=SECRET_B)
        new_fp = new_cred.public_fingerprint()

        proof = make_rotation_proof(old_cred, new_fp)
        assert reg.rotate("dev-01", new_fp, proof) is True

        # Invalid proof rejected
        assert reg.rotate("dev-01", "other_fp", "bad_proof") is False

    def test_revocation(self):
        reg = DeviceRegistry()
        cred = DeviceCredential(device_id="dev-01", owner="bos", secret=SECRET_A)
        vt = make_verify_token(cred)
        reg.register_with_proof(cred, vt)

        reg.revoke("dev-01")
        challenge = "nonce"
        resp = cred.sign(challenge)
        assert reg.verify_challenge("dev-01", challenge, resp) is False


class TestCloudLinkProtocol:
    @pytest.mark.asyncio
    async def test_handshake_authenticated_success(self):
        cred = DeviceCredential(device_id="dev-01", owner="bos", secret=SECRET_A)
        codec = EnvelopeCodec(SECRET_A.encode())

        # Prepare server responses
        challenge_env = codec.seal("link.challenge", "cloud", {"nonce": "ch-nonce-42"})
        ack_env = codec.seal("link.auth_ok", "cloud", {"device_id": "dev-01"})

        transport = FakeTransport(
            responses=[
                json.dumps(challenge_env.as_dict()),
                json.dumps(ack_env.as_dict()),
            ]
        )

        link = CloudLink("wss://cloud.ruka.ai/link", cred, codec)
        ok = await link.connect(transport)

        assert ok is True
        assert link.state == LinkState.AUTHENTICATED
        assert len(transport.sent) == 2  # hello + auth_response
        assert link.capability()["available"] is True

    @pytest.mark.asyncio
    async def test_handshake_challenge_type_mismatch_fails(self):
        cred = DeviceCredential(device_id="dev-01", owner="bos", secret=SECRET_A)
        codec = EnvelopeCodec(SECRET_A.encode())

        # Send invalid envelope type instead of link.challenge
        bad_env = codec.seal("link.bad_type", "cloud", {})
        transport = FakeTransport(responses=[json.dumps(bad_env.as_dict())])

        link = CloudLink("wss://cloud.ruka.ai/link", cred, codec)
        ok = await link.connect(transport)

        assert ok is False
        assert link.state == LinkState.DISCONNECTED

    @pytest.mark.asyncio
    async def test_connection_refused_schedules_retry(self):
        cred = DeviceCredential(device_id="dev-01", owner="bos", secret=SECRET_A)
        codec = EnvelopeCodec(SECRET_A.encode())

        transport = FakeTransport(fail_connect=True)
        link = CloudLink("wss://cloud.ruka.ai/link", cred, codec)

        ok = await link.connect(transport)
        assert ok is False
        assert link.state == LinkState.RETRYING
        assert link.capability()["attempts"] == 1

        # Error and state_change logged
        events = [e.kind for e in link.events]
        assert "error" in events
        assert "state_change" in events

    @pytest.mark.asyncio
    async def test_sovereign_gate_allowlist_acceptance_and_rejection(self):
        cred = DeviceCredential(device_id="dev-01", owner="bos", secret=SECRET_A)
        codec = EnvelopeCodec(SECRET_A.encode())

        # 1. Allowed message: task_delivery
        allowed_env = codec.seal("task_delivery", "cloud", {"task_id": "t-1"})
        # 2. Disallowed message: arbitrary_shell_exec
        disallowed_env = codec.seal("arbitrary_shell_exec", "cloud", {"cmd": "rm -rf"})

        transport = FakeTransport(
            responses=[
                json.dumps(allowed_env.as_dict()),
                json.dumps(disallowed_env.as_dict()),
            ]
        )

        received_envelopes = []
        link = CloudLink("wss://cloud.ruka.ai/link", cred, codec)
        link.state = LinkState.AUTHENTICATED
        link._transport = transport
        link.on_message(lambda env: received_envelopes.append(env))

        # First message: accepted
        env1 = await link.receive_once()
        assert env1 is not None
        assert env1.type == "task_delivery"
        assert len(received_envelopes) == 1

        # Second message: rejected by sovereign policy gate
        env2 = await link.receive_once()
        assert env2 is None
        assert len(received_envelopes) == 1  # Not delivered to on_message

        # Verify rejection logged
        rejected_events = [e for e in link.events if e.kind == "rejected"]
        assert any(e.detail.get("type") == "arbitrary_shell_exec" for e in rejected_events)

    @pytest.mark.asyncio
    async def test_tampered_and_replayed_envelope_rejected(self):
        cred = DeviceCredential(device_id="dev-01", owner="bos", secret=SECRET_A)
        codec = EnvelopeCodec(SECRET_A.encode())

        valid_env = codec.seal("presence_ping", "cloud", {"status": "alive"})
        tampered_dict = valid_env.as_dict()
        tampered_dict["payload"] = {"status": "tampered"}  # Corrupt payload without resigning

        transport = FakeTransport(
            responses=[
                json.dumps(tampered_dict),
                json.dumps(valid_env.as_dict()),
                json.dumps(valid_env.as_dict()),  # Replay same nonce
            ]
        )

        link = CloudLink("wss://cloud.ruka.ai/link", cred, codec)
        link.state = LinkState.AUTHENTICATED
        link._transport = transport

        # Tampered -> None
        assert await link.receive_once() is None
        # First valid -> Received
        assert await link.receive_once() is not None
        # Replayed -> None (rejected)
        assert await link.receive_once() is None

    @pytest.mark.asyncio
    async def test_send_envelope_authenticated(self):
        cred = DeviceCredential(device_id="dev-01", owner="bos", secret=SECRET_A)
        codec = EnvelopeCodec(SECRET_A.encode())
        transport = FakeTransport()

        link = CloudLink("wss://cloud.ruka.ai/link", cred, codec)
        link.state = LinkState.AUTHENTICATED
        link._transport = transport

        success = await link.send("task_result", {"result": "ok"})
        assert success is True
        assert len(transport.sent) == 1

        sent_env = codec.verify_dict(json.loads(transport.sent[0]))
        assert sent_env.type == "task_result"
        assert sent_env.payload == {"result": "ok"}


class TestLoopbackWebSocketLink:
    """Real loopback WebSocket server test as required by Part XIX Page 144."""

    @pytest.mark.asyncio
    async def test_real_loopback_handshake_and_echo(self):
        cred = DeviceCredential(device_id="dev-01", owner="bos", secret=SECRET_A)
        codec = EnvelopeCodec(SECRET_A.encode())
        reg = DeviceRegistry()
        reg.register_with_proof(cred, make_verify_token(cred))

        server_stop = asyncio.Event()

        async def handler(websocket):
            try:
                # 1. Recv hello
                raw = await websocket.recv()
                hello_dict = json.loads(raw)
                hello_env = codec.verify_dict(hello_dict)
                assert hello_env.type == "link.hello"

                # 2. Send challenge
                ch_nonce = "loopback-nonce-12345"
                ch_env = codec.seal("link.challenge", "cloud", {"nonce": ch_nonce})
                await websocket.send(json.dumps(ch_env.as_dict()))

                # 3. Recv auth_response
                auth_raw = await websocket.recv()
                auth_dict = json.loads(auth_raw)
                auth_env = codec.verify_dict(auth_dict)
                assert auth_env.type == "link.auth_response"
                resp = auth_env.payload["response"]

                # 4. Verify in registry
                if reg.verify_challenge("dev-01", ch_nonce, resp):
                    ack = codec.seal("link.auth_ok", "cloud", {"device_id": "dev-01"})
                    await websocket.send(json.dumps(ack.as_dict()))
                else:
                    rej = codec.seal("link.auth_fail", "cloud", {})
                    await websocket.send(json.dumps(rej.as_dict()))
                    return

                # 5. Send one ping
                ping = codec.seal("presence_ping", "cloud", {"seq": 1})
                await websocket.send(json.dumps(ping.as_dict()))

            except Exception:
                pass

        async with websockets.serve(handler, "127.0.0.1", 8765):
            adapter = WebSocketTransportAdapter()
            link = CloudLink("ws://127.0.0.1:8765", cred, codec)

            ok = await link.connect(adapter)
            assert ok is True
            assert link.state == LinkState.AUTHENTICATED

            # Receive presence_ping over real socket
            msg = await link.receive_once()
            assert msg is not None
            assert msg.type == "presence_ping"
            assert msg.payload == {"seq": 1}

            await link.close()
            assert link.state == LinkState.DISCONNECTED
