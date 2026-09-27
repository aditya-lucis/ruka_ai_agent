"""Tests for RUKA VI Distributed Systems Mathematics (Part VIII & XXV).
Strictly verifies:
- Version vectors: partial order, semilattice (join/merge idempotence, commutativity, associativity)
- Concurrency detection: EQUAL, LESS, GREATER, CONCURRENT
- Deterministic LWW resolution with lexicographical tie-break
- IdempotencyCache: FIFO eviction, TTL eviction, result caching
- Full-jitter exponential backoff: U(0, min(cap, base * 2^attempt)), boundary bounds, seed determinism
"""

import random
import pytest

from ruka_companion.math.distributed import (
    VectorRelation,
    compare_version_vectors,
    merge_version_vectors,
    resolve_lww,
    IdempotencyCache,
    backoff_full_jitter,
)


class TestVersionVectorSemilattice:
    def test_merge_commutativity(self):
        v1 = {"node-a": 3, "node-b": 1}
        v2 = {"node-b": 4, "node-c": 2}
        assert merge_version_vectors(v1, v2) == merge_version_vectors(v2, v1)

    def test_merge_associativity(self):
        v1 = {"a": 1, "b": 5}
        v2 = {"b": 2, "c": 3}
        v3 = {"a": 4, "c": 1}
        m1 = merge_version_vectors(merge_version_vectors(v1, v2), v3)
        m2 = merge_version_vectors(v1, merge_version_vectors(v2, v3))
        assert m1 == m2

    def test_merge_idempotence(self):
        v = {"a": 3, "b": 7, "c": 2}
        assert merge_version_vectors(v, v) == v

    def test_causal_relations(self):
        # Equal
        assert compare_version_vectors({"a": 2}, {"a": 2}) == VectorRelation.EQUAL
        # Less
        assert compare_version_vectors({"a": 1, "b": 2}, {"a": 2, "b": 2}) == VectorRelation.LESS
        # Greater
        assert compare_version_vectors({"a": 3, "b": 2}, {"a": 2, "b": 2}) == VectorRelation.GREATER
        # Concurrent
        assert compare_version_vectors({"a": 3, "b": 1}, {"a": 2, "b": 2}) == VectorRelation.CONCURRENT


class TestLWWResolver:
    def test_timestamp_dominance(self):
        assert resolve_lww(100.0, "node-a", 200.0, "node-b") == "node-b"
        assert resolve_lww(300.0, "node-a", 200.0, "node-b") == "node-a"

    def test_lexicographical_tie_break(self):
        # Same timestamp: 'node-z' > 'node-a'
        assert resolve_lww(100.0, "node-z", 100.0, "node-a") == "node-z"
        assert resolve_lww(100.0, "node-a", 100.0, "node-z") == "node-z"


class TestIdempotencyCache:
    def test_record_and_seen(self):
        cache = IdempotencyCache(max_entries=10, ttl_ms=0)
        assert cache.seen("k1", now_ms=100) is False

        cache.record("k1", now_ms=100, result={"status": "ok"})
        assert cache.seen("k1", now_ms=150) is True
        assert cache.result("k1") == {"status": "ok"}

    def test_ttl_expiration(self):
        cache = IdempotencyCache(max_entries=10, ttl_ms=1000)
        cache.record("k1", now_ms=100)

        # Within TTL
        assert cache.seen("k1", now_ms=500) is True

        # Expired after TTL
        assert cache.seen("k1", now_ms=1200) is False

    def test_fifo_capacity_eviction(self):
        cache = IdempotencyCache(max_entries=3, ttl_ms=0)
        cache.record("k1", now_ms=10)
        cache.record("k2", now_ms=20)
        cache.record("k3", now_ms=30)

        # Evicts oldest k1
        cache.record("k4", now_ms=40)
        assert cache.seen("k1", now_ms=50) is False
        assert cache.seen("k2", now_ms=50) is True
        assert cache.seen("k4", now_ms=50) is True


