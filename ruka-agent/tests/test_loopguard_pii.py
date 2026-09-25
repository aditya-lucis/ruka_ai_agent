from __future__ import annotations
import pytest
from src.agent.loopguard import (
    LoopGuard,
    LoopGuardConfig,
    LoopGuardError,
)
from src.telemetry.tracing import redact

# --- LoopGuard Tests (6 tests) ---

def test_two_identical_calls_raise_loopguard():
    guard = LoopGuard(LoopGuardConfig(max_identical_calls=2))
    guard.check("search", {"q": "cats"})
    with pytest.raises(LoopGuardError, match="loop patologis"):
        guard.check("search", {"q": "cats"})

def test_different_arguments_do_not_raise():
    guard = LoopGuard(LoopGuardConfig(max_identical_calls=2))
    guard.check("search", {"q": "cats"})
    guard.check("search", {"q": "dogs"})  # different args -> no raise

def test_repetition_within_window_caught():
    guard = LoopGuard(LoopGuardConfig(max_identical_calls=2, window=5))
    guard.check("search", {"q": "cats"})
    guard.check("read", {"file": "a.txt"})
    guard.check("search", {"q": "cats"})
    with pytest.raises(LoopGuardError):
        guard.check("search", {"q": "cats"})

def test_three_identical_errors_trigger_should_abort():
    guard = LoopGuard(LoopGuardConfig(max_identical_errors=3))
    assert guard.should_abort() is None
    guard.observe_error("TimeoutError:web_fetch")
    guard.observe_error("TimeoutError:web_fetch")
    assert guard.should_abort() is None
    guard.observe_error("TimeoutError:web_fetch")
    assert guard.should_abort() is not None

def test_different_errors_do_not_abort():
    guard = LoopGuard(LoopGuardConfig(max_identical_errors=3))
    guard.observe_error("TimeoutError:web_fetch")
    guard.observe_error("ValueError:read_file")
    guard.observe_error("TimeoutError:web_fetch")
    assert guard.should_abort() is None

def test_dict_key_order_does_not_fool_fingerprint():
    guard = LoopGuard(LoopGuardConfig(max_identical_calls=2))
    guard.check("query", {"x": 1, "y": 2})
    with pytest.raises(LoopGuardError):
        guard.check("query", {"y": 2, "x": 1})

# --- PII Redaction Tests (4 tests) ---

def test_gemini_api_key_redacted():
    raw = "Failed with key AIzaSyD3fakekey12345678901234567890123 in request"
    redacted = redact(raw)
    assert "AIzaSyD" not in redacted
    assert "[REDAKTED]" in redacted

def test_bearer_token_redacted():
    raw = "Authorization: Bearer mysecrettoken12345678901234567890"
    redacted = redact(raw)
    assert "mysecrettoken" not in redacted
    assert "[REDAKTED]" in redacted

def test_email_and_card_redacted():
    raw = "User user.test@example.com with card 1234567812345678 logged in"
    redacted = redact(raw)
    assert "user.test@example.com" not in redacted
    assert "1234567812345678" not in redacted
    assert "[REDAKTED]" in redacted

def test_clean_text_unchanged():
    raw = "Ini teks aman tanpa token atau kunci rahasia sama sekali."
    assert redact(raw) == raw
