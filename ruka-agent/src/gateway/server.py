# -*- coding: utf-8 -*-
"""RUKA Gateway — Central Control Plane Server.

Mengkoordinasikan sesi, event bus, izin keamanan (PathJail), saluran klien,
serta memanggil Cognitive Core dengan fondasi matematika.
"""
from __future__ import annotations

import json
import logging
import os
import secrets
import socket
import sys
import threading
import time
import uuid
from pathlib import Path

from typing import Any, Callable

from src.gateway.protocol import InboundMessage, OutboundMessage
from src.gateway.session import SessionManager, Session
from src.gateway.events import EventBus, Event
from src.gateway.permissions import PermissionManager
from src.gateway.channels.desktop import DesktopChannelAdapter
from src.gateway.channels.cli import CliChannelAdapter
from src.gateway.skills.registry import SkillRegistry
from src.gateway.skills.runtime import SkillsRuntime
from src.gateway.confirmations import (
    ConfirmationError,
    ConfirmationManager,
    describe_action,
    render_ticket_card,
)
from src.gateway.skills.coding_bridge import register_builtin_coding_skills
from src.gateway.skills.loader import get_skills_dir
from src.math_foundations.control import BudgetController, loop_health
from src.memory.palace import MemoryPalace
from src.gateway.supervisor import OrganSupervisor

log = logging.getLogger("ruka.gateway.server")


