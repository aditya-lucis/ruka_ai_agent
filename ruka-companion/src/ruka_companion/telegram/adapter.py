"""RUKA VI: Telegram Remote Presence — Bot API Subset via httpx.
Strictly follows RUKA-VI Chapter XVIII (baris 55-300).
"""

from __future__ import annotations

from dataclasses import dataclass, field
import hmac as _hmac
import time
from typing import Any, Awaitable, Callable

import httpx

from ruka_companion.security.injection import (
    InjectionVerdict,
    RemoteInjectionGuard,
)


@dataclass
class TelegramConfig:
    """Konfigurasi Telegram adapter."""

    bot_token: str
    api_base: str = "https://api.telegram.org"
    poll_timeout_s: int = 25
    allowed_chat_ids: set[int] = field(default_factory=set)
    allowed_user_ids: set[int] = field(default_factory=set)
    webhook_secret: str = ""

    def __post_init__(self) -> None:
        if not self.bot_token or len(self.bot_token) < 10:
            raise ValueError("bot token wajib (format <id>:<secret>)")


@dataclass(frozen=True)
class Update:
    """Proyeksi Update resmi — hanya field yang Ruka pakai (subset stabil)."""

    update_id: int
    chat_id: int | None = None
    user_id: int | None = None
    username: str | None = None
    text: str | None = None
    is_command: bool = False
    command: str | None = None
    raw: dict[str, Any] = field(default_factory=dict)


def parse_update(raw: dict[str, Any]) -> Update:
    """Update JSON → proyeksi. Abaikan update non-message (callback, edited)."""
    update_id = int(raw.get("update_id", 0))
    msg = raw.get("message") or raw.get("edited_message") or {}
    if not msg:
        return Update(update_id=update_id, raw=raw)
    chat = msg.get("chat", {})
    user = msg.get("from", {})
    text = msg.get("text", "")
    entities = msg.get("entities", [])
    is_command = bool(
        text.startswith("/")
        and any(e.get("type") == "bot_command" for e in entities)
    )
    command = text.split()[0].lstrip("/").split("@")[0] if is_command else None

    return Update(
        update_id=update_id,
        chat_id=int(chat.get("id", 0)) or None,
        user_id=int(user.get("id", 0)) or None,
        username=user.get("username"),
        text=text,
        is_command=is_command,
        command=command,
        raw=raw,
    )


