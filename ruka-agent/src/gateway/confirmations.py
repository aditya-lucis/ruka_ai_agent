# -*- coding: utf-8 -*-
"""RUKA Gateway — Confirmation tickets (human-in-the-loop approvals).

Risky skill executions are never authorised by a client-asserted flag. Instead the
server issues a *ticket* bound to the exact action (skill + canonical args), the
workspace it was proposed in and the requesting session. A ticket is single-use,
expires after a TTL and is tamper-evident (SHA-256 digest re-verified on consume).

Approval text typed by the human is interpreted deterministically by
:func:`parse_approval`; it is never delegated to an LLM.
"""
from __future__ import annotations

import copy
import hashlib
import json
import re
import secrets
import threading
import time
from dataclasses import dataclass
from typing import Any, Callable, Sequence

from src.gateway.events import Event, EventBus

DEFAULT_TTL_SECONDS = 300.0
MAX_PENDING_PER_SESSION = 3
MAX_ARGS_BYTES = 200_000


class ConfirmationError(RuntimeError):
    """Raised when a ticket is missing, expired, consumed, mismatched or tampered with."""


def _canonical(skill_name: str, args: dict[str, Any], workspace: str) -> str:
    return json.dumps(
        {"skill": skill_name, "args": args, "workspace": workspace},
        sort_keys=True,
        ensure_ascii=False,
        default=str,
    )