class TestBackoffFullJitter:
    def test_bounds_and_cap(self):
        base = 500
        cap = 30_000
        for attempt in range(10):
            max_delay = min(cap, base * (2 ** attempt))
            for _ in range(20):
                d = backoff_full_jitter(attempt, base_ms=base, cap_ms=cap)
                assert 0 <= d <= max_delay

    def test_seed_determinism(self):
        rng1 = random.Random(20260910)
        rng2 = random.Random(20260910)

        seq1 = [backoff_full_jitter(i, rng=rng1) for i in range(10)]
        seq2 = [backoff_full_jitter(i, rng=rng2) for i in range(10)]
        assert seq1 == seq2

    def test_attempt_zero_average_matches_synthetic_benchmark(self):
        # 200 samples of attempt 0 with fixed seed 20260910
        rng = random.Random(20260910)
        samples = [backoff_full_jitter(0, base_ms=500, cap_ms=30_000, rng=rng) for _ in range(200)]
        mean = sum(samples) / len(samples)
        # Expected around 250 ms (U(0, 500))
        assert 200 <= mean <= 300


# ============================================================ Extended Tests
class TestIdempotencyCache:
    def test_basic_seen_and_record(self):
        cache = IdempotencyCache(max_entries=10)
        assert not cache.seen("k1", 100)
        cache.record("k1", 100, result="ok")
        assert cache.seen("k1", 100)

    def test_result_retrieval(self):
        cache = IdempotencyCache(max_entries=10)
        cache.record("k1", 100, result={"status": "done"})
        assert cache.result("k1") == {"status": "done"}

    def test_ttl_eviction(self):
        cache = IdempotencyCache(max_entries=100, ttl_ms=1000)
        cache.record("k1", 100)
        assert cache.seen("k1", 500)
        # After TTL
        assert not cache.seen("k1", 1200)

    def test_fifo_eviction(self):
        cache = IdempotencyCache(max_entries=3)
        cache.record("a", 1)
        cache.record("b", 2)
        cache.record("c", 3)
        # Now full; adding d should evict 'a' (oldest)
        cache.record("d", 4)
        assert not cache.seen("a", 5)
        assert cache.seen("d", 5)

    def test_zero_max_entries_rejected(self):
        with pytest.raises(ValueError):
            IdempotencyCache(max_entries=0)


class TestVersionVectorExtended:
    def test_merge_idempotence(self):
        v1 = {"A": 2, "B": 1}
        m = merge_version_vectors(v1, v1)
        assert m == v1

    def test_merge_commutativity(self):
        v1 = {"A": 2, "B": 1}
        v2 = {"A": 1, "B": 3}
        assert merge_version_vectors(v1, v2) == merge_version_vectors(v2, v1)

    def test_merge_associativity(self):
        v1 = {"A": 1}
        v2 = {"B": 2}
        v3 = {"A": 3, "C": 1}
        m12_3 = merge_version_vectors(merge_version_vectors(v1, v2), v3)
        m1_23 = merge_version_vectors(v1, merge_version_vectors(v2, v3))
        assert m12_3 == m1_23

    def test_compare_self_equal(self):
        v = {"X": 5, "Y": 3}
        assert compare_version_vectors(v, v) == VectorRelation.EQUAL

    def test_compare_strict_less(self):
        v1 = {"A": 1, "B": 1}
        v2 = {"A": 2, "B": 2}
        assert compare_version_vectors(v1, v2) == VectorRelation.LESS

    def test_compare_strict_greater(self):
        v1 = {"A": 3, "B": 3}
        v2 = {"A": 1, "B": 1}
        assert compare_version_vectors(v1, v2) == VectorRelation.GREATER


class TestLWWExtended:
    def test_lww_timestamp_wins(self):
        assert resolve_lww(100, "node_a", 200, "node_b") == "node_b"
        assert resolve_lww(300, "node_a", 200, "node_b") == "node_a"

    def test_lww_tie_lexicographic(self):
        # Same timestamp → higher node_id wins
        assert resolve_lww(100, "alpha", 100, "beta") == "beta"
        assert resolve_lww(100, "zulu", 100, "alpha") == "zulu"

