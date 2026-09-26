"""RUKA VI: Delegation Registry and Delegated Grant.
Strictly follows RUKA-VI Chapter IX.
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable

from .types import AuthenticationStrength, RecognitionState

NON_DELEGATABLE: frozenset[str] = frozenset(
    {
        "terminal.execute",
        "memory.delete",
        "permission.grant",
        "system.shutdown",
    }
)

DELEGATABLE_CAPABILITIES: frozenset[str] = frozenset(
    {
        "filesystem.read",
        "filesystem.write",
        "excel.read",
        "excel.write",
        "document.read",
        "search.read",
        "tasks.read",
        "tasks.create",
    }
) | NON_DELEGATABLE


class DelegationState(str, Enum):
    PENDING_CONFIRM = "PENDING_CONFIRM"
    ACTIVE = "ACTIVE"
    EXPIRED = "EXPIRED"
    REVOKED = "REVOKED"


@dataclass
class DelegatedGrant:
    """Satu hibah delegasi — imutable kecuali state administratif."""

    grant_id: str
    grantor: str  # profile_id pemberi (wajib role 'bos')
    grantee: str  # profile_id penerima
    capabilities: frozenset[str]
    scope: dict[str, str] = field(default_factory=dict)
    created_at_ms: int = field(default_factory=lambda: int(time.time() * 1000))
    expires_at_ms: int | None = None
    state: DelegationState = DelegationState.PENDING_CONFIRM
    revoked_reason: str | None = None
    _tick: Callable[[], int] = field(
        default=lambda: int(time.time() * 1000), repr=False, compare=False
    )

    def is_active(self, now_ms: int | None = None) -> bool:
        now = self._tick() if now_ms is None else now_ms
        if self.state == DelegationState.REVOKED:
            return False
        if self.expires_at_ms is not None and now >= self.expires_at_ms:
            self.state = DelegationState.EXPIRED
            return False
        return self.state == DelegationState.ACTIVE

    def revoke(self, reason: str = "manual") -> None:
        """Pencabutan EFEKTIF LANGSUNG tanpa restart runtime."""
        self.state = DelegationState.REVOKED
        self.revoked_reason = reason

    def activate(self) -> None:
        if self.state != DelegationState.PENDING_CONFIRM:
            raise ValueError(f"aktivasi ilegal dari state {self.state}")
        self.state = DelegationState.ACTIVE


class DelegationRegistry:
    """Registri delegasi + evaluasi kapabilitas delegated-user."""

    def __init__(self, floor_ms: int = 0) -> None:
        self._grants: dict[str, DelegatedGrant] = {}
        self._now: Callable[[], int] = lambda: int(time.time() * 1000) + floor_ms

    def propose(
        self,
        grantor: str,
        grantee: str,
        capabilities: set[str],
        scope: dict[str, str] | None = None,
        ttl_ms: int | None = None,
    ) -> DelegatedGrant:
        """Usulan delegasi — LAHIR PENDING_CONFIRM (Bos mengonfirmasi)."""
        illegal = set(capabilities) & NON_DELEGATABLE
        if illegal:
            raise ValueError(f"kapabilitas tak bisa didelegasikan: {sorted(illegal)}")
        unknown = set(capabilities) - DELEGATABLE_CAPABILITIES
        if unknown:
            raise ValueError(f"kapabilitas tak dikenal: {sorted(unknown)}")
        if ttl_ms is not None and ttl_ms <= 0:
            raise ValueError("ttl_ms > 0 atau None")
        now = self._now()
        grant = DelegatedGrant(
            grant_id=f"dlg-{uuid.uuid4().hex[:12]}",
            grantor=grantor,
            grantee=grantee,
            capabilities=frozenset(capabilities),
            scope=dict(scope or {}),
            created_at_ms=now,
            expires_at_ms=(now + ttl_ms) if ttl_ms is not None else None,
        )
        self._grants[grant.grant_id] = grant
        return grant

    def confirm(self, grant_id: str) -> DelegatedGrant:
        g = self._grants.get(grant_id)
        if g is None:
            raise KeyError(grant_id)
        g.activate()
        return g

    def revoke(self, grant_id: str, reason: str = "manual") -> None:
        g = self._grants.get(grant_id)
        if g is None:
            raise KeyError(grant_id)
        g.revoke(reason)

    def check(
        self, grantee: str, capability: str, now_ms: int | None = None
    ) -> tuple[bool, str]:
        """Bolehkah grantee memakai kapabilitas? → (allowed, alasan)."""
        now = self._now() if now_ms is None else now_ms
        for g in sorted(self._grants.values(), key=lambda x: x.grant_id):
            if g.grantee == grantee and capability in g.capabilities:
                if g.is_active(now):
                    return True, f"grant {g.grant_id} aktif"
                return False, f"grant {g.grant_id} state={g.state.value}"
        return False, "tidak ada grant aktif untuk pasangan (grantee, capability)"

    def check_with_recognition(
        self,
        grantee: str,
        capability: str,
        recognition_state: RecognitionState,
        auth: AuthenticationStrength,
        now_ms: int | None = None,
    ) -> tuple[bool, str]:
        """Delegasi + kondisi pengenalan: LOW_CONFIDENCE/SUSPICIOUS/UNKNOWN → tolak."""
        if recognition_state not in (RecognitionState.KNOWN,):
            return False, f"recognition {recognition_state.value} tak memenuhi"
        if auth == AuthenticationStrength.NONE:
            return False, "authentication NONE tak memenuhi syarat delegasi"
        return self.check(grantee, capability, now_ms=now_ms)
