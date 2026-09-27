"""RUKA VI: Security Injection Guard — DATA != INSTRUCTIONS Quarantine.
Strictly follows RUKA-VI Chapter XXII (baris 100-165).
"""

from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any

# 10 Sinyal injeksi kanonik (Vol V + VI)
SIGNALS: list[tuple[str, tuple[re.Pattern[str], ...], float]] = [
    (
        "instruction_override",
        (
            re.compile(
                r"ignore\s+(?:all\s+)?(?:previous|prior)\s+instructions?",
                re.IGNORECASE,
            ),
            re.compile(
                r"abaikan\s+(?:semua\s+)?instruksi\s+(?:sebelumnya|awal)",
                re.IGNORECASE,
            ),
            re.compile(
                r"disregard\s+(?:all\s+)?(?:previous|prior)", re.IGNORECASE
            ),
        ),
        0.8,
    ),
    (
        "system_impersonation",
        (
            re.compile(r"\bSYSTEM\s*:", re.IGNORECASE),
            re.compile(r"\[SYSTEM\]", re.IGNORECASE),
            re.compile(r"<\|im_start\|>system", re.IGNORECASE),
            re.compile(r"<\|system\|>", re.IGNORECASE),
        ),
        0.7,
    ),
    (
        "role_play_jailbreak",
        (
            re.compile(
                r"you\s+are\s+now\s+(?:an?\s+)?(?:unfiltered|unrestricted|DAN)",
                re.IGNORECASE,
            ),
            re.compile(
                r"kamu\s+sekarang\s+adalah\s+(?:mode\s+bebas|tanpa\s+aturan)",
                re.IGNORECASE,
            ),
            re.compile(r"\bjailbreak\b", re.IGNORECASE),
        ),
        0.6,
    ),
    (
        "credential_leak",
        (
            re.compile(
                r"(?:reveal|print|show|dump)\s+(?:all\s+)?(?:api[_-]?keys?|secrets?|tokens?|passwords?)",
                re.IGNORECASE,
            ),
            re.compile(
                r"(?:bocorkan|tampilkan|cetak)\s+(?:semua\s+)?(?:kunci|token|password|secret)",
                re.IGNORECASE,
            ),
        ),
        0.7,
    ),
    (
        "exfiltration",
        (
            re.compile(r"(?:curl|wget|fetch|post)\s+https?://", re.IGNORECASE),
            re.compile(r"(?:send|kirim)\s+(?:to|ke)\s+https?://", re.IGNORECASE),
        ),
        0.5,
    ),
    (
        "privilege_escalation",
        (
            re.compile(r"\bsudo\s+su\b", re.IGNORECASE),
            re.compile(
                r"(?:grant|give)\s+(?:all\s+)?permissions?", re.IGNORECASE
            ),
            re.compile(r"mode\s+administrator\s+penuh", re.IGNORECASE),
        ),
        0.6,
    ),
    (
        "markdown_exfil_link",
        (re.compile(r"!\[.*?\]\(https?://[^\s\)]+\)", re.IGNORECASE),),
        0.4,
    ),
    (
        "tool_call_mimicry",
        (
            re.compile(r"<tool_call>", re.IGNORECASE),
            re.compile(r"\"function\":\s*\"(?:execute|run|read)\"", re.IGNORECASE),
        ),
        0.5,
    ),
    (
        "delimiter_injection",
        (
            re.compile(r"```json\s*\{\s*\"action\"", re.IGNORECASE),
            re.compile(r"---END OF INSTRUCTIONS---", re.IGNORECASE),
        ),
        0.5,
    ),
    (
        "prompt_leaking",
        (
            re.compile(
                r"(?:what\s+is\s+your|repeat\s+the)\s+system\s+prompt",
                re.IGNORECASE,
            ),
            re.compile(r"apa\s+isi\s+prompt\s+sistem\s+kamu", re.IGNORECASE),
        ),
        0.4,
    ),
]


@dataclass(frozen=True)
class InjectionVerdict:
    quarantine: bool
    score: float
    signals: tuple[str, ...]
    matched_fragments: tuple[str, ...]
    channel: str = "remote"


class RemoteInjectionGuard:
    """Guard kanal remote — QUARANTINE ber-skor, bukan blok buta.
    Skor = max(sinyal) + 0.15·(n_sinyal−1) (multipart attack naik).
    Ambang quarantine 0.25 (Vol V definitive — warisan terkalibrasi).
    """

    THRESHOLD: float = 0.25

    def __init__(
        self,
        channel: str = "remote",
        extra_patterns: tuple[
            tuple[str, tuple[re.Pattern[str], ...], float], ...
        ] = (),
    ) -> None:
        self.signals = list(SIGNALS) + list(extra_patterns)
        self.channel = channel

    def inspect(self, text: str, source: str = "telegram") -> InjectionVerdict:
        """Periksa teks eksternal → vonis. Teks TIDAK pernah 'dipercaya' karena
        lolos inspeksi — hanya 'tidak dikarantina SEMENTERA ini'."""
        if not text or not text.strip():
            return InjectionVerdict(False, 0.0, (), (), self.channel)
        hits: list[str] = []
        frags: list[str] = []
        for name, patterns, weight in self.signals:
            for pat in patterns:
                m = pat.search(text)
                if m:
                    hits.append(name)
                    frags.append(m.group(0)[:60])
                    break
        if not hits:
            return InjectionVerdict(False, 0.0, (), (), self.channel)
        weights = [w for n, _p, w in self.signals if n in hits]
        score = max(weights) + 0.15 * (len(set(hits)) - 1)
        return InjectionVerdict(
            quarantine=score >= self.THRESHOLD,
            score=round(min(score, 1.0), 3),
            signals=tuple(sorted(set(hits))),
            matched_fragments=tuple(frags),
            channel=self.channel,
        )

    def inspect_tool_output(self, output: str) -> InjectionVerdict:
        """Output alat = DATA — 'SYSTEM:' menyaru di dalamnya = karantina."""
        return self.inspect(output, source="tool-output")
