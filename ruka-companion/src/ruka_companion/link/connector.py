"""RUKA VI: Secure Link Connector — Outbound WSS Client & Local Sovereign Gate.
Strictly follows RUKA-VI Chapter XIX (baris 55-205).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
import json
import time
from typing import Any, Callable

from ruka_companion.math.distributed import backoff_full_jitter
from ruka_companion.security.envelope import (
    Envelope,
    EnvelopeCodec,
    EnvelopeError,
)
from ruka_companion.security.redaction import redact_dict
from .credential import DeviceCredential


class LinkState(str, Enum):
    """Siklus hidup koneksi keluar (outbound link)."""

    DISCONNECTED = "DISCONNECTED"
    CONNECTING = "CONNECTING"
    AUTHENTICATING = "AUTHENTICATING"
    AUTHENTICATED = "AUTHENTICATED"
    RETRYING = "RETRYING"
    DEGRADED = "DEGRADED"


@dataclass
class LinkEvent:
    timestamp_ms: int
    kind: str
    detail: dict[str, Any]


@dataclass
class LinkPolicy:
    """Kebijakan lokal yang berdaulat atas pesan inbound."""

    allowed_inbound: frozenset[str] = field(
        default_factory=lambda: frozenset(
            {
                "task_delivery",  # pengiriman task (→ TaskQueue → policy check)
                "presence_ping",  # heartbeat server
                "sync_push",  # delta memori (→ SyncEngine, tetap diklasifikasi)
                "permission_request",  # permintaan izin yang butuh Bos
                "task_cancel",  # pembatalan task belum dieksekusi
            }
        )
    )


class CloudLink:
    """Connector outbound — transport disuntik agar bisa diuji."""

    def __init__(
        self,
        uri: str,
        credential: DeviceCredential,
        codec: EnvelopeCodec,
        policy: LinkPolicy | None = None,
        clock: Callable[[], int] | None = None,
    ) -> None:
        self.uri = uri
        self.credential = credential
        self.codec = codec
        self.policy = policy or LinkPolicy()
        self._now = clock or (lambda: int(time.time() * 1000))
        self.state = LinkState.DISCONNECTED
        self.events: list[LinkEvent] = []
        self._transport: Any = None
        self._attempt = 0
        self._on_message: Callable[[Envelope], None] | None = None
        self._auth_challenge: str | None = None

    def _log(self, kind: str, detail: dict[str, Any]) -> None:
        self.events.append(LinkEvent(self._now(), kind, redact_dict(detail)))

    def on_message(self, handler: Callable[[Envelope], None]) -> None:
        """Handler pesan inbound yang LOLOS kebijakan (task, sync, ...)."""
        self._on_message = handler

    # ------------------------------------------------------------ lifecycle
    async def connect(self, transport: Any) -> bool:
        """CONNECTING → challenge-response → AUTHENTICATED.
        Protokol (3 langkah, deterministik):
            L→C: hello {device_id, fingerprint, generation}
            C→L: challenge (nonce)
            L→C: response = HMAC(secret, nonce) + envelope pertama
        """
        self.state = LinkState.CONNECTING
        self._log("state_change", {"state": self.state.value})
        try:
            await transport.connect(self.uri)
        except Exception as exc:
            self._log("error", {"phase": "connect", "error": str(exc)})
            await self.schedule_retry()
            return False

        self._transport = transport
        self.state = LinkState.AUTHENTICATING
        self._log("state_change", {"state": self.state.value})

        hello = self.codec.seal(
            "link.hello",
            f"device:{self.credential.device_id}",
            {
                "device_id": self.credential.device_id,
                "fingerprint": self.credential.public_fingerprint(),
                "generation": self.credential.generation,
            },
        )
        await transport.send(json.dumps(hello.as_dict()))

        # tunggu challenge
        raw = await transport.recv()
        challenge_env = self.codec.verify_dict(json.loads(raw))
        if challenge_env.type != "link.challenge":
            await self.close()
            return False

        nonce = str(challenge_env.payload.get("nonce", ""))
        response = (
            self.credential.sign_challenge(nonce)
            if hasattr(self.credential, "sign_challenge")
            else self.credential.sign(nonce)
        )
        proof = self.codec.seal(
            "link.auth_response",
            f"device:{self.credential.device_id}",
            {"response": response, "device_id": self.credential.device_id},
            correlation_id=hello.correlation_id,
        )
        await transport.send(json.dumps(proof.as_dict()))

        ack_raw = await transport.recv()
        ack = self.codec.verify_dict(json.loads(ack_raw))
        if ack.type == "link.auth_ok":
            self.state = LinkState.AUTHENTICATED
            self._attempt = 0
            self._log("state_change", {"state": self.state.value})
            return True

        await self.close()
        return False

    async def schedule_retry(self) -> int:
        """Backoff full-jitter — mengembalikan delay ms berikutnya."""
        self.state = LinkState.RETRYING
        delay = backoff_full_jitter(self._attempt, base_ms=500, cap_ms=30_000)
        self._attempt += 1
        self._log(
            "state_change",
            {
                "state": self.state.value,
                "retry_in_ms": delay,
                "attempt": self._attempt,
            },
        )
        return delay

    async def send(self, type_: str, payload: dict[str, Any]) -> bool:
        """Kirim envelope bertanda (L→C). Gagal → state DEGRADED."""
        if self.state not in (LinkState.AUTHENTICATED, LinkState.DEGRADED):
            return False
        env = self.codec.seal(
            type_, f"device:{self.credential.device_id}", payload
        )
        try:
            await self._transport.send(json.dumps(env.as_dict()))
            self._log(
                "sent", {"type": type_, "correlation_id": env.correlation_id}
            )
            return True
        except Exception as exc:
            self._log("error", {"phase": "send", "error": str(exc)})
            self.state = LinkState.DEGRADED
            return False

    async def receive_once(self) -> Envelope | None:
        """Terima SATU pesan cloud→local; terapkan kebijakan LOCAL.
        Pesan di luar allowlist → REJECTED (dicatat, TIDAK dieksekusi).
        Pesan tak bertanda / replay → EnvelopeError → REJECTED.
        """
        try:
            raw = await self._transport.recv()
        except Exception as exc:
            self._log("error", {"phase": "recv", "error": str(exc)})
            self.state = LinkState.DEGRADED
            return None

        try:
            env = self.codec.verify_dict(json.loads(raw))
        except (EnvelopeError, json.JSONDecodeError) as exc:
            self._log("rejected", {"reason": f"envelope: {exc}"})
            return None

        if env.type not in self.policy.allowed_inbound:
            self._log(
                "rejected", {"type": env.type, "reason": "not in allowlist"}
            )
            return None

        self._log(
            "received", {"type": env.type, "correlation_id": env.correlation_id}
        )
        if self._on_message is not None:
            self._on_message(env)
        return env

    async def close(self) -> None:
        if self._transport is not None:
            try:
                await self._transport.close()
            except Exception:
                pass
        self._transport = None
        self.state = LinkState.DISCONNECTED
        self._log("state_change", {"state": self.state.value})

    def capability(self) -> dict[str, Any]:
        return {
            "layer": "remote-bridge",
            "kind": "cloud-link",
            "available": self.state == LinkState.AUTHENTICATED,
            "state": self.state.value,
            "attempts": self._attempt,
        }
