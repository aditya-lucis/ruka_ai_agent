"""RUKA VI: Security Envelope — Signed JSON Envelopes & Anti-Replay Codec.
Strictly follows RUKA-VI Chapter XIX (baris 58-145).
"""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import hmac
import json
import time
from typing import Any
import uuid


class EnvelopeError(Exception):
    pass


def sha256_hex(data: str | bytes) -> str:
    b = data.encode() if isinstance(data, str) else data
    return hashlib.sha256(b).hexdigest()


@dataclass
class Envelope:
    """Pesan dua arah ber-meterai HMAC-SHA256."""

    type: str
    correlation_id: str
    nonce: str
    timestamp_ms: int
    sender: str
    payload: dict[str, Any]
    signature: str = ""

    def canonical(self) -> str:
        payload_str = json.dumps(self.payload, sort_keys=True, separators=(",", ":"))
        return f"{self.type}|{self.correlation_id}|{self.nonce}|{self.timestamp_ms}|{self.sender}|{payload_str}"

    def as_dict(self) -> dict[str, Any]:
        return {
            "type": self.type,
            "correlation_id": self.correlation_id,
            "nonce": self.nonce,
            "timestamp_ms": self.timestamp_ms,
            "sender": self.sender,
            "payload": self.payload,
            "signature": self.signature,
        }
    to_dict = as_dict



    @staticmethod
    def from_dict(d: dict[str, Any]) -> "Envelope":
        required = {
            "type",
            "correlation_id",
            "nonce",
            "timestamp_ms",
            "sender",
            "payload",
            "signature",
        }
        missing = required - set(d)
        if missing:
            raise EnvelopeError(f"envelope bolong: {sorted(missing)}")
        return Envelope(
            type=str(d["type"]),
            correlation_id=str(d["correlation_id"]),
            nonce=str(d["nonce"]),
            timestamp_ms=int(d["timestamp_ms"]),
            sender=str(d["sender"]),
            payload=dict(d["payload"]),
            signature=str(d["signature"]),
        )


@dataclass
class EnvelopeCodec:
    """Encode/decode + sign/verify + jendela replay.
    window_ms default 120_000 (2 menit) — sinkron dengan TTL task default.
    """

    secret: bytes
    window_ms: int = 120_000
    _seen: dict[str, int] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.secret or len(self.secret) < 16:
            raise EnvelopeError("kunci envelope minimal 16 byte")

    # ------------------------------------------------------------------- sign
    def sign(self, env: Envelope) -> Envelope:
        env.signature = hmac.new(
            self.secret, env.canonical().encode(), hashlib.sha256
        ).hexdigest()
        return env

    def seal(
        self,
        type_: str,
        sender: str,
        payload: dict[str, Any],
        correlation_id: str | None = None,
        timestamp_ms: int | None = None,
        nonce: str | None = None,
    ) -> Envelope:
        """Buat envelope baru bertanda tangan."""
        env = Envelope(
            type=type_,
            correlation_id=correlation_id or uuid.uuid4().hex[:16],
            nonce=nonce or uuid.uuid4().hex,
            timestamp_ms=(
                timestamp_ms
                if timestamp_ms is not None
                else int(time.time() * 1000)
            ),
            sender=sender,
            payload=payload,
        )
        return self.sign(env)

    def verify(self, env: Envelope, now_ms: int | None = None) -> None:
        """Raise EnvelopeError bila PALSU/REPLAY/STALE. Idempotent terhadap
        verifikasi signature; nonce dicatat SAAT valid."""
        now = now_ms if now_ms is not None else int(time.time() * 1000)
        # 1. jendela waktu
        if abs(now - env.timestamp_ms) > self.window_ms:
            raise EnvelopeError(
                f"timestamp {env.timestamp_ms} di luar jendela ±{self.window_ms}ms"
            )
        # 2. signature (bandingkan konstan-waktu)
        expected = hmac.new(
            self.secret, env.canonical().encode(), hashlib.sha256
        ).hexdigest()
        if not hmac.compare_digest(expected, env.signature):
            raise EnvelopeError("signature TIDAK valid — pemalsuan atau kunci salah")
        # 3. replay nonce
        if env.nonce in self._seen:
            raise EnvelopeError(f"nonce {env.nonce[:8]}… sudah dipakai — REPLAY")

        # evict nonce luar jendela 2x
        self._seen[env.nonce] = now
        expired = [n for n, t in self._seen.items() if now - t > 2 * self.window_ms]
        for n in expired:
            self._seen.pop(n, None)

    def verify_dict(self, d: dict[str, Any], now_ms: int | None = None) -> Envelope:
        env = Envelope.from_dict(d)
        self.verify(env, now_ms)
        return env

