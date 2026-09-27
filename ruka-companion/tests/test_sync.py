"""Tests for RUKA VI Memory Synchronization Engine (Part XX).
Strictly verifies:
- 6-level classification, legacy mappings, NEVER_SYNC boundary enforcement
- VersionVector causality, domination, concurrency, and LWW determinism
- Offline-first local writes (upsert/delete) & outbox draining
- Six sequential remote delta acceptance rules:
  1. NEVER_SYNC boundary rejection (REJECTED_NEVER_SYNC)
  2. Idempotency duplicate rejection (DUPLICATE)
  3. Tombstone anti-resurrection law (IGNORED_TOMBSTONE)
  4. Stale delta rejection (IGNORED_STALE)
  5. Causal ordering advance (APPLIED)
  6. Explicit conflict resolution:
     - Disjoint field merge (winner: merge)
     - Overlapping field LWW tie-break (winner: node_id)
     - Delete vs write (winner: tombstone)
"""

import pytest
from ruka_companion.sync.classification import (
    SyncClass,
    NEVER_SYNC_KEYS,
    LEGACY_SENSITIVITY_MAP,
    SyncClassifier,
)
from ruka_companion.sync.engine import (
    VersionVector,
    ConflictDetector,
    LWWResolver,
    DeltaEvent,
    MemorySyncEngine,
    SyncOutcome,
)


class TestClassification:
    def test_six_levels_exist_and_ordered(self):
        assert SyncClass.PUBLIC < SyncClass.PERSONAL
        assert SyncClass.PERSONAL < SyncClass.PRIVATE
        assert SyncClass.PRIVATE < SyncClass.SENSITIVE
        assert SyncClass.SENSITIVE < SyncClass.LOCAL_ONLY
        assert SyncClass.LOCAL_ONLY < SyncClass.NEVER_SYNC

    def test_never_sync_keys_contain_core_secrets(self):
        core = {
            "api_key",
            "secret",
            "token",
            "password",
            "credential",
            "private_key",
            "raw_biometrics",
            "face_embedding",
            "voice_embedding",
        }
        assert core.issubset(NEVER_SYNC_KEYS)

    def test_legacy_sensitivity_mapping(self):
        classifier = SyncClassifier()
        assert classifier.classify("core", "NORMAL") == SyncClass.PRIVATE
        assert classifier.classify("core", "PERSONAL") == SyncClass.SENSITIVE
        assert classifier.classify("core", "SENSITIVE") == SyncClass.LOCAL_ONLY

    def test_payload_with_forbidden_key_forces_never_sync(self):
        classifier = SyncClassifier()
        cls_ = classifier.classify("preference", None, payload_keys={"theme", "secret"})
        assert cls_ == SyncClass.NEVER_SYNC

    def test_can_sync_direction_rules(self):
        classifier = SyncClassifier()
        # to_cloud allows up to SENSITIVE
        assert classifier.can_sync(SyncClass.PUBLIC, "to_cloud") is True
        assert classifier.can_sync(SyncClass.PERSONAL, "to_cloud") is True
        assert classifier.can_sync(SyncClass.PRIVATE, "to_cloud") is True
        assert classifier.can_sync(SyncClass.SENSITIVE, "to_cloud") is True
        assert classifier.can_sync(SyncClass.LOCAL_ONLY, "to_cloud") is False
        assert classifier.can_sync(SyncClass.NEVER_SYNC, "to_cloud") is False

        # to_plugin allows only PUBLIC
        assert classifier.can_sync(SyncClass.PUBLIC, "to_plugin") is True
        assert classifier.can_sync(SyncClass.PERSONAL, "to_plugin") is False
        assert classifier.can_sync(SyncClass.SENSITIVE, "to_plugin") is False