class RukaGatewayServer:
    """Server Gateway Lokal Ruka (Marquis of Trendamis Control Plane)."""

    def __init__(
        self,
        host: str = "127.0.0.1",
        port: int = 0,
        token: str | None = None,
        workspace_root: str | Path | None = None,
        brain: Any = None,
    ) -> None:
        self.host = host
        self.token = token or secrets.token_hex(16)
        self.start_time = time.time()
        self.running = False

        # Komponen subsistem
        self.session_mgr = SessionManager()
        self.event_bus = EventBus()
        self.permission_mgr = PermissionManager(workspace_root)
        self.confirmations = ConfirmationManager(event_bus=self.event_bus)
        self.budget_ctrl = BudgetController()
        self.brain = brain

        # Inisialisasi Istana Memori (Memory Palace)
        palace_db = Path(os.environ.get("LOCALAPPDATA", str(Path.home()))) / "ruka" / "palace.db"
        self.memory_palace = MemoryPalace(db_path=palace_db, event_bus=self.event_bus)

        # Inisialisasi Organ Supervisor & Watchdog (0.5 Hz heartbeat)
        beat_state_file = Path(os.environ.get("LOCALAPPDATA", str(Path.home()))) / "ruka" / "supervisor_beat.txt"
        self.supervisor = OrganSupervisor(event_bus=self.event_bus, state_file=beat_state_file)
        self.supervisor.register_organ("MemoryPalace", "memory", check_fn=lambda: self.memory_palace is not None)

        # Inisialisasi Organ Noctis (Senses, Hands, Heart, Converse, Presence, OS Companion, Avatar)
        from src.senses import BloodHearing, EternalVoice, CrimsonEyes
        from src.hands import ShadowHands
        from src.heart import CrimsonHeart
        from src.converse import ConversationLoop
        from src.presence.engine import LivingPresenceEngine
        from src.os_companion.ghost_window import GhostWindowManager
        from src.os_companion.docking import MagneticDockManager
        from src.os_companion.voice_hud import VoiceHUD
        from src.avatar.engine import LivingAvatarEngine

        self.hearing = BloodHearing(event_bus=self.event_bus)
        self.voice = EternalVoice(event_bus=self.event_bus)
        self.eyes = CrimsonEyes(event_bus=self.event_bus)
        self.hands = ShadowHands(event_bus=self.event_bus)
        self.heart = CrimsonHeart(event_bus=self.event_bus, memory_palace=self.memory_palace)
        self.converse = ConversationLoop(event_bus=self.event_bus, memory_palace=self.memory_palace)
        self.presence = LivingPresenceEngine(event_bus=self.event_bus)
        self.avatar = LivingAvatarEngine()
        self.ghost_window = GhostWindowManager()
        self.dock_mgr = MagneticDockManager()
        self.voice_hud = VoiceHUD()

        self.supervisor.register_organ("BloodHearing", "ear", check_fn=lambda: self.hearing is not None)
        self.supervisor.register_organ("EternalVoice", "voice", check_fn=lambda: self.voice is not None)
        self.supervisor.register_organ("CrimsonEyes", "eyes", check_fn=lambda: self.eyes is not None)
        self.supervisor.register_organ("ShadowHands", "hands", check_fn=lambda: self.hands is not None)
        self.supervisor.register_organ("CrimsonHeart", "heart", check_fn=lambda: self.heart is not None)
        self.supervisor.register_organ("MultimodalConverse", "converse", check_fn=lambda: self.converse is not None)
        self.supervisor.register_organ("LivingPresence", "presence", check_fn=lambda: self.presence is not None)
        self.supervisor.register_organ("LivingAvatar", "presence", check_fn=lambda: self.avatar is not None)

        # Subsistem Skills
        self.skill_registry = SkillRegistry()
        self.skills_runtime = SkillsRuntime(
            registry=self.skill_registry,
            permission_manager=self.permission_mgr,
            event_bus=self.event_bus,
        )
        try:
            skills_dir = get_skills_dir()
            register_builtin_coding_skills(
                self.skill_registry,
                skills_dir=skills_dir,
                workspace_root=workspace_root,
                jail=self.permission_mgr.jail,
            )
        except Exception as e_reg:
            log.warning("Peringatan saat mendaftarkan coding skills: %s", e_reg)

        if self.brain is not None:
            self.set_brain(self.brain)

        # Saluran Komunikasi
        self.desktop_adapter = DesktopChannelAdapter(token=self.token)
        self.cli_adapter = CliChannelAdapter()


        # Hubungkan handler inbound ke gateway
        self.desktop_adapter.set_message_handler(self.dispatch_inbound)
        self.cli_adapter.set_message_handler(self.dispatch_inbound)

        # Socket loopback
        self.server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_sock.bind((self.host, port))
        self.port = self.server_sock.getsockname()[1]
        self._clients: list[socket.socket] = []
        self._lock = threading.Lock()

    def set_brain(self, brain: Any) -> None:
        """Menetapkan instans Cognitive Core Brain."""
        self.brain = brain
        if self.brain is not None:
            self.brain.skill_registry = self.skill_registry
            self.brain.skills_runtime = self.skills_runtime
            self.brain.confirmations = self.confirmations
            self.brain.memory_palace = self.memory_palace
            self.brain.event_bus = self.event_bus
            self.brain.supervisor = self.supervisor
            self.brain.hearing = self.hearing
            self.brain.voice = self.voice
            self.brain.eyes = self.eyes
            self.brain.hands = self.hands
            self.brain.heart = self.heart
            self.brain.converse = self.converse
            self.brain.presence = self.presence
            self.brain.avatar = self.avatar
            self.supervisor.register_organ("Brain", "heart", check_fn=lambda: self.brain is not None)

    def _handle_skill_execute(self, msg: InboundMessage, session_id: str) -> OutboundMessage:
        """Run a skill. Gated skills require a server-issued, single-use confirmation ticket.

        A client-supplied ``confirm_granted`` flag is never trusted.
        """

        def reply(ok: bool, content: dict[str, Any]) -> OutboundMessage:
            return OutboundMessage(
                type="response" if ok else "error",
                channel=msg.channel,
                session_id=session_id,
                correlation_id=msg.correlation_id,
                content=content,
            )

        if msg.content.get("confirm_granted"):
            log.warning("confirm_granted dari klien diabaikan (sesi %s).", session_id)

        ticket_id = msg.content.get("confirmation_id")
        skill_name = msg.content.get("skill_name", "")
        args = msg.content.get("args", {})
        if not isinstance(args, dict):
            return reply(False, {"success": False, "error": "args harus berupa objek"})
        workspace = str(self.permission_mgr.jail.base)

        if ticket_id:
            if msg.content.get("deny"):
                ticket = self.confirmations.get(str(ticket_id))
                if ticket is None or ticket.session_id != session_id:
                    return reply(False, {"success": False, "error": "titah tidak ditemukan"})
                self.confirmations.deny(ticket.ticket_id)
                return reply(True, {"success": True, "denied": True})
            ticket = self.confirmations.get(str(ticket_id))
            if ticket is not None and skill_name and skill_name != ticket.skill_name:
                return reply(False, {"success": False, "error": "skill tidak sesuai dengan titah"})
            if ticket is not None and ticket.session_id == session_id and ticket.workspace != workspace:
                self.confirmations.deny(ticket.ticket_id)
                return reply(False, {"success": False, "error": "ruang kerja berubah; titah dibatalkan"})
            try:
                ticket = self.confirmations.consume(str(ticket_id), session_id)
            except ConfirmationError as exc:
                return reply(False, {"success": False, "error": str(exc)})
            res = self.skills_runtime.execute(
                skill_name=ticket.skill_name,
                args=ticket.args,
                session_id=session_id,
                confirm_granted=True,
            )
            return reply(res.success, res.to_dict())

        if self.skills_runtime.needs_approval(skill_name):
            skill = self.skill_registry.get(skill_name)
            try:
                ticket = self.confirmations.request(
                    session_id,
                    skill_name,
                    args,
                    risk_level=str(getattr(skill, "risk_level", "high")),
                    workspace=workspace,
                    summary=describe_action(skill_name, args, workspace),
                )
            except ConfirmationError as exc:
                return reply(False, {"success": False, "error": str(exc)})
            return reply(
                False,
                {
                    "success": False,
                    "error": "confirmation_required",
                    "confirmation_id": ticket.ticket_id,
                    "card": render_ticket_card(ticket),
                },
            )

        res = self.skills_runtime.execute(
            skill_name=skill_name, args=args, session_id=session_id, confirm_granted=False
        )
        return reply(res.success, res.to_dict())

    def dispatch_inbound(self, msg: InboundMessage) -> OutboundMessage:
        """Memproses pesan masuk dari sembarang saluran secara terpusat."""
        # Ambil atau buat sesi jika belum ada
        sess = self.session_mgr.get_session(msg.session_id)
        if sess is None:
            sess = self.session_mgr.create_session(
                channel=msg.channel,
                session_id=msg.session_id,
            )
            self.event_bus.publish(
                Event(
                    event_type="session.created",
                    source="gateway",
                    payload={"session_id": sess.session_id, "channel": sess.channel},
                    session_id=sess.session_id,
                )
            )

        self.event_bus.publish(
            Event(
                event_type="session.message_received",
                source="gateway",
                payload={"type": msg.type, "correlation_id": msg.correlation_id},
                session_id=sess.session_id,
            )
        )

        ipc_channel = msg.metadata.get("ipc_channel", "")

        # Permintaan daftar skill
        if ipc_channel == "ruka:skills-list" or msg.type == "skill.list":
            return OutboundMessage(
                type="response",
                channel=msg.channel,
                session_id=sess.session_id,
                correlation_id=msg.correlation_id,
                content={"skills": self.skill_registry.to_tool_definitions()},
            )

        # Permintaan eksekusi skill langsung
        if ipc_channel == "ruka:skill-execute" or msg.type == "skill.execute":
            return self._handle_skill_execute(msg, sess.session_id)

        # Status runtime / Health check
        if ipc_channel == "ruka:runtime-status" or msg.type == "runtime.status" or (msg.type == "status" and not ipc_channel):
            uptime = time.time() - self.start_time
            health = loop_health(
                repeated_errors=0,
                max_allowed_errors=5,
                iterations=self.budget_ctrl.used_iterations,
                budget_iterations=self.budget_ctrl.max_iterations,
            )
            return OutboundMessage(
                type="response",
                channel=msg.channel,
                session_id=sess.session_id,
                correlation_id=msg.correlation_id,
                content={
                    "state": "ready",
                    "liveness": True,
                    "readiness": True,
                    "uptime_s": round(uptime, 1),
                    "health_score": round(health, 3),
                    "budget": self.budget_ctrl.summary(),
                },
            )

        # Permintaan status kesehatan organ PROJECT NOCTIS (FR-HE-01, FR-OS-06)
        if ipc_channel == "ruka:organ-status" or msg.type == "organ.status":
            return OutboundMessage(
                type="response",
                channel=msg.channel,
                session_id=sess.session_id,
                correlation_id=msg.correlation_id,
                content=self.supervisor.status(),
            )

        # Permintaan pose avatar 60 fps (FR-AV-01, FR-AV-10)
        if ipc_channel == "ruka:avatar-pose" or msg.type == "avatar.pose":
            pose = self.avatar.get_pose()
            return OutboundMessage(
                type="response",
                channel=msg.channel,
                session_id=sess.session_id,
                correlation_id=msg.correlation_id,
                content={
                    "frame_index": pose.frame_index,
                    "timestamp": pose.timestamp,
                    "bones": pose.bones.__dict__,
                    "blendshapes": pose.blendshapes,
                    "viseme": pose.viseme.__dict__,
                    "pupil": pose.pupil.__dict__,
                    "lod_level": pose.lod_level,
                },
            )

        # Pengaturan ekspresi blendshape avatar (FR-AV-10)
        if ipc_channel == "ruka:avatar-expression" or msg.type == "avatar.expression":
            name = str(msg.content.get("name", ""))
            weight = float(msg.content.get("weight", 1.0))
            ok = self.avatar.set_expression(name, weight)
            return OutboundMessage(
                type="response" if ok else "error",
                channel=msg.channel,
                session_id=sess.session_id,
                correlation_id=msg.correlation_id,
                content={"success": ok, "blendshape": name, "weight": weight},
            )

        # Pengaturan viseme suara avatar (FR-AV-10)
        if ipc_channel == "ruka:avatar-viseme" or msg.type == "avatar.viseme":
            viseme_id = str(msg.content.get("viseme_id", "sil"))
            weight = float(msg.content.get("weight", 1.0))
            ok = self.avatar.set_viseme(viseme_id, weight)
            return OutboundMessage(
                type="response" if ok else "error",
                channel=msg.channel,
                session_id=sess.session_id,
                correlation_id=msg.correlation_id,
                content={"success": ok, "viseme_id": viseme_id, "weight": weight},
            )

        # Status kehadiran dan mode tidur (FR-PR-01, FR-PR-10)
        if ipc_channel == "ruka:presence-status" or msg.type == "presence.status":
            frame = self.presence.latest_frame or self.presence.step_frame(0.016)
            return OutboundMessage(
                type="response",
                channel=msg.channel,
                session_id=sess.session_id,
                correlation_id=msg.correlation_id,
                content={
                    "frame_index": frame.frame_index,
                    "mood": frame.mood.value,
                    "chest_scale": frame.breathing.chest_scale,
                    "head_yaw": frame.head_yaw_deg,
                    "head_pitch": frame.head_pitch_deg,
                    "degradation": frame.degradation.value,
                    "sleep_mode": frame.is_sleep_mode,
                },
            )

        # Fase sirkadian Lunar Clock (FR-OS-07)
        if ipc_channel == "ruka:lunar-phase" or msg.type == "lunar.phase":
            from src.os_companion.lunar_clock import LunarClock
            phase = LunarClock.get_phase()
            constraints = LunarClock.get_mood_constraints(phase)
            return OutboundMessage(
                type="response",
                channel=msg.channel,
                session_id=sess.session_id,
                correlation_id=msg.correlation_id,
                content={
                    "phase": phase.value,
                    "voice_allowed": LunarClock.is_voice_allowed(phase),
                    "constraints": constraints,
                },
            )

        # Pencarian Memori Istana (FR-ME / Memory Palace RAG)
        if ipc_channel == "ruka:memory-search" or msg.type == "memory.search":
            q = str(msg.content.get("query", ""))
            limit = int(msg.content.get("limit", 5))
            results = self.memory_palace.recall(q, top_k=limit)
            hits = [
                {
                    "entry_id": r.entry_id,
                    "wing": r.wing.value if hasattr(r.wing, "value") else str(r.wing),
                    "content": r.content,
                    "score": r.score,
                    "sources": r.match_sources,
                }
                for r in results
            ]
            return OutboundMessage(
                type="response",
                channel=msg.channel,
                session_id=sess.session_id,
                correlation_id=msg.correlation_id,
                content={"hits": hits, "took_ms": 1.0},
            )

        user_text = msg.content.get("text", "")
        attachment = msg.content.get("attachment")

        if self.brain is not None and hasattr(self.brain, "think_and_reply"):
            try:
                reply = self.brain.think_and_reply(user_text, attachment=attachment)
            except Exception as ex:
                log.error("CognitiveBrain error: %s", ex)
                reply = f"Young Lord, hamba mengalami hambatan internal saat menelaah: {ex}"
        else:
            reply = f"Young Lord, hamba telah mendengar titah: '{user_text}'. Nalar kognitif sedang dalam penyesuaian."

        self.budget_ctrl.record_step(tokens=len(user_text) + len(reply))

        self.event_bus.publish(
            Event(
                event_type="session.response_dispatched",
                source="gateway",
                payload={"correlation_id": msg.correlation_id},
                session_id=sess.session_id,
            )
        )

        return OutboundMessage(
            type="response",
            channel=msg.channel,
            session_id=sess.session_id,
            correlation_id=msg.correlation_id,
            content={
                "seq": 1,
                "delta": reply,
                "done": True,
            },
        )

    def start(self) -> None:
        """Memulai listener Gateway pada socket loopback lokal."""
        self.server_sock.listen(5)
        self.running = True
        self.desktop_adapter.start()
        self.cli_adapter.start()

        self.event_bus.publish(
            Event(
                event_type="gateway.started",
                source="gateway",
                payload={"host": self.host, "port": self.port},
            )
        )

        accept_thread = threading.Thread(target=self._accept_loop, daemon=True)
        accept_thread.start()

    def stop(self) -> None:
        """Menghentikan seluruh layanan Gateway."""
        self.running = False
        self.desktop_adapter.stop()
        self.cli_adapter.stop()
        if hasattr(self, "supervisor") and self.supervisor:
            try:
                self.supervisor.stop()
            except Exception:
                pass
        if hasattr(self, "presence") and self.presence:
            try:
                self.presence.stop()
            except Exception:
                pass
        with self._lock:
            for c in self._clients:
                try:
                    c.close()
                except Exception:
                    pass
            self._clients.clear()
        try:
            self.server_sock.close()
        except Exception:
            pass

    def _accept_loop(self) -> None:
        while self.running:
            try:
                self.server_sock.settimeout(0.1)
                conn, addr = self.server_sock.accept()
                with self._lock:
                    self._clients.append(conn)
                t = threading.Thread(target=self._client_handler, args=(conn,), daemon=True)
                t.start()
            except socket.timeout:
                continue
            except Exception as e:
                if self.running:
                    log.warning("Gateway accept error: %s", e)

    def _client_handler(self, conn: socket.socket) -> None:
        buf = ""
        authenticated = False
        session_id = f"sess_conn_{uuid.uuid4().hex[:8]}"
        conn.settimeout(0.2)


        try:
            while self.running:
                try:
                    data = conn.recv(65536)
                except (socket.timeout, TimeoutError):
                    continue
                except (ConnectionResetError, BrokenPipeError, OSError):
                    break
                if not data:
                    break


                buf += data.decode("utf-8", errors="ignore")
                while "\n" in buf:
                    line, buf = buf.split("\n", 1)
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        raw_req = json.loads(line)
                    except Exception:
                        continue

                    # Handshake check
                    chan = raw_req.get("channel")
                    if chan == "hello":
                        resp, auth = self.desktop_adapter.process_raw_ipc_request(raw_req, session_id=session_id)
                        if auth is not None:
                            authenticated = auth
                        if resp:
                            conn.sendall((json.dumps(resp) + "\n").encode("utf-8"))
                        continue

                    if not authenticated:
                        err_resp = {
                            "type": "error",
                            "channel": chan,
                            "correlationId": raw_req.get("correlationId", "corr-default"),
                            "protocolVersion": 2,
                            "payload": {"error": "Belum terautentikasi"},
                            "ts": time.time(),
                        }
                        conn.sendall((json.dumps(err_resp) + "\n").encode("utf-8"))
                        continue

                    resp, _ = self.desktop_adapter.process_raw_ipc_request(raw_req, session_id=session_id)
                    if resp:
                        conn.sendall((json.dumps(resp) + "\n").encode("utf-8"))

        except Exception as ex:
            log.debug("Client handler info: %s", ex)
        finally:
            with self._lock:
                if conn in self._clients:
                    self._clients.remove(conn)
            try:
                conn.close()
            except Exception:
                pass
            self.session_mgr.close_session(session_id)
