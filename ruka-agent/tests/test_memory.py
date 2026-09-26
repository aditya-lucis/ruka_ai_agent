"""Unit tests for MultimodalMemory — Ruka Volume IV Listings 13.2 & 13.3."""

import time

import pytest

from ruka_perception.memory.multimodal import (
    AdmissionPolicy,
    MemoryCandidate,
    Modality,
    MultimodalMemory,
    RETENTION_POLICY,
    memory_class,
)


def _cand(**kwargs) -> MemoryCandidate:
    """Helper: buat MemoryCandidate dengan override."""
    defaults = dict(modality=Modality.TEXT, summary="Test summary", importance=0.6)
    defaults.update(kwargs)
    return MemoryCandidate(**defaults)


def test_memory_class_semantic_threshold():
    """importance >= 0.8 -> semantic (ingatan penting setahun)."""
    assert memory_class(Modality.TEXT, 0.8) == "semantic"
    assert memory_class(Modality.IMAGE, 1.0) == "semantic"


def test_memory_class_per_modality():
    """Modality di bawah 0.8 -> kelas sesuai modality."""
    assert memory_class(Modality.TEXT, 0.5) == "conversation"
    assert memory_class(Modality.IMAGE, 0.3) == "visual_episode"
    assert memory_class(Modality.AUDIO, 0.7) == "audio_episode"
    assert memory_class(Modality.INTERACTION_EVENT, 0.6) == "interaction_event"


def test_retention_policy_semantic_ttl():
    """Semantic harus memiliki TTL 365 hari (dalam detik)."""
    ttl, _quota = RETENTION_POLICY["semantic"]
    assert ttl == 365 * 86400


def test_admission_threshold():
    """Kandidat dengan skor di bawah threshold harus ditolak."""
    policy = AdmissionPolicy(threshold=0.45)
    low = _cand(importance=0.1)  # skor = 0.5*0.1 + 0.25*0.3 + 0 = 0.125 < 0.45
    admitted, score = policy.evaluate(low)
    assert not admitted
    assert score < 0.45


def test_admission_user_flagged_forces_admit():
    """user_flagged = True harus memaksa masuk meskipun skor rendah."""
    policy = AdmissionPolicy(threshold=0.45)
    flagged = _cand(importance=0.1, metadata={"user_flagged": True})
    admitted, _ = policy.evaluate(flagged)
    assert admitted


def test_offer_high_importance_admits_semantic():
    """Kandidat importance >= 0.8 harus lolos dan menjadi kelas semantic."""
    mem = MultimodalMemory()
    cand = _cand(importance=0.85, modality=Modality.IMAGE, summary="deploy error screenshot")
    ok, mid = mem.offer(cand)
    assert ok
    assert mem.items[mid]["class"] == "semantic"
    assert mem.items[mid]["keep_raw"] is False  # bytes TIDAK disimpan


def test_raw_without_consent_rejected():
    """Kandidat dengan keep_raw=True tanpa user_consent harus ditolak (RAW GATE)."""
    mem = MultimodalMemory()
    cand = _cand(keep_raw=True)  # tanpa user_consent
    ok, mid = mem.offer(cand)
    assert not ok
    assert mid == ""
    assert any(r["reason"] == "raw_without_consent" for r in mem.rejected)


def test_raw_with_consent_accepted():
    """Kandidat dengan keep_raw=True DAN user_consent harus bisa lolos gerbang."""
    mem = MultimodalMemory()
    cand = _cand(
        keep_raw=True,
        importance=0.9,
        metadata={"user_consent": True},
    )
    ok, _ = mem.offer(cand)
    assert ok


def test_forget_is_idempotent():
    """Invarian buku: forget() dua kali — panggil kedua harus False (bukan error)."""
    mem = MultimodalMemory()
    cand = _cand(importance=0.9)
    _, mid = mem.offer(cand)
    assert mem.forget(mid) is True   # pertama
    assert mem.forget(mid) is False  # kedua — idempoten


def test_sweep_expired_removes_ttl_passed():
    """Item dengan expires_at di masa lalu harus dibuang oleh sweep_expired."""
    t_past = time.time() - 1e6  # sudah lama lewat

    def fixed_time():
        return time.time()

    mem = MultimodalMemory(now=fixed_time)
    cand = _cand(importance=0.9, summary="old memory")
    cand.created_at = t_past
    ok, mid = mem.offer(cand)
    assert ok

    # Override expires_at ke masa lalu
    mem.items[mid]["expires_at"] = t_past + 1

    n = mem.sweep_expired()
    assert n >= 1
    assert mid not in mem.items


def test_semantic_ttl_365_days():
    """Semantic item harus memiliki TTL 365 hari dari saat dibuat."""
    t0 = 1_000_000.0
    mem = MultimodalMemory()
    cand = _cand(importance=0.9)
    cand.created_at = t0
    _, mid = mem.offer(cand)
    expected_expiry = t0 + 365 * 86400
    assert abs(mem.items[mid]["expires_at"] - expected_expiry) < 1.0


def test_list_all_summary_truncated():
    """list_all harus memotong ringkasan ke 60 karakter."""
    mem = MultimodalMemory()
    long_summary = "A" * 200
    cand = _cand(importance=0.9, summary=long_summary)
    mem.offer(cand)
    items = mem.list_all()
    assert all(len(i["summary"]) <= 60 for i in items)


def test_sensitivity_preserved():
    """sensitivity dari kandidat harus tersimpan apa adanya."""
    mem = MultimodalMemory()
    cand = _cand(importance=0.9, sensitivity="high")
    _, mid = mem.offer(cand)
    assert mem.items[mid]["sensitivity"] == "high"
