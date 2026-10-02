# -*- coding: utf-8 -*-
"""RUKA Gateway — CLI Channel Adapter.

Menghubungkan sesi Terminal / CLI interaktif ke Ruka Gateway.
"""
from __future__ import annotations

import logging
from typing import Any

from src.gateway.channels.base import BaseChannelAdapter
from src.gateway.protocol import InboundMessage, OutboundMessage

log = logging.getLogger("ruka.gateway.cli")


class CliChannelAdapter(BaseChannelAdapter):
    """Adapter saluran interaksi Terminal CLI."""

    def __init__(self) -> None:
        super().__init__(channel_name="cli")
        self._running = False

    def start(self) -> None:
        self._running = True

    def stop(self) -> None:
        self._running = False

    def send_prompt(
        self,
        prompt: str,
        session_id: str,
        metadata: dict[str, Any] | None = None,
    ) -> OutboundMessage | None:
        """Mengirim pesan dari terminal ke Gateway dan menerima respons sinkron."""
        inbound = InboundMessage(
            type="message",
            channel="cli",
            session_id=session_id,
            content={"text": prompt},
            metadata=metadata or {},
        )
        return self.handle_inbound(inbound)
