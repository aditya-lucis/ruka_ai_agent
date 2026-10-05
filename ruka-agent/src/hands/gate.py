# -*- coding: utf-8 -*-
"""Action Gate & Fail-Closed Policy Rails (FR-HA-01, FR-HA-04, FR-HA-07).

Satu pintu gerbang aksi sistem operasi:
- Kebijakan gagal-tertutup (fail-closed): jika kebijakan rusak/hilang, seluruh aksi ditolak.
- Zona terlarang dan denylist regex (keamanan kata sandi, perbankan, form kredensial).
- Putusan izin tiga nilai: ALLOW, CONFIRM, DENY.
"""
from __future__ import annotations

import re
from typing import Any
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

DENYLIST_PATTERNS = [
    re.compile(r"(?i)\b(?:password|passwd|pin|cvv|secret|token|private[_\s]key)\b"),
    re.compile(r"(?i)\b(?:bank|banking|klikbca|mandiri|bca|paypal|stripe)\b"),
]


class ActionGate:
    def __init__(self, policy_healthy: bool = True) -> None:
        self.policy_healthy = policy_healthy
        self.forbidden_zones: list[tuple[int, int, int, int]] = []  # (x1, y1, x2, y2)

    def add_forbidden_zone(self, x1: int, y1: int, x2: int, y2: int) -> None:
        self.forbidden_zones.append((x1, y1, x2, y2))

    def evaluate(
        self,
        action: ShadowAction,
        target_context: str = "",
        risk_level: RiskLevel = RiskLevel.GREEN,
    ) -> PermissionVerdict:
        """Mengevaluasi izin aksi dengan kebijakan gagal-tertutup mutlak."""
        # 1. Validasi tipe aksi tertutup
        validate_action(action)

        # 2. Penegakan Gagal-Tertutup (Fail-Closed)
        if not self.policy_healthy:
            return PermissionVerdict.DENY

        # 3. Pengecekan Denylist pada konteks target atau teks ketikan
        check_text = target_context
        if isinstance(action, TypeAction):
            check_text = f"{target_context} {action.text}"

        for pat in DENYLIST_PATTERNS:
            if pat.search(check_text):
                return PermissionVerdict.DENY

        # 4. Pengecekan Zona Koordinat Terlarang
        if isinstance(action, ClickAction):
            for x1, y1, x2, y2 in self.forbidden_zones:
                if x1 <= action.x <= x2 and y1 <= action.y <= y2:
                    return PermissionVerdict.DENY

        # 5. Pengecekan Tingkat Risiko
        if risk_level == RiskLevel.RED:
            return PermissionVerdict.CONFIRM
        elif risk_level == RiskLevel.YELLOW:
            # Yellow diizinkan tapi butuh toast peringatan
            return PermissionVerdict.ALLOW
        else:
            return PermissionVerdict.ALLOW
