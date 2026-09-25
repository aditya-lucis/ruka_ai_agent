# -*- coding: utf-8 -*-
import json
from pathlib import Path
import pytest
from src.telemetry.tracing import (
    PII_PATTERNS,
    Trace,
    TraceWriter,
    redact,
    setup_json_logging,
)


def test_pii_redacted_at_write_time(tmp_path: Path):
    t = Trace(goal="kirim ke bos@trendamis.im ya", session_id="s1")
    t.event(
        "tool",
        "tool_args",
        email="bos@trendamis.im",
        credential="sk-abcdefgh12345678",
    )   # dummy uji redaksi
    doc = t.close("done", {})
    blob = json.dumps(doc)
    assert "bos@trendamis.im" not in blob
    assert "sk-abcdefgh12345678" not in blob
    assert "[REDAKTED]" in blob


def test_one_request_one_line(tmp_path: Path):
    w = TraceWriter(tmp_path, retention_days=14)
    t = Trace("goal", "s1")
    t.event("orchestrator", "llm_call", tokens=120)
    w.write(t, "done", {"tokens": 120})
    lines = list((tmp_path / next(iter(tmp_path.iterdir()))).open())
    assert len(lines) == 1
    doc = json.loads(lines[0])
    for k in ("trace_id", "goal", "final_status", "summary", "events"):
        assert k in doc                      # bidang wajib hadir


def test_close_is_idempotent():
    t = Trace("g", "s")
    a = t.close("done", {})
    b = t.close("partial", {})
    assert a is b and a["final_status"] == "done"


def test_closed_trace_rejects_events():
    t = Trace("g", "s")
    t.close("done", {})
    n_before = t.frozen["n_events"]
    t.event("tool", "late_event")
    assert t.frozen["n_events"] == n_before


def test_sampling_deterministic(tmp_path: Path):
    w = TraceWriter(tmp_path, sample_rate=0.5)   # tulis 1 dari 2
    written = 0
    for i in range(6):
        if w.write(Trace(f"g{i}", "s"), "done", {}) is not None:
            written += 1
    assert written == 3
