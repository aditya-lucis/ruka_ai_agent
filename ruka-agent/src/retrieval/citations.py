"""Citation generation + stale knowledge detection."""
from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime, timezone

@dataclass(frozen=True)
class Citation:
    chunk_id: str
    source_path: str
    heading: str
    stale_days: float

    def render(self) -> str:
        age = f" (sumber {self.stale_days:.0f} hari)" if self.stale_days > 180 else ""
        head = f" › {self.heading}" if self.heading else ""
        return f"[{self.chunk_id}] {self.source_path}{head}{age}"

def render_citations(used: list[Citation]) -> str:
    if not used:
        return ""
    lines = ["Sumber:"] + ["  " + c.render() for c in used]
    if any(c.stale_days > 180 for c in used):
        lines.append("  (catatan: sebagian sumber berumur > 6 bulan — "
                     "periksa kebaruan)")
    return "\n".join(lines)

def stale_report(candidates: list, now: datetime | None = None) -> dict:
    """Ringkasan basi untuk trace & sweep harian."""
    now = now or datetime.now(timezone.utc)
    buckets = {"fresh<30d": 0, "ok 30-180d": 0, "stale>180d": 0}
    for c in candidates:
        if c.stale_days < 30:
            buckets["fresh<30d"] += 1
        elif c.stale_days <= 180:
            buckets["ok 30-180d"] += 1
        else:
            buckets["stale>180d"] += 1
    return buckets