def _digest(skill_name: str, args: dict[str, Any], workspace: str) -> str:
    return hashlib.sha256(_canonical(skill_name, args, workspace).encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class PendingAction:
    """An approval request bound to one exact action."""

    ticket_id: str
    session_id: str
    skill_name: str
    args_json: str
    risk_level: str
    workspace: str
    summary: str
    destructive: bool
    created_at: float
    expires_at: float
    digest: str

    @property
    def args(self) -> dict[str, Any]:
        """A fresh deep copy of the stored arguments (the ticket itself stays immutable)."""
        return copy.deepcopy(json.loads(self.args_json))


class ConfirmationManager:
    """Thread-safe store of pending approvals with TTL, single-use and audit events."""

    def __init__(
        self,
        ttl_seconds: float = DEFAULT_TTL_SECONDS,
        max_pending_per_session: int = MAX_PENDING_PER_SESSION,
        event_bus: EventBus | None = None,
        clock: Callable[[], float] = time.time,
    ) -> None:
        self.ttl_seconds = ttl_seconds
        self.max_pending_per_session = max_pending_per_session
        self.event_bus = event_bus
        self._clock = clock
        self._lock = threading.RLock()
        self._tickets: dict[str, PendingAction] = {}

    # -- internals -----------------------------------------------------
    def _emit(self, event_type: str, ticket: PendingAction) -> None:
        if self.event_bus is None:
            return
        self.event_bus.publish(
            Event(
                event_type=event_type,
                source="confirmations",
                payload={
                    "ticket_id": ticket.ticket_id,
                    "skill_name": ticket.skill_name,
                    "risk_level": ticket.risk_level,
                    "digest": ticket.digest,
                },
                session_id=ticket.session_id,
            )
        )

    def _purge_expired(self) -> None:
        now = self._clock()
        for tid in [t for t, p in self._tickets.items() if p.expires_at <= now]:
            expired = self._tickets.pop(tid)
            self._emit("confirmation.expired", expired)

    # -- public API ----------------------------------------------------
    def request(
        self,
        session_id: str,
        skill_name: str,
        args: dict[str, Any],
        *,
        risk_level: str,
        workspace: str,
        summary: str = "",
        destructive: bool = False,
    ) -> PendingAction:
        """Issue (or re-use) a ticket for one exact action."""
        args_json = json.dumps(args, sort_keys=True, ensure_ascii=False, default=str)
        if len(args_json.encode("utf-8")) > MAX_ARGS_BYTES:
            raise ConfirmationError("Argumen aksi terlalu besar untuk diajukan sebagai titah persetujuan.")
        clean_args = json.loads(args_json)
        digest = _digest(skill_name, clean_args, workspace)

        with self._lock:
            self._purge_expired()
            session_tickets = [p for p in self._tickets.values() if p.session_id == session_id]
            for existing in session_tickets:
                if existing.digest == digest:
                    return existing
            if len(session_tickets) >= self.max_pending_per_session:
                raise ConfirmationError(
                    f"Terlalu banyak titah menunggu persetujuan ({len(session_tickets)}). "
                    "Selesaikan atau batalkan salah satunya terlebih dahulu."
                )
            ticket_id = secrets.token_hex(3)
            while ticket_id in self._tickets:
                ticket_id = secrets.token_hex(3)
            now = self._clock()
            ticket = PendingAction(
                ticket_id=ticket_id,
                session_id=session_id,
                skill_name=skill_name,
                args_json=args_json,
                risk_level=str(risk_level),
                workspace=workspace,
                summary=summary,
                destructive=destructive,
                created_at=now,
                expires_at=now + self.ttl_seconds,
                digest=digest,
            )
            self._tickets[ticket_id] = ticket
        self._emit("confirmation.requested", ticket)
        return ticket

    def pending(self, session_id: str) -> list[PendingAction]:
        """Live (unexpired, unconsumed) tickets of a session, oldest first."""
        with self._lock:
            self._purge_expired()
            items = [p for p in self._tickets.values() if p.session_id == session_id]
        return sorted(items, key=lambda p: p.created_at)

    def get(self, ticket_id: str) -> PendingAction | None:
        with self._lock:
            self._purge_expired()
            return self._tickets.get(ticket_id)

    def consume(self, ticket_id: str, session_id: str) -> PendingAction:
        """Atomically validate and burn a ticket. Raises ConfirmationError on any mismatch."""
        with self._lock:
            self._purge_expired()
            ticket = self._tickets.get(ticket_id)
            if ticket is None:
                raise ConfirmationError(
                    f"Titah {ticket_id!r} tidak ditemukan, sudah kedaluwarsa, atau sudah dipakai."
                )
            if ticket.session_id != session_id:
                raise ConfirmationError("Titah ini milik sesi lain dan tidak dapat disetujui dari sesi ini.")
            if _digest(ticket.skill_name, ticket.args, ticket.workspace) != ticket.digest:
                self._tickets.pop(ticket_id, None)
                raise ConfirmationError("Integritas titah gagal diverifikasi; titah dibatalkan demi keamanan.")
            self._tickets.pop(ticket_id)
        self._emit("confirmation.approved", ticket)
        return ticket

    def deny(self, ticket_id: str) -> bool:
        with self._lock:
            self._purge_expired()
            ticket = self._tickets.pop(ticket_id, None)
        if ticket is not None:
            self._emit("confirmation.denied", ticket)
            return True
        return False

    def deny_all(self, session_id: str) -> int:
        count = 0
        for ticket in self.pending(session_id):
            if self.deny(ticket.ticket_id):
                count += 1
        return count


# ---------------------------------------------------------------------------
# Deterministic parsing of the human's reply
# ---------------------------------------------------------------------------

_APPROVE = frozenset(
    {
        "ya", "iya", "y", "yes", "yep", "yup", "ok", "oke", "okay", "setuju", "lanjut", "lanjutkan",
        "silakan", "silahkan", "boleh", "gas", "sikat", "approve", "approved", "benar", "betul",
        "izinkan", "kabulkan", "laksanakan", "jalankan",
    }
)
_STRONG = frozenset({"yakin", "konfirmasi", "confirm", "confirmed", "pasti", "sure"})
_DENY = frozenset(
    {
        "tidak", "nggak", "enggak", "ga", "gak", "no", "nope", "batal", "batalkan", "cancel",
        "tolak", "jangan", "stop", "hentikan", "urungkan", "tak",
    }
)
_FILLER = frozenset(
    {
        "ruka", "young", "lord", "my", "sir", "dong", "deh", "saja", "aja", "lah", "nih", "tolong",
        "sekarang", "itu", "tersebut", "titah", "aksi", "saya", "aku", "ini", "tuan",
    }
)
MAX_APPROVAL_TOKENS = 8


@dataclass(frozen=True)
class ApprovalDecision:
    kind: str | None            # "approve" | "deny" | None (not an approval reply)
    strong: bool = False        # explicit "yakin"/"confirm" wording present
    ticket_id: str | None = None


def parse_approval(text: str, pending_ids: Sequence[str] = ()) -> ApprovalDecision:
    """Interpret a short human reply as approve / deny / unrelated.

    Deliberately strict: every token must be an approval word, a denial word, a filler
    word or a pending ticket id. Anything else (e.g. a new instruction) is not an approval.
    Contradictory replies (approve + deny words) resolve to deny.
    """
    tokens = re.findall(r"[a-z0-9]+", (text or "").lower())
    if not tokens or len(tokens) > MAX_APPROVAL_TOKENS:
        return ApprovalDecision(None)

    ids = {i.lower() for i in pending_ids}
    named = [t for t in tokens if t in ids]
    allowed = _APPROVE | _STRONG | _DENY | _FILLER | ids
    if any(t not in allowed for t in tokens):
        return ApprovalDecision(None)

    ticket_id = named[0] if named else None
    if any(t in _DENY for t in tokens):
        return ApprovalDecision("deny", ticket_id=ticket_id)
    if any(t in _APPROVE or t in _STRONG for t in tokens):
        return ApprovalDecision(
            "approve", strong=any(t in _STRONG for t in tokens), ticket_id=ticket_id
        )
    return ApprovalDecision(None)


# ---------------------------------------------------------------------------
# Deterministic rendering of what is being asked
# ---------------------------------------------------------------------------

def _clip(value: Any, limit: int) -> str:
    text = value if isinstance(value, str) else json.dumps(value, ensure_ascii=False, default=str)
    return text if len(text) <= limit else text[:limit] + f"... [+{len(text) - limit} karakter]"


def describe_action(skill_name: str, args: dict[str, Any], workspace: str) -> str:
    """Plain, persona-free description of the exact action (safe to place in a code block)."""
    lines = [f"skill     : {skill_name}", f"workspace : {workspace}"]
    if skill_name == "run_terminal":
        lines.append(f"command   : {_clip(args.get('command', ''), 600)}")
        if args.get("working_directory"):
            lines.append(f"cwd       : {args['working_directory']}")
    elif skill_name == "code_write":
        content = args.get("content", "")
        lines.append(f"path      : {args.get('path', '')}")
        lines.append(f"size      : {len(content)} karakter")
        lines.append("content   :")
        lines.append(_clip(content, 800))
    elif skill_name == "code_edit":
        lines.append(f"path      : {args.get('path', '')}")
        lines.append(f"replace_all: {bool(args.get('replace_all', False))}")
        lines.append("--- old_string")
        lines.append(_clip(args.get("old_string", ""), 500))
        lines.append("+++ new_string")
        lines.append(_clip(args.get("new_string", ""), 500))
    else:
        lines.append(f"args      : {_clip(args, 800)}")
    return "\n".join(lines)


def render_ticket_card(ticket: PendingAction) -> str:
    """Approval card appended by the system itself so the human always sees the exact action."""
    minutes = max(1, int(round((ticket.expires_at - ticket.created_at) / 60)))
    header = (
        f"**Titah menunggu restu Young Lord** — ID `{ticket.ticket_id}` · risiko **{ticket.risk_level}**"
    )
    body = f"```text\n{ticket.summary}\n```"
    if ticket.destructive:
        how = (
            "Aksi ini berpotensi merusak. Balas `ya, saya yakin` untuk menyetujui "
            f"atau `batal` untuk membatalkan (berlaku {minutes} menit)."
        )
    else:
        how = f"Balas `ya` untuk menyetujui atau `batal` untuk membatalkan (berlaku {minutes} menit)."
    return f"{header}\n{body}\n{how}"
