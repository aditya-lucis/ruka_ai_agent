# -*- coding: utf-8 -*-
"""Secret Scrubber for Voice Safety (FR-VO-14).

Penyaring kata rahasia yang memastikan 100% token, API key, kata sandi,
JWT, dan kunci privat tidak pernah diucapkan oleh modul suara Ruka.
"""
from __future__ import annotations

import re


REDACTION_TAG = "[KODE_RAHASIA]"

PATTERNS = [
    # RSA / Private Key blocks
    (re.compile(r"-----BEGIN[ A-Z_-]*PRIVATE KEY-----[\s\S]*?-----END[ A-Z_-]*PRIVATE KEY-----", re.IGNORECASE), "[KUNCI_PRIVAT_TERSEMBUNYI]"),
    # JWT tokens (Header.Payload.Signature)
    (re.compile(r"eyJ[A-Za-z0-9_-]{10,}\.eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}"), "[TOKEN_JWT_TERSEMBUNYI]"),
    # OpenAI / Anthropic / Generic sk- keys
    (re.compile(r"\b(?:sk|ant|pk)-[A-Za-z0-9_-]{16,}\b"), REDACTION_TAG),
    # GitHub personal access tokens
    (re.compile(r"\b(?:ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9_]{20,}\b"), REDACTION_TAG),
    # Google API Keys
    (re.compile(r"\bAIza[0-9A-Za-z-_]{35}\b"), REDACTION_TAG),
    # AWS Access Keys
    (re.compile(r"\bAKIA[0-9A-Z]{16}\b"), REDACTION_TAG),
    # Database URIs with credentials
    (re.compile(r"\b(?:postgres|postgresql|mysql|mongodb|redis|sqlite):\/\/[^\s]+:[^\s]+@[^\s]+\b", re.IGNORECASE), "[KONEKSI_DATABASE_TERSEMBUNYI]"),
    # Bearer authorization header
    (re.compile(r"\bBearer\s+[A-Za-z0-9._~+/-]{15,}={0,2}\b", re.IGNORECASE), "Bearer [TOKEN_TERSEMBUNYI]"),
    # Explicit key-value secrets (password=..., secret: ..., token=...)
    (re.compile(r"(?i)\b(password|passwd|secret|api_key|apikey|access_token|auth_token)\s*[:=]\s*['\"]?([^\s,;'\"]{4,})['\"]?"), r"\1: [KATA_SANDI_TERSEMBUNYI]"),
]


class SecretScrubber:
    """Penyaring rahasia deterministik sebelum teks dikirim ke TTS engine."""

    def __init__(self) -> None:
        self.patterns = PATTERNS

    def scrub(self, text: str) -> str:
        """Menghapus seluruh nilai sensitif dan menggantinya dengan penanda ramah ucapan."""
        if not text:
            return ""

        scrubbed = text
        for pattern, replacement in self.patterns:
            if callable(replacement):
                scrubbed = pattern.sub(replacement, scrubbed)
            elif "\\" in replacement:
                # regex backreference handling
                try:
                    scrubbed = pattern.sub(replacement, scrubbed)
                except Exception:
                    scrubbed = pattern.sub(REDACTION_TAG, scrubbed)
            else:
                scrubbed = pattern.sub(replacement, scrubbed)

        # Cek manual untuk token hex acak sangat panjang (>= 32 char)
        scrubbed = re.sub(r"\b[a-f0-9]{32,64}\b", REDACTION_TAG, scrubbed)

        return scrubbed
