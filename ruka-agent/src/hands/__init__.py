# -*- coding: utf-8 -*-
"""Shadow Hands Automation Package (FR-HA)."""
from src.hands.audit import AuditTrail
from src.hands.bezier import HumanMouseTrajectory
from src.hands.confirm import ConfirmGate, ConfirmTicket
from src.hands.controller import ShadowHands
from src.hands.gate import ActionGate
from src.hands.input_os import SafeInputOS
from src.hands.models import (
    ClickAction,
    KeyAction,
    PermissionVerdict,
    RiskLevel,
    ScrollAction,
    ShadowAction,
    TypeAction,
    WaitAction,
    validate_action,
)
from src.hands.worker import SingleWriterWorker

__all__ = [
    "ActionGate",
    "AuditTrail",
    "ClickAction",
    "ConfirmGate",
    "ConfirmTicket",
    "HumanMouseTrajectory",
    "KeyAction",
    "PermissionVerdict",
    "RiskLevel",
    "SafeInputOS",
    "ScrollAction",
    "ShadowAction",
    "ShadowHands",
    "SingleWriterWorker",
    "TypeAction",
    "WaitAction",
    "validate_action",
]
