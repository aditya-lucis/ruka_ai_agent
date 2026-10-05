# -*- coding: utf-8 -*-
"""Shadow Hands Models & Frozen Action Space (FR-HA-01, FR-HA-10).

Ruang aksi tertutup lima kata kerja sebagai dataclass beku (frozen):
- ClickAction
- TypeAction
- ScrollAction
- KeyAction
- WaitAction
Kata kerja asing di luar lima ini ditolak keras secara deterministik.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Tuple, Union


class RiskLevel(str, Enum):
    GREEN = "green"    # Eksekusi langsung + audit
    YELLOW = "yellow"  # Toast 2 detik yang dapat dibatalkan
    RED = "red"        # Overlay konfirmasi wajib (timeout 60s -> deny)


class PermissionVerdict(str, Enum):
    ALLOW = "allow"
    CONFIRM = "confirm"
    DENY = "deny"


# Lima kata kerja tertutup beku
@dataclass(frozen=True)
class ClickAction:
    x: int
    y: int
    button: str = "left"  # left, right, middle
    clicks: int = 1


@dataclass(frozen=True)
class TypeAction:
    text: str
    interval_ms: float = 40.0


@dataclass(frozen=True)
class ScrollAction:
    dx: int
    dy: int


@dataclass(frozen=True)
class KeyAction:
    key: str
    modifiers: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class WaitAction:
    duration_ms: float


ShadowAction = Union[ClickAction, TypeAction, ScrollAction, KeyAction, WaitAction]
VALID_ACTION_TYPES = (ClickAction, TypeAction, ScrollAction, KeyAction, WaitAction)


def validate_action(action: Any) -> ShadowAction:
    """Memvalidasi aksi sistem operasi. Menolak keras aksi asing."""
    if not isinstance(action, VALID_ACTION_TYPES):
        raise ValueError(
            f"Aksi '{type(action).__name__}' tidak sah! Ruang aksi Shadow Hands hanya mengizinkan: "
            f"{[t.__name__ for t in VALID_ACTION_TYPES]}"
        )
    return action
