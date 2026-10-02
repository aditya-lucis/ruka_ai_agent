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
from src.gateway.skills.coding_bridge import register_builtin_coding_skills
from src.math_foundations.control import BudgetController, loop_health

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
        self.budget_ctrl = BudgetController()
        self.brain = brain

        # Subsistem Skills
        self.skill_registry = SkillRegistry()
        self.skills_runtime = SkillsRuntime(
            registry=self.skill_registry,
            permission_manager=self.permission_mgr,
            event_bus=self.event_bus,
        )
        try:
            candidates = [
                Path(sys.executable).parent / "skills",
                Path(getattr(sys, "_MEIPASS", "")) / "skills",
                Path.cwd() / "skills",
                Path(__file__).resolve().parent.parent.parent.parent / "skills",
            ]
            skills_dir = next((p for p in candidates if p.exists() and p.is_dir()), candidates[-1])
            register_builtin_coding_skills(self.skill_registry, skills_dir=skills_dir, workspace_root=workspace_root)
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
            skill_name = msg.content.get("skill_name", "")
            args = msg.content.get("args", {})
            confirmed = msg.content.get("confirm_granted", False)
            res = self.skills_runtime.execute(
                skill_name=skill_name,
                args=args,
                session_id=sess.session_id,
                confirm_granted=confirmed,
            )
            return OutboundMessage(
                type="response" if res.success else "error",
                channel=msg.channel,
                session_id=sess.session_id,
                correlation_id=msg.correlation_id,
                content=res.to_dict(),
            )

        # Status runtime / Health check
        if ipc_channel == "ruka:runtime-status" or msg.type == "status":
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

        # Pemrosesan Obrolan Kognitif (Chat / Coding Prompt)

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
