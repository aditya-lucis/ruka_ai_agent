# -*- coding: utf-8 -*-
"""Structured tracing – log bukan print, trace bukan teks.
JSONL: satu request = satu baris; redaksi PII; retensi terbatas;
sampling opsional untuk lingkungan produksi bervolume tinggi.
v0.3.1 (Patch 1.1): PII_PATTERNS mencakup Google API keys & Bearer tokens.
"""
from __future__ import annotations
import json
import logging
import re
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

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


@dataclass
class TraceEvent:
    at: float                            # monotonic ms relatif mulai
    layer: str                           # "orchestrator" | "tool" | ...
    kind: str                            # "llm_call" | "tool_result" | ...
    payload: dict = field(default_factory=dict)


class Trace:
    """Satu request. Diisi lapisan; ditutup sekali."""
    def __init__(self, goal: str, session_id: str) -> None:
        self.trace_id = uuid.uuid4().hex[:12]
        self.session_id = session_id
        self.goal = redact(goal)
        self._t0 = time.monotonic()
        self._events: list[TraceEvent] = []
        self.frozen: dict | None = None

    def event(self, layer: str, kind: str, **payload) -> None:
        if self.frozen is not None:
            return                         # tertutup: tolak diam-diam
        safe = {k: (redact(v) if isinstance(v, str) else v)
                for k, v in payload.items()}
        self._events.append(TraceEvent(
            at=round((time.monotonic() - self._t0) * 1000, 1),
            layer=layer, kind=kind, payload=safe))

    def close(self, final_status: str, summary: dict) -> dict:
        """Bekukan jadi dokumen; idempotent."""
        if self.frozen is not None:
            return self.frozen
        self.frozen = {
            "trace_id": self.trace_id,
            "session_id": self.session_id,
            "ts": datetime.now(timezone.utc).isoformat(),
            "goal": self.goal,
            "final_status": final_status,
            "summary": summary,
            "n_events": len(self._events),
            "events": [{"at": e.at, "layer": e.layer,
                        "kind": e.kind, **e.payload}
                       for e in self._events],
        }
        return self.frozen


class TraceWriter:
    """Tulis JSONL + retensi + sampling produksi."""
    def __init__(self, log_dir: Path, retention_days: int = 14,
                 sample_rate: float = 1.0, seed: int = 7) -> None:
        self._dir = log_dir
        self._retention = retention_days
        self._sample = sample_rate
        self._counter = 0
        self._dir.mkdir(parents=True, exist_ok=True)

    def write(self, trace: Trace, final_status: str,
              summary: dict) -> str | None:
        self._counter += 1
        if self._sample < 1.0 and (self._counter % int(1 / self._sample)):
            return None                      # sampling deterministik
        doc = trace.close(final_status, summary)
        day = datetime.now(timezone.utc).strftime("%Y%m%d")
        path = self._dir / f"ruka-{day}.jsonl"
        with path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(doc, ensure_ascii=False) + "\n")
        self._rotate()
        return str(path)

    def _rotate(self) -> None:
        cutoff = time.time() - self._retention * 86400
        for f in self._dir.glob("ruka-*.jsonl"):
            if f.stat().st_mtime < cutoff:
                f.unlink()


# ---- log terstruktur: print yang belajar etika ----
class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        base = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage()
        }
        if record.exc_info:
            base["exc"] = self.formatException(record.exc_info)[:2000]
        return json.dumps(base, ensure_ascii=False)


def setup_json_logging(level: int = logging.INFO) -> None:
    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())
    root = logging.getLogger()
    root.handlers[:] = [handler]
    root.setLevel(level)