class TestVersionVectorAndConflictDetector:
    def test_vv_operations(self):
        vv = VersionVector()
        vv.inc("node-1")
        assert vv.vv == {"node-1": 1}
        vv.inc("node-1")
        assert vv.vv == {"node-1": 2}

        vv.merge({"node-2": 3})
        assert vv.vv == {"node-1": 2, "node-2": 3}

    def test_vv_causality_and_concurrency(self):
        vv1 = VersionVector({"a": 2, "b": 1})
        vv2 = VersionVector({"a": 1, "b": 1})
        vv3 = VersionVector({"a": 1, "b": 2})

        assert vv1.dominates(vv2.vv) is True
        assert vv2.is_dominated_by(vv1.vv) is True
        assert vv1.is_concurrent_with(vv3.vv) is True

    def test_conflict_detector_outcomes(self):
        cd = ConflictDetector()
        assert cd.outcome({"a": 1}, {"a": 1}) == "SAME"
        assert cd.outcome({"a": 2}, {"a": 1}) == "LHS_NEWER"
        assert cd.outcome({"a": 1}, {"a": 2}) == "RHS_NEWER"
        assert cd.outcome({"a": 2, "b": 1}, {"a": 1, "b": 2}) == "CONCURRENT"

    def test_lww_resolver_determinism(self):
        lww = LWWResolver()
        # Higher timestamp wins
        winner, val = lww.resolve(
            (100, "node-a", {"k": "v1"}),
            (200, "node-b", {"k": "v2"}),
        )
        assert winner == "node-b"
        assert val == {"k": "v2"}

        # Equal timestamp: tie-break by node_id lexicographical
        winner1, _ = lww.resolve(
            (100, "node-z", {"k": "z"}),
            (100, "node-a", {"k": "a"}),
        )
        assert winner1 == "node-z"


