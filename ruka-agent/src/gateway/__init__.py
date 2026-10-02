# -*- coding: utf-8 -*-
"""RUKA Gateway — Local Control Plane.

Paket Gateway menyatukan:
- RukaGatewayServer: Server kontrol utama
- Session & SessionManager: Pengelolaan sesi interaktif
- Event & EventBus: Saluran observabilitas Pub/Sub
- PermissionManager & PathJail: Keamanan Zero-Trust
- Protocol: Format pesan masuk & keluar
- Channel Adapters: Desktop Electron, CLI, dsb.
"""
from __future__ import annotations

from src.gateway.protocol import InboundMessage, OutboundMessage
from src.gateway.session import Session, SessionManager
from src.gateway.events import Event, EventBus
from src.gateway.permissions import PermissionManager, RiskLevel, Permission
from src.gateway.server import RukaGatewayServer

__all__ = [
    "InboundMessage",
    "OutboundMessage",
    "Session",
    "SessionManager",
    "Event",
    "EventBus",
    "PermissionManager",
    "RiskLevel",
    "Permission",
    "RukaGatewayServer",
]
