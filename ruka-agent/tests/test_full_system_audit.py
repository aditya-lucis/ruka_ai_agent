# -*- coding: utf-8 -*-
"""Full System End-to-End Audit Test (Zero Dead-End Guarantee).

Memverifikasi bahwa seluruh kanal IPC dan organ terintegrasi penuh tanpa rute buntu:
1. RukaGatewayServer IPC dispatch: organ-status, avatar-pose, avatar-expression,
   avatar-viseme, presence-status, lunar-phase, memory-search, skills-list, runtime-status.
2. Launcher RukaBrainServer: delegasi mulus ke Gateway tanpa error 'Kanal tak dikenal'.
"""
from __future__ import annotations

import time
import pytest

from src.gateway.protocol import InboundMessage
import secrets
from src.gateway.server import RukaGatewayServer


class DummyAuditBrain:
    def think_and_reply(self, text: str, attachment=None) -> str:
        return f"Marquis menerima titah: {text}"


class TestFullSystemGatewayAudit:
    @pytest.fixture
    def server(self, tmp_path):
        srv = RukaGatewayServer(token=secrets.token_hex(16), brain=DummyAuditBrain(), workspace_root=tmp_path)
        yield srv
        srv.stop()

    def test_ipc_organ_status_channel(self, server):
        msg = InboundMessage(
            type="status",
            channel="desktop",
            session_id="sess_audit_1",
            content={},
            metadata={"ipc_channel": "ruka:organ-status"},
        )
        out = server.dispatch_inbound(msg)
        assert out.type == "response"
        assert "organs" in out.content
        assert "LivingPresence" in out.content["organs"]
        assert "LivingAvatar" in out.content["organs"]

    def test_ipc_avatar_pose_and_control(self, server):
        # 1. Ambil pose avatar 60 fps
        msg_pose = InboundMessage(
            type="query",
            channel="desktop",
            session_id="sess_audit_2",
            content={},
            metadata={"ipc_channel": "ruka:avatar-pose"},
        )
        out_pose = server.dispatch_inbound(msg_pose)
        assert out_pose.type == "response"
        assert "frame_index" in out_pose.content
        assert "blendshapes" in out_pose.content

        # 2. Atur ekspresi
        msg_exp = InboundMessage(
            type="command",
            channel="desktop",
            session_id="sess_audit_2",
            content={"name": "mouthSmileLeft", "weight": 0.85},
            metadata={"ipc_channel": "ruka:avatar-expression"},
        )
        out_exp = server.dispatch_inbound(msg_exp)
        assert out_exp.type == "response"
        assert out_exp.content["success"] is True

        # 3. Atur viseme
        msg_vis = InboundMessage(
            type="command",
            channel="desktop",
            session_id="sess_audit_2",
            content={"viseme_id": "O", "weight": 0.9},
            metadata={"ipc_channel": "ruka:avatar-viseme"},
        )
        out_vis = server.dispatch_inbound(msg_vis)
        assert out_vis.type == "response"
        assert out_vis.content["success"] is True

    def test_ipc_presence_status_and_lunar_phase(self, server):
        # 1. Presence status
        msg_pres = InboundMessage(
            type="query",
            channel="desktop",
            session_id="sess_audit_3",
            content={},
            metadata={"ipc_channel": "ruka:presence-status"},
        )
        out_pres = server.dispatch_inbound(msg_pres)
        assert out_pres.type == "response"
        assert "mood" in out_pres.content
        assert "chest_scale" in out_pres.content

        # 2. Lunar phase
        msg_lunar = InboundMessage(
            type="query",
            channel="desktop",
            session_id="sess_audit_3",
            content={},
            metadata={"ipc_channel": "ruka:lunar-phase"},
        )
        out_lunar = server.dispatch_inbound(msg_lunar)
        assert out_lunar.type == "response"
        assert "phase" in out_lunar.content
        assert "voice_allowed" in out_lunar.content

    def test_ipc_memory_search(self, server):
        # Simpan satu ingatan dulu
        server.memory_palace.remember("relationship", subject="Young Lord", predicate="title", object_="Aditia")

        msg_mem = InboundMessage(
            type="query",
            channel="desktop",
            session_id="sess_audit_4",
            content={"query": "Aditia", "limit": 3},
            metadata={"ipc_channel": "ruka:memory-search"},
        )
        out_mem = server.dispatch_inbound(msg_mem)
        assert out_mem.type == "response"
        assert "hits" in out_mem.content

    def test_skills_list_and_runtime_status(self, server):
        # Skills list
        msg_sk = InboundMessage(
            type="skill.list",
            channel="desktop",
            session_id="sess_audit_5",
            content={},
            metadata={"ipc_channel": "ruka:skills-list"},
        )
        out_sk = server.dispatch_inbound(msg_sk)
        assert out_sk.type == "response"
        assert "skills" in out_sk.content

        # Runtime status
        msg_rt = InboundMessage(
            type="status",
            channel="desktop",
            session_id="sess_audit_5",
            content={},
            metadata={"ipc_channel": "ruka:runtime-status"},
        )
        out_rt = server.dispatch_inbound(msg_rt)
        assert out_rt.type == "response"
        assert out_rt.content["state"] == "ready"


class TestLauncherGatewayDelegationAudit:
    def test_launcher_delegates_to_gateway(self, tmp_path):
        import launcher
        brain_srv = launcher.RukaBrainServer(workspace=tmp_path)

        # Buat request mentah yang sebelumnya ditolak sebagai 'Kanal tak dikenal'
        raw_req_organ = {
            "channel": "ruka:organ-status",
            "correlationId": "corr-test-1",
            "protocolVersion": 2,
            "payload": {},
        }

        resp, _ = brain_srv._process_request(raw_req_organ, is_auth=True)
        assert resp is not None
        assert resp["type"] == "response"
        assert "organs" in resp["payload"]

        raw_req_pose = {
            "channel": "ruka:avatar-pose",
            "correlationId": "corr-test-2",
            "protocolVersion": 2,
            "payload": {},
        }
        resp_pose, _ = brain_srv._process_request(raw_req_pose, is_auth=True)
        assert resp_pose is not None
        assert resp_pose["type"] == "response"
        assert "frame_index" in resp_pose["payload"]

        raw_req_skills = {
            "channel": "ruka:skills-list",
            "correlationId": "corr-test-3",
            "protocolVersion": 2,
            "payload": {},
        }
        resp_skills, _ = brain_srv._process_request(raw_req_skills, is_auth=True)
        assert resp_skills is not None
        assert resp_skills["type"] == "response"
        assert "skills" in resp_skills["payload"]
