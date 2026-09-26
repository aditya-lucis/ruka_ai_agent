"""Perception Metrics, Redaction, and Observability — Ruka Volume IV.

Implements Listings 15.1, 15.2, and 15.3 from RUKA-IV Part XV.

Telemetri persepsi mengikuti tata kelola Vol III dan menambah aturan media:
bytes gambar/audio TIDAK PERNAH masuk log — cukup mime, ukuran, fingerprint
hash, dan trace.
"""

from __future__ import annotations

import hashlib
import math
import re
import time
from collections import defaultdict


# ---------------------------------------------------------------------------
# Listing 15.3 — Redaksi + fingerprint (Part XV)
# ---------------------------------------------------------------------------

_SECRET_PATTERNS = [
    re.compile(r"AIza[A-Za-z0-9_-]{35}"),               # Google API key
    re.compile(r"sk-[A-Za-z0-9]{20,}"),                  # OpenAI key
    re.compile(r"[A-Za-z0-9+/]{40,}={0,2}"),             # long base64 blobs
]


def redact(text: str) -> str:
    """Redaksi secret dalam teks bebas. Konsisten dengan Vol III."""
    out = text
    for pat in _SECRET_PATTERNS:
        out = pat.sub("[REDACTED]", out)
    # Tangani nilai setelah label (label=VALUE) yang lolos pola pertama
    out = re.sub(
        r"(?i)(api[_-]?key|token|secret|password)"
        r"(\s*[=:]\s*)\S+",
        r"\1\2[REDACTED]",
        out,
    )
    return out


def content_fingerprint(data: bytes) -> str:
    """Sidik jari konten: sha256[:16].

    Cukup untuk korelasi log TANPA menyimpan isi.
    Tabrakan 16-hex jarang dan hanya berdampak log yang membingungkan —
    risiko yang dinyatakan jujur, bukan disembunyikan.
    """
    return hashlib.sha256(data).hexdigest()[:16]


# ---------------------------------------------------------------------------
# Listings 15.1 & 15.2 — PerceptionMetrics (latensi, event, persentil)
# ---------------------------------------------------------------------------

class PerceptionMetrics:
    """Perekam latensi per tahap + event terstruktur."""

    def __init__(self) -> None:
        self._stages: dict[str, list[float]] = defaultdict(list)
        self.events: list[dict] = []

    def stage(self, name: str, fn, *args, **kwargs):
        """Bungkus satu tahap: catat durasi + hasil/exception (tanpa isi sensitif).

        Return nilai fn.
        """
        t0 = time.perf_counter()
        try:
            result = fn(*args, **kwargs)
        except Exception as exc:
            self._stages[name].append((time.perf_counter() - t0) * 1000.0)
            self.events.append({
                "stage": name,
                "ok": False,
                "error": type(exc).__name__,
            })
            raise
        self._stages[name].append((time.perf_counter() - t0) * 1000.0)
        return result

    def record_stage(self, name: str, ms: float) -> None:
        """Catat latensi tahap dari luar (adapter async dsb.)."""
        self._stages[name].append(float(ms))

    def media_event(
        self,
        stage: str,
        mime: str,
        size: int,
        fingerprint: str,
        trace_id: str,
        ok: bool = True,
    ) -> None:
        """Event media: tanpa bytes, tanpa transkrip."""
        self.events.append({
            "stage": stage,
            "mime": mime,
            "bytes": size,
            "fingerprint": fingerprint,
            "trace": trace_id,
            "ok": ok,
        })

    def state_transition(self, prev: str, next_: str, cause: str) -> None:
        """Event transisi ekspresi (label + sebab, bukan vektor)."""
        self.events.append({
            "stage": "expression",
            "from": prev,
            "to": next_,
            "cause": cause,
        })

    # ----------------------------------------------------------------
    # Listing 15.2 — Persentil nearest-rank
    # ----------------------------------------------------------------

    @staticmethod
    def _nearest_rank(sorted_vals: list[float], q: float) -> float:
        """Persentil nearest-rank (Vol III): p = ceil(q/100 * N) elemen
        ke-p pada data terurut — konsisten & anti floor-bias."""
        n = len(sorted_vals)
        if n == 0:
            return 0.0
        k = max(1, math.ceil(q / 100.0 * n))
        return sorted_vals[min(k, n) - 1]

    def summary(self) -> dict:
        """Ringkasan p50/p95/p99 per tahap + jumlah event."""
        out = {}
        for stage, vals in sorted(self._stages.items()):
            sv = sorted(vals)
            out[stage] = {
                "n": len(sv),
                "p50_ms": round(self._nearest_rank(sv, 50), 3),
                "p95_ms": round(self._nearest_rank(sv, 95), 3),
                "p99_ms": round(self._nearest_rank(sv, 99), 3),
            }
        out["events"] = len(self.events)
        return out
