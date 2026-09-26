"""Unit tests for observability/metrics.py — Listings 15.1, 15.2, 15.3."""

import time

import pytest

from ruka_perception.observability.metrics import (
    PerceptionMetrics,
    content_fingerprint,
    redact,
)


class TestRedact:
    def test_google_api_key_redacted(self):
        """Kunci bentuk AIza... harus diredaksi."""
        text = "key = AIzaSyD1234567890123456789012345678901234"
        result = redact(text)
        assert "AIza" not in result
        assert "[REDACTED]" in result

    def test_label_value_redacted(self):
        """api_key=VALUE harus diredaksi."""
        text = "api_key=my_secret_key_12345"
        result = redact(text)
        assert "my_secret_key" not in result
        assert "[REDACTED]" in result

    def test_safe_text_unchanged(self):
        """Teks tanpa secret tidak diubah (selain kemungkinan match panjang base64)."""
        text = "hello world, ini pesan biasa"
        result = redact(text)
        assert "hello" in result


class TestContentFingerprint:
    def test_deterministic(self):
        """Fingerprint sama untuk bytes yang sama."""
        data = b"test data bytes"
        assert content_fingerprint(data) == content_fingerprint(data)

    def test_length_16(self):
        """Fingerprint selalu 16 karakter hex."""
        fp = content_fingerprint(b"anything")
        assert len(fp) == 16

    def test_different_data_different_fingerprint(self):
        """Bytes berbeda -> fingerprint berbeda."""
        fp1 = content_fingerprint(b"data_1")
        fp2 = content_fingerprint(b"data_2")
        assert fp1 != fp2


class TestPerceptionMetrics:
    def test_stage_records_duration(self):
        """stage() harus mencatat durasi (ms)."""
        m = PerceptionMetrics()
        result = m.stage("validation", lambda x: x * 2, 21)
        assert result == 42
        s = m.summary()
        assert "validation" in s
        assert s["validation"]["n"] == 1
        assert s["validation"]["p50_ms"] >= 0

    def test_stage_exception_recorded(self):
        """stage() mencatat event error jika fn gagal."""
        m = PerceptionMetrics()
        with pytest.raises(ZeroDivisionError):
            m.stage("bad_stage", lambda: 1 / 0)
        assert any(
            e.get("stage") == "bad_stage" and e.get("ok") is False
            for e in m.events
        )

    def test_record_stage_manual(self):
        """record_stage() dari luar harus masuk summary."""
        m = PerceptionMetrics()
        m.record_stage("api_call", 250.0)
        m.record_stage("api_call", 300.0)
        s = m.summary()
        assert s["api_call"]["n"] == 2

    def test_media_event_no_bytes(self):
        """media_event mencatat metadata, BUKAN bytes."""
        m = PerceptionMetrics()
        m.media_event("upload", "image/png", 1024, "abc123", "trace-1")
        assert len(m.events) == 1
        assert m.events[0]["mime"] == "image/png"
        assert m.events[0]["fingerprint"] == "abc123"

    def test_state_transition_event(self):
        """state_transition mencatat label + sebab."""
        m = PerceptionMetrics()
        m.state_transition("calm", "curious", "user asked question")
        assert m.events[0]["from"] == "calm"
        assert m.events[0]["to"] == "curious"
        assert m.events[0]["cause"] == "user asked question"

    def test_percentile_p95_gte_p50(self):
        """p95 harus >= p50 (invarian nearest-rank)."""
        m = PerceptionMetrics()
        for v in [10, 20, 30, 50, 100, 200, 500]:
            m.record_stage("test_stage", float(v))
        s = m.summary()
        assert s["test_stage"]["p95_ms"] >= s["test_stage"]["p50_ms"]

    def test_percentile_empty(self):
        """Stage kosong -> p50 = 0."""
        assert PerceptionMetrics._nearest_rank([], 50) == 0.0

    def test_summary_events_count(self):
        """Summary harus melaporkan jumlah event."""
        m = PerceptionMetrics()
        m.media_event("a", "image/png", 100, "fp", "t1")
        m.media_event("b", "audio/wav", 200, "fp2", "t2")
        s = m.summary()
        assert s["events"] == 2
