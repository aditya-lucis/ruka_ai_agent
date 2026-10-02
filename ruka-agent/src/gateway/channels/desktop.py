# -*- coding: utf-8 -*-
"""RUKA Gateway — Desktop Channel Adapter.

Menghubungkan Desktop Electron ke Gateway melalui protokol IPC loopback socket,
mempertahankan kompatibilitas 100% dengan frontend Electron yang ada.
"""
from __future__ import annotations

import json
import logging
from typing import Any

from src.gateway.channels.base import BaseChannelAdapter
from src.gateway.protocol import InboundMessage, OutboundMessage

log = logging.getLogger("ruka.gateway.desktop")


class DesktopChannelAdapter(BaseChannelAdapter):
    """Adapter untuk Desktop Electron UI."""

    def __init__(self, token: str) -> None:
        super().__init__(channel_name="desktop")
        self.token = token
        self._running = False

    def start(self) -> None:
        self._running = True

    def stop(self) -> None:
        self._running = False

    def process_raw_ipc_request(self, raw_req: dict[str, Any], session_id: str = "default_desktop") -> tuple[dict[str, Any] | None, bool | None]:
        """Memproses request mentah dari socket Electron.

        Returns:
            tuple (response_dict, new_auth_state_or_None)
        """
        channel = raw_req.get("channel")
        cid = raw_req.get("correlationId", "corr-default")
        payload = raw_req.get("payload", {})

        # Handshake verifikasi token
        if channel == "hello":
            token = payload.get("token")
            if token == self.token:
                return {
                    "type": "response",
                    "channel": "hello",
                    "correlationId": cid,
                    "protocolVersion": 2,
                    "payload": {"ok": True, "protocol_version": 2},
                }, True
            else:
                return {
                    "type": "error",
                    "channel": "hello",
                    "correlationId": cid,
                    "protocolVersion": 2,
                    "payload": {"error": "Token handshake tidak valid"},
                }, False

        inbound = InboundMessage.from_legacy_ipc(raw_req, channel="desktop", session_id=session_id)
        outbound = self.handle_inbound(inbound)

        if outbound is not None:
            return outbound.to_legacy_ipc(legacy_channel=channel), None
        return None, None