class TelegramClient:
    """Klien Bot API subset — transport disuntik (httpx.AsyncClient atau Mock).
    Semua request POST JSON sesuai docs; getUpdates memakai offset+timeout.
    """

    def __init__(
        self,
        config: TelegramConfig,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self.config = config
        self._transport = transport
        self._client: httpx.AsyncClient | None = None

    async def _ac(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = (
                httpx.AsyncClient(transport=self._transport, timeout=30.0)
                if self._transport is not None
                else httpx.AsyncClient(timeout=30.0)
            )
        return self._client

    async def close(self) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    async def _call(
        self, method: str, payload: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        url = f"{self.config.api_base}/bot{self.config.bot_token}/{method}"
        client = await self._ac()
        resp = await client.post(url, json=payload or {})
        data = resp.json()
        if not data.get("ok"):
            raise RuntimeError(
                f"Bot API {method} gagal: {data.get('description')}"
            )
        return data["result"]

    # ------------------------------------------------------------ subset API
    async def get_me(self) -> dict[str, Any]:
        return await self._call("getMe")

    async def get_updates(
        self, offset: int | None = None, timeout_s: int | None = None
    ) -> list[dict[str, Any]]:
        payload: dict[str, Any] = {
            "timeout": (
                timeout_s if timeout_s is not None else self.config.poll_timeout_s
            )
        }
        if offset is not None:
            payload["offset"] = offset
        return await self._call("getUpdates", payload)

    async def send_message(self, chat_id: int, text: str) -> dict[str, Any]:
        return await self._call(
            "sendMessage", {"chat_id": chat_id, "text": text}
        )

    async def send_chat_action(
        self, chat_id: int, action: str = "typing"
    ) -> dict[str, Any]:
        return await self._call(
            "sendChatAction", {"chat_id": chat_id, "action": action}
        )

    async def get_file(self, file_id: str) -> dict[str, Any]:
        return await self._call("getFile", {"file_id": file_id})

    async def set_webhook(self, url: str, secret_token: str) -> dict[str, Any]:
        return await self._call(
            "setWebhook", {"url": url, "secret_token": secret_token}
        )

    async def delete_webhook(self) -> dict[str, Any]:
        return await self._call(
            "deleteWebhook", {"drop_pending_updates": False}
        )


class WebhookVerifier:
    """Verifikasi header rahasia webhook — X-Telegram-Bot-Api-Secret-Token.
    Docs (verified): Telegram menaruh secret_token ini pada SETIAP request
    webhook. Tanpa verifikasi ini, siapa pun yang tahu URL bisa mengirim
    update palsu.
    """

    def __init__(self, secret: str) -> None:
        if not secret or len(secret) < 16:
            raise ValueError("webhook secret minimal 16 karakter (docs: 1-256)")
        self.secret = secret

    def verify(self, received: str | None) -> bool:
        if not received:
            return False
        return _hmac.compare_digest(received, self.secret)


class RateLimiter:
    """Token bucket per chat — margin teknik (bukan kontrak API docs).
    Docs resmi hanya menyatakan broadcast 30/s; limit per-chat 20/mnt
    adalah community-knowledge → kami menyetel margin sendiri + bisa
    dikonfigurasi. Jangan jual angka ini sebagai spesifikasi Telegram.
    """

    def __init__(self, per_chat_per_min: int = 20) -> None:
        if per_chat_per_min <= 0:
            raise ValueError("> 0")
        self.per_chat = per_chat_per_min
        self._hits: dict[int, list[int]] = {}

    def allow(self, chat_id: int, now_ms: int | None = None) -> bool:
        now = now_ms if now_ms is not None else int(time.time() * 1000)
        window = [t for t in self._hits.get(chat_id, []) if now - t < 60_000]
        if len(window) >= self.per_chat:
            self._hits[chat_id] = window
            return False
        window.append(now)
        self._hits[chat_id] = window
        return True


class MessageRouter:
    """Router update → aksi Ruka (keputusan SELALU lokal, jangan di cloud-only).
    Alur aman (dipakai di cloud runtime):
        update → parse → allowlist? → injection guard → handler
    Handler = callback lokal: (update) → teks balasan / task proposal.
    """

    def __init__(
        self,
        client: TelegramClient,
        config: TelegramConfig,
        guard: RemoteInjectionGuard | None = None,
        rate_limiter: RateLimiter | None = None,
    ) -> None:
        self.client = client
        self.config = config
        self.guard = guard or RemoteInjectionGuard()
        self.rate_limiter = rate_limiter or RateLimiter()
        self.handlers: dict[str, Callable[[Update], Awaitable[str]]] = {}

    def register_command(
        self, command: str, handler: Callable[[Update], Awaitable[str]]
    ) -> None:
        self.handlers[command.lstrip("/")] = handler

    async def handle_update(self, raw: dict[str, Any]) -> dict[str, Any]:
        update = parse_update(raw)

        # 1. Allowlist pengguna
        if (
            self.config.allowed_user_ids
            and update.user_id not in self.config.allowed_user_ids
        ):
            return {
                "action": "BLOCKED_USER",
                "update_id": update.update_id,
                "user_id": update.user_id,
            }

        # 2. Rate limit per chat
        if update.chat_id is not None and not self.rate_limiter.allow(
            update.chat_id
        ):
            return {"action": "RATE_LIMITED", "update_id": update.update_id}

        # 3. DATA != INSTRUCTIONS (Injection quarantine)
        verdict: InjectionVerdict = self.guard.inspect(update.text or "")
        if verdict.quarantine:
            return {
                "action": "QUARANTINED",
                "signals": list(verdict.signals),
                "score": verdict.score,
                "update_id": update.update_id,
            }

        # 4. Dispatch command / fallback
        if update.is_command and update.command in self.handlers:
            reply = await self.handlers[update.command](update)
            if update.chat_id:
                await self.client.send_message(update.chat_id, reply)
            return {
                "action": "HANDLED",
                "command": update.command,
                "update_id": update.update_id,
            }

        return {
            "action": "FALLBACK_CHAT",
            "update_id": update.update_id,
            "text_preview": (update.text or "")[:80],
        }


class PollingLoop:
    """Loop getUpdates long-polling — offset naik (docs: offset = update_id+1)."""

    def __init__(self, router: MessageRouter) -> None:
        self.router = router
        self.offset: int | None = None
        self.running = False

    async def poll_once(self) -> list[dict[str, Any]]:
        updates = await self.router.client.get_updates(offset=self.offset)
        results = []
        for raw in updates:
            results.append(await self.router.handle_update(raw))
            self.offset = int(raw["update_id"]) + 1
        return results
