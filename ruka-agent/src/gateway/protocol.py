# -*- coding: utf-8 -*-
"""RUKA Gateway — Communication Protocol & Message Schemas.

Mendefinisikan skema pesan Inbound, Outbound, dan Control Messages
antara berbagai Clients (Desktop Electron, CLI) dan Ruka Gateway.
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Mapping


@dataclass
class InboundMessage:
    """Pesan masuk dari Client menuju Gateway."""
    type: str                                           # "message" | "control" | "event"
    channel: str                                        # "desktop" | "cli" | "telegram"
    session_id: str
    content: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)
    correlation_id: str = field(default_factory=lambda: f"corr_{uuid.uuid4().hex[:8]}")
    timestamp: float = field(default_factory=time.time)

    @classmethod
    def from_legacy_ipc(cls, req: dict[str, Any], channel: str = "desktop", session_id: str = "default") -> InboundMessage:
        """Membuat InboundMessage dari format JSON IPC lawas."""
        cid = req.get("correlationId") or f"corr_{uuid.uuid4().hex[:8]}"
        payload = req.get("payload", {})
        req_type = req.get("type", "message")
        return cls(
            type=req_type,
            channel=channel,
            session_id=session_id,
            content=payload,
            metadata={"ipc_channel": req.get("channel")},
            correlation_id=cid,
            timestamp=req.get("ts", time.time()),
        )


@dataclass
class OutboundMessage:
    """Pesan keluar dari Gateway menuju Client."""
    type: str                                           # "response" | "error" | "event" | "stream"
    channel: str
    session_id: str
    correlation_id: str
    content: dict[str, Any] = field(default_factory=dict)
    events: list[dict[str, Any]] = field(default_factory=list)
    timestamp: float = field(default_factory=time.time)

    def to_legacy_ipc(self, legacy_channel: str | None = None) -> dict[str, Any]:
        """Konversi kembali ke skema loopback IPC JSONL untuk kompatibilitas desktop Electron."""
        chan = legacy_channel or self.channel
        return {
            "type": self.type,
            "channel": chan,
            "correlationId": self.correlation_id,
            "protocolVersion": 2,
            "payload": self.content,
            "events": self.events,
            "ts": self.timestamp,
        }
