"""RUKA VI: Security Redaction — Canonical sensitive pattern masking.
Strictly follows RUKA-VI Chapter XXII (baris 20-90).
"""

from __future__ import annotations

import re
from typing import Any

# Telegram bot token: <bot_id>:<secret> 35-40 char
_TGTOKEN = re.compile(r"\b\d{8,10}:[A-Za-z0-9_\-]{34,40}\b")
# device secret hex-64 (yang di-config cloud/local)
_DEVICE_SECRET = re.compile(r"\b[0-9a-f]{64}\b", re.IGNORECASE)
# umum: sk-..., ghp_..., password=
_GENERIC = re.compile(r"\b(?:sk-[A-Za-z0-9]{20,}|ghp_[A-Za-z0-9]{30,})\b")
# AIza (Google API keys 30+ char)
_AIZA = re.compile(r"\bAIza[0-9A-Za-z_\-]{30,}\b")
# Bearer tokens
_BEARER = re.compile(r"Bearer\s+[A-Za-z0-9_\-\.]{20,}", re.IGNORECASE)

_PATTERNS = [_TGTOKEN, _DEVICE_SECRET, _GENERIC, _AIZA, _BEARER]

# pasangan kunci-sensitif di dict
SENSITIVE_KEY_RE = re.compile(
    r"(api[_-]?key|secret|token|password|passwd|credential|private[_-]?key|verify_token)",
    re.IGNORECASE,
)


_PLACEHOLDER = "<redacted>"


def redact(text: str) -> str:
    """Redaksi string — idempotent (placeholder tak dobel-redaksi)."""
    if not text:
        return text
    out = text
    for pat in _PATTERNS:
        out = pat.sub(_PLACEHOLDER, out)
    return out


def is_sensitive_key(key: str) -> bool:
    return bool(SENSITIVE_KEY_RE.search(key))


def redact_dict(d: dict[str, Any], _depth: int = 0) -> dict[str, Any]:
    """Redaksi rekursif dict: (a) pola dalam STRING, (b) VALUE dengan kunci
    sensitif → '<redacted>' penuh. Max depth 6 (anti loop JSON aneh)."""
    if _depth > 6:
        return {"<truncated>": True}
    out: dict[str, Any] = {}
    for k, v in d.items():
        if isinstance(v, str):
            out[k] = _PLACEHOLDER if is_sensitive_key(str(k)) else redact(v)
        elif isinstance(v, dict):
            out[k] = (
                _PLACEHOLDER
                if is_sensitive_key(str(k))
                else redact_dict(v, _depth + 1)
            )
        elif isinstance(v, list):
            out[k] = (
                _PLACEHOLDER
                if is_sensitive_key(str(k))
                else [
                    (
                        redact(x)
                        if isinstance(x, str)
                        else redact_dict(x, _depth + 1)
                        if isinstance(x, dict)
                        else x
                    )
                    for x in v[:50]
                ]
            )
        else:
            out[k] = _PLACEHOLDER if is_sensitive_key(str(k)) else v
    return out
