from __future__ import annotations
import logging
import time
import random

log = logging.getLogger("ruka.llm")

class LLMError(Exception):
    """Error panggilan model setelah retry habis."""

class LLMTransientError(LLMError):
    """Transient (429/5xx) — aman dicoba ulang."""

class LLMPermanentError(LLMError):
    """Permanen (400/403) — TIDAK boleh di-retry."""

def retry_transient(
    fn,
    *,
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 30.0,
):
    """Exponential backoff + jitter — hanya untuk transient.
    Aturan (sesuai panduan resmi): jangan pernah me-retry
    error klien seperti 400 (permintaan salah) atau 403
    (autentikasi) — ulangi hanya 429/timeout/5xx.
    """
    for attempt in range(max_retries + 1):
        try:
            return fn()
        except LLMTransientError:
            if attempt == max_retries:
                raise
            delay = min(base_delay * 2 ** attempt, max_delay)
            delay += random.uniform(0, delay * 0.1)  # jitter
            log.warning(
                "transient error, retry %d/%d dalam %.1fs",
                attempt + 1, max_retries, delay,
            )
            time.sleep(delay)
    raise LLMError("unreachable")
