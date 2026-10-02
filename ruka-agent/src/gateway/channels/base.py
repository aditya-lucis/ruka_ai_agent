# -*- coding: utf-8 -*-
"""RUKA Gateway — Base Channel Adapter Interface.

Setiap antarmuka komunikasi (Desktop Electron, Terminal CLI, Telegram, dsb.)
mengimplementasikan adapter ini untuk menghubungkan antarmuka luar dengan Gateway.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Callable
from src.gateway.protocol import InboundMessage, OutboundMessage


class BaseChannelAdapter(ABC):
    """Kelas abstrak dasar untuk Channel Adapter."""

    def __init__(self, channel_name: str) -> None:
        self.channel_name = channel_name
        self._handler: Callable[[InboundMessage], OutboundMessage | None] | None = None

    def set_message_handler(self, handler: Callable[[InboundMessage], OutboundMessage | None]) -> None:
        """Menetapkan callback pemrosesan pesan dari Gateway."""
        self._handler = handler

    def handle_inbound(self, message: InboundMessage) -> OutboundMessage | None:
        """Meneruskan pesan masuk ke pemroses Gateway."""
        if self._handler is not None:
            return self._handler(message)
        return None

    @abstractmethod
    def start(self) -> None:
        """Memulai listener saluran."""
        pass

    @abstractmethod
    def stop(self) -> None:
        """Menghentikan saluran komunikasi."""
        pass
