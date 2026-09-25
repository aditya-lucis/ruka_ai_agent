# -*- coding: utf-8 -*-
"""Telemetry tracing v0.3.1 — redaksi diperkuat.
Patch 1.1: PII_PATTERNS vol II tidak mencakup POLA KUNCI GOOGLE.
Kunci Gemini API berbentuk `AIza...` (39 char). Tanpa pola ini, pesan
error / debug yang memuat kunci akan bocor ke trace. Ditambah juga
Bearer token dan header Authorization.
"""
from __future__ import annotations
import re

PII_PATTERNS = [
    re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+"),                   # email
    re.compile(r"\b\d{16,19}\b"),                             # kartu
    re.compile(r"\b(?:sk|pk)-[A-Za-z0-9]{16,}\b"),            # kunci umum
    re.compile(r"\bAIza[0-9A-Za-z_\-]{30,}\b"),               # kunci Gemini
    re.compile(r"(?i)bearer\s+[A-Za-z0-9._\-]{20,}"),         # bearer
]

def redact(text: str) -> str:
    out = text
    for pat in PII_PATTERNS:
        out = pat.sub("[REDAKTED]", out)
    return out