class TestMemorySyncEngine:
    def test_local_write_and_outbox(self):
        engine = MemorySyncEngine(node_id="local-01", clock=lambda: 1000)
        delta = engine.local_upsert("settings", "theme", {"color": "dark"})

        assert delta.op == "upsert"
        assert delta.memory_system == "settings"
        assert delta.object_id == "theme"
        assert delta.vv == {"local-01": 1}
        assert delta.origin_node == "local-01"

        # Outbox contains delta
        outbox = engine.drain_outbox()
        assert len(outbox) == 1
        assert outbox[0].event_id == delta.event_id
        assert len(engine.drain_outbox()) == 0

    def test_local_write_with_never_sync_keys_raises(self):
        engine = MemorySyncEngine(node_id="local-01")
        with pytest.raises(ValueError):
            engine.local_upsert("secrets", "tok", {"api_key": "secret123"})

    def test_local_delete_creates_tombstone(self):
        engine = MemorySyncEngine(node_id="local-01", clock=lambda: 1000)
        engine.local_upsert("notes", "n1", {"title": "hello"})
        del_delta = engine.local_delete("notes", "n1")

        assert del_delta.op == "delete"
        state = engine.get("notes", "n1")
        assert state.deleted is True
        assert state.tombstone is not None
        assert state.tombstone.node == "local-01"
        assert state.value == {}

    def test_rule1_never_sync_payload_rejected(self):
        engine = MemorySyncEngine(node_id="local-01")
        delta = DeltaEvent(
            event_id="e1",
            memory_system="notes",
            object_id="n1",
            op="upsert",
            payload={"token": "forbidden_token"},
            vv={"cloud": 1},
            origin_node="cloud",
            cls_int=int(SyncClass.NEVER_SYNC),
            cls_name="NEVER_SYNC",
            timestamp_ms=1000,
        )
        outcome = engine.apply_remote(delta)
        assert outcome.applied is False
        assert outcome.action == "REJECTED_NEVER_SYNC"
        assert engine.stats["rejected"] == 1

    def test_rule2_duplicate_event_id_ignored(self):
        engine = MemorySyncEngine(node_id="local-01")
        delta = DeltaEvent(
            event_id="e-dup",
            memory_system="notes",
            object_id="n1",
            op="upsert",
            payload={"text": "hello"},
            vv={"cloud": 1},
            origin_node="cloud",
            cls_int=int(SyncClass.PERSONAL),
            cls_name="PERSONAL",
            timestamp_ms=1000,
        )
        res1 = engine.apply_remote(delta)
        assert res1.applied is True
        assert res1.action == "APPLIED"

        # Apply again with same event_id
        res2 = engine.apply_remote(delta)
        assert res2.applied is False
        assert res2.action == "DUPLICATE"
        assert engine.stats["duplicate"] >= 1

    def test_rule3_tombstone_anti_resurrection(self):
        engine = MemorySyncEngine(node_id="local-01", clock=lambda: 1000)
        # 1. Local delete creates tombstone at vv {"local-01": 1}
        engine.local_delete("notes", "n1")

        # 2. Remote delta with older/equal causal history tries to upsert
        delta = DeltaEvent(
            event_id="e-resurrect",
            memory_system="notes",
            object_id="n1",
            op="upsert",
            payload={"text": "zombie content"},
            vv={"local-01": 1},  # Not strictly dominating
            origin_node="cloud",
            cls_int=int(SyncClass.PERSONAL),
            cls_name="PERSONAL",
            timestamp_ms=900,
        )
        outcome = engine.apply_remote(delta)
        assert outcome.applied is False
        assert outcome.action == "IGNORED_TOMBSTONE"
        assert engine.stats["tombstone_blocked"] == 1
        assert engine.get("notes", "n1").deleted is True

    def test_rule4_and_rule5_stale_and_same_vv(self):
        engine = MemorySyncEngine(node_id="local-01", clock=lambda: 1000)
        engine.local_upsert("notes", "n1", {"text": "v2"})
        engine.local_upsert("notes", "n1", {"text": "v3"})  # local vv is {"local-01": 2}

        # Remote delta with vv {"local-01": 1} -> stale
        delta = DeltaEvent(
            event_id="e-stale",
            memory_system="notes",
            object_id="n1",
            op="upsert",
            payload={"text": "v1"},
            vv={"local-01": 1},
            origin_node="cloud",
            cls_int=int(SyncClass.PERSONAL),
            cls_name="PERSONAL",
            timestamp_ms=800,
        )
        outcome = engine.apply_remote(delta)
        assert outcome.applied is False
        assert outcome.action == "IGNORED_STALE"
        assert engine.stats["stale"] == 1

    def test_rule6_causal_advance_applied(self):
        engine = MemorySyncEngine(node_id="local-01", clock=lambda: 1000)
        engine.local_upsert("notes", "n1", {"text": "v1"})  # local vv {"local-01": 1}

        # Remote delta causally newer: {"local-01": 1, "cloud": 1}
        delta = DeltaEvent(
            event_id="e-advance",
            memory_system="notes",
            object_id="n1",
            op="upsert",
            payload={"text": "v2 from cloud"},
            vv={"local-01": 1, "cloud": 1},
            origin_node="cloud",
            cls_int=int(SyncClass.PERSONAL),
            cls_name="PERSONAL",
            timestamp_ms=1100,
        )
        outcome = engine.apply_remote(delta)
        assert outcome.applied is True
        assert outcome.action == "APPLIED"
        assert engine.get("notes", "n1").value == {"text": "v2 from cloud"}
        assert engine.stats["applied"] == 1

    def test_conflict_disjoint_fields_merged(self):
        engine = MemorySyncEngine(node_id="local-01", clock=lambda: 1000)
        engine.local_upsert("user", "u1", {"theme": "dark"})  # vv {"local-01": 1}

        # Concurrent delta modifying disjoint field 'lang'
        delta = DeltaEvent(
            event_id="e-merge",
            memory_system="user",
            object_id="u1",
            op="upsert",
            payload={"lang": "id"},
            vv={"cloud": 1},  # Concurrent with {"local-01": 1}
            origin_node="cloud",
            cls_int=int(SyncClass.PERSONAL),
            cls_name="PERSONAL",
            timestamp_ms=1050,
        )
        outcome = engine.apply_remote(delta)
        assert outcome.applied is True
        assert outcome.action == "CONFLICT_RESOLVED"
        assert outcome.winner == "merge"
        assert engine.get("user", "u1").value == {"theme": "dark", "lang": "id"}

    def test_conflict_overlapping_fields_lww_tie_break(self):
        # Local write at ts=500
        engine = MemorySyncEngine(node_id="local-01", clock=lambda: 500)
        engine.local_upsert("preference", "p1", {"theme": "dark"})

        # Remote concurrent delta at ts=999
        delta = DeltaEvent(
            event_id="evt-1",
            memory_system="preference",
            object_id="p1",
            op="upsert",
            payload={"theme": "light"},
            vv={"cloud-01": 1},
            origin_node="cloud-01",
            cls_int=int(SyncClass.PERSONAL),
            cls_name="PERSONAL",
            timestamp_ms=999,
        )
        out = engine.apply_remote(delta)
        assert out.action == "CONFLICT_RESOLVED"
        assert out.winner == "cloud-01"
        assert engine.get("preference", "p1").value == {"theme": "light"}

    def test_conflict_delete_vs_write_tombstone_wins(self):
        engine = MemorySyncEngine(node_id="local-01", clock=lambda: 1000)
        engine.local_upsert("notes", "n1", {"content": "still here"})

        # Concurrent remote delete
        delta = DeltaEvent(
            event_id="e-del-win",
            memory_system="notes",
            object_id="n1",
            op="delete",
            payload={},
            vv={"cloud": 1},
            origin_node="cloud",
            cls_int=int(SyncClass.PERSONAL),
            cls_name="PERSONAL",
            timestamp_ms=1000,
        )
        outcome = engine.apply_remote(delta)
        assert outcome.applied is True
        assert outcome.action == "CONFLICT_RESOLVED"
        assert outcome.winner == "tombstone"
        assert engine.get("notes", "n1").deleted is True
        assert engine.get("notes", "n1").value == {}
