# -*- coding: utf-8 -*-
"""Unit tests for src.gateway package.
Memverifikasi Session Manager, Event Bus, Permissions (PathJail),
Protokol Komunikasi, Channel Adapters, dan Gateway Server.
"""
import json
import socket
import time
import pytest

from src.gateway.protocol import InboundMessage, OutboundMessage
from src.gateway.session import SessionManager, Session
from src.gateway.events import EventBus, Event
from src.gateway.permissions import PermissionManager, RiskLevel
from src.gateway.channels.desktop import DesktopChannelAdapter
from src.gateway.channels.cli import CliChannelAdapter
from src.gateway.server import RukaGatewayServer


class DummyBrain:
    def think_and_reply(self, text: str, attachment=None) -> str:
        return f"Marquis menerima titah: {text}"


class TestSessionManager:
    def test_create_and_get_session(self):
        sm = SessionManager()
        sess = sm.create_session(channel="desktop", user_id="young_lord")
        assert sess.channel == "desktop"
        assert sess.user_id == "young_lord"

        retrieved = sm.get_session(sess.session_id)
        assert retrieved is not None
        assert retrieved.session_id == sess.session_id

    def test_cleanup_expired(self):
        sm = SessionManager(default_ttl_seconds=0.01)
        sess = sm.create_session(channel="cli")
        time.sleep(0.02)
        expired_count = sm.cleanup_expired_sessions(max_idle_seconds=0.01)
        assert expired_count == 1
        assert sm.get_session(sess.session_id) is None


class TestEventBus:
    def test_publish_and_wildcard_subscribe(self):
        bus = EventBus()
        received = []

        sub_id = bus.subscribe("session.*", lambda evt: received.append(evt))
        bus.publish(Event(event_type="session.created", source="test", payload={"id": 1}))
        bus.publish(Event(event_type="skill.executed", source="test", payload={"skill": "edit"}))
        bus.publish(Event(event_type="session.closed", source="test", payload={"id": 1}))

        assert len(received) == 2
        assert received[0].event_type == "session.created"
        assert received[1].event_type == "session.closed"

        bus.unsubscribe(sub_id)
        bus.publish(Event(event_type="session.created", source="test", payload={"id": 2}))
        assert len(received) == 2

    def test_event_history(self):
        bus = EventBus(max_history=10)
        for i in range(5):
            bus.publish(Event(event_type=f"test.event.{i}", source="test"))
        hist = bus.history(limit=3)
        assert len(hist) == 3
        assert hist[-1].event_type == "test.event.4"


class TestPermissions:
    def test_permissions_and_jail(self, tmp_path):
        pm = PermissionManager(workspace_root=tmp_path)
        valid_file = tmp_path / "src" / "code.py"
        valid_file.parent.mkdir(parents=True, exist_ok=True)
        valid_file.write_text("print('hello')", encoding="utf-8")

        confined = pm.verify_path(valid_file)
        assert confined.exists()

        assert pm.check_permissions(["filesystem:read", "filesystem:write"]) is True
        assert pm.requires_confirmation(RiskLevel.LOW) is False
        assert pm.requires_confirmation(RiskLevel.CRITICAL) is True


class TestProtocolAndChannels:
    def test_inbound_and_outbound(self):
        legacy = {
            "type": "request",
            "channel": "ruka:chat-send",
            "correlationId": "corr_123",
            "payload": {"text": "Halo Ruka"},
            "ts": 12345.0,
        }
        inbound = InboundMessage.from_legacy_ipc(legacy, channel="desktop", session_id="sess_1")
        assert inbound.channel == "desktop"
        assert inbound.correlation_id == "corr_123"
        assert inbound.content["text"] == "Halo Ruka"

        outbound = OutboundMessage(
            type="response",
            channel="desktop",
            session_id="sess_1",
            correlation_id="corr_123",
            content={"delta": "Salam Young Lord", "done": True},
        )
        converted = outbound.to_legacy_ipc(legacy_channel="ruka:chat-send")
        assert converted["channel"] == "ruka:chat-send"
        assert converted["correlationId"] == "corr_123"
        assert converted["payload"]["delta"] == "Salam Young Lord"


class TestGatewayServer:
    def test_gateway_dispatch_and_status(self):
        server = RukaGatewayServer(brain=DummyBrain())
        # Status request
        msg_status = InboundMessage(
            type="request",
            channel="desktop",
            session_id="sess_test",
            content={},
            metadata={"ipc_channel": "ruka:runtime-status"},
        )
        resp_status = server.dispatch_inbound(msg_status)
        assert resp_status.content["state"] == "ready"
        assert resp_status.content["health_score"] >= 0.9

        # Chat request
        msg_chat = InboundMessage(
            type="request",
            channel="desktop",
            session_id="sess_test",
            content={"text": "Uji sistem"},
            metadata={"ipc_channel": "ruka:chat-send"},
        )
        resp_chat = server.dispatch_inbound(msg_chat)
        assert "Marquis menerima titah: Uji sistem" in resp_chat.content["delta"]

    def test_gateway_socket_ipc(self):
        server = RukaGatewayServer(brain=DummyBrain())
        server.start()
        time.sleep(0.05)

        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.connect((server.host, server.port))

            # 1. Handshake salah
            bad_hello = json.dumps({
                "channel": "hello",
                "correlationId": "c1",
                "payload": {"token": "wrong_token"},
            }) + "\n"
            s.sendall(bad_hello.encode("utf-8"))
            resp1 = json.loads(s.recv(4096).decode("utf-8").strip())
            assert resp1["type"] == "error"

            # 2. Handshake benar
            good_hello = json.dumps({
                "channel": "hello",
                "correlationId": "c2",
                "payload": {"token": server.token},
            }) + "\n"
            s.sendall(good_hello.encode("utf-8"))
            resp2 = json.loads(s.recv(4096).decode("utf-8").strip())
            assert resp2["type"] == "response"
            assert resp2["payload"]["ok"] is True

            # 3. Kirim chat-send
            chat_req = json.dumps({
                "channel": "ruka:chat-send",
                "correlationId": "c3",
                "payload": {"text": "Selamat malam Ruka"},
            }) + "\n"
            s.sendall(chat_req.encode("utf-8"))
            resp3 = json.loads(s.recv(4096).decode("utf-8").strip())
            assert resp3["type"] == "response"
            assert "Marquis menerima titah" in resp3["payload"]["delta"]

            s.close()
        finally:
            server.stop()
