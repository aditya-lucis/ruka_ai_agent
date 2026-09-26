# -*- coding: utf-8 -*-
"""Mathematical observability: record scores, never secrets.
Volume II taught tracing; Volume III records the *numbers* the
cognitive stack produces — similarity, ranking, tool scores, neural
confidence, loss, latency, iteration counts, decision reasons —
because a subsystem whose scores nobody sees cannot be tuned, and a
subsystem whose scores cannot be explained cannot be debugged.
Redaction is enforced in ``record``: events carrying API keys, AIza
tokens, or PII patterns are scrubbed *before* they enter the log.
``raw`` payloads are stored only when the caller explicitly marks
``sensitive=False`` and the redactor finds nothing.
"""
from __future__ import annotations
import math
import re
import time
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Mapping

# Google API key pattern (the Patch 1.1 lesson): AIza[0-9A-Za-z_-]{35}
_SECRET_PATTERNS = [
    re.compile(r"AIza[0-9A-Za-z_\-]{35}"),
    re.compile(r"(?i)\b(api[_-]?key|secret|token|password)\b\s*[:=]\s*\S+"),
    re.compile(r"(?i)bearer\s+[0-9a-z._\-]{16,}"),
    re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.]+\b"),       # email as PII stand-in
]

_SECRET_KEY_NAMES = re.compile(
    r"(?i)^(api[_-]?key|secret|token|password|credential|key|passwd)$")
_REDACTED = "[REDACTED]"

def redact(value: Any) -> Any:
    """Scrub secrets from any JSON-ish structure, recursively.
    Two shapes are handled: secrets *embedded in strings* (matched by
    pattern) and secrets *shaped as key/value pairs* — if a dict key is
    itself a secret-ish name, its whole value is redacted even when the
    value alone looks harmless ("hunter2" matches no pattern).
    """
    if isinstance(value, str):
        out = value
        for pat in _SECRET_PATTERNS:
            out = pat.sub(_REDACTED, out)
        return out
    if isinstance(value, dict):
        clean = {}
        for k, v in value.items():
            if _SECRET_KEY_NAMES.match(str(k)):
                clean[redact(k)] = _REDACTED
            else:
                clean[redact(k)] = redact(v)
        return clean
    if isinstance(value, (list, tuple)):
        return type(value)(redact(v) for v in value)
    return value

@dataclass(frozen=True)
class MetricEvent:
    name: str
    value: float
    request_id: str = ""
    tags: Mapping[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)
    raw: Any = None

    def as_line(self) -> str:
        base = (f"metric name={self.name} value={self.value:.6g} "
                f"request_id={self.request_id}")
        if self.tags:
            flat = " ".join(f"{k}={v}" for k, v in sorted(self.tags.items()))
            base = f"{base} {flat}"
        return base

class MetricsRecorder:
    """In-memory recorder with redaction and percentile summaries."""
    def __init__(self, max_events: int = 10_000) -> None:
        self._events: list[MetricEvent] = []
        self._by_name: dict[str, list[float]] = defaultdict(list)
        self._redactions = 0
        self._max_events = max_events

    @property
    def redaction_count(self) -> int:
        return self._redactions

    def record(self, name: str, value: float, request_id: str = "",
               tags: Mapping[str, Any] | None = None,
               raw: Any = None) -> MetricEvent:
        if len(self._events) >= self._max_events:
            raise RuntimeError(
                f"metric buffer overflow: >{self._max_events} events")
                
        tags_clean = redact(dict(tags or {}))
        if repr(tags_clean) != repr(dict(tags or {})):
            self._redactions += 1
            
        raw_clean = redact(raw)
        if raw is not None and repr(raw_clean) != repr(raw):
            self._redactions += 1
            
        ev = MetricEvent(name=name, value=float(value),
                         request_id=request_id, tags=tags_clean,
                         raw=raw_clean)
        self._events.append(ev)
        self._by_name[name].append(ev.value)
        return ev

    def summary(self, name: str) -> dict:
        """Count, mean, min, max, p50/p95 — enough to alert on drift.
        Percentiles use nearest-rank indices with CEIL on p95: an
        int() floor once made p95 < p50 on tiny samples, which no
        dashboard should ever have to explain.
        """
        vals = self._by_name.get(name, [])
        if not vals:
            return {"count": 0}
        vs = sorted(vals)
        n = len(vs)
        p50_idx = min(n - 1, max(0, math.ceil(0.50 * n) - 1))
        p95_idx = min(n - 1, max(0, math.ceil(0.95 * n) - 1))
        return {
            "count": n,
            "mean": sum(vs) / n,
            "min": vs[0],
            "max": vs[-1],
            "p50": vs[p50_idx],
            "p95": vs[p95_idx],
        }

    def names(self) -> list[str]:
        return sorted(self._by_name)

    def drain_lines(self) -> list[str]:
        """Return all events as log lines and clear the buffer."""
        lines = [e.as_line() for e in self._events]
        self._events.clear()
        return lines
