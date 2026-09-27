"""RUKA VI: Memory Synchronization Engine — Delta Events, Version Vectors, and Tombstones.
Strictly follows RUKA-VI Chapter XX (baris 60-240).
"""

from __future__ import annotations

from dataclasses import dataclass, field
import time
from typing import Any, Callable, Mapping
import uuid

from ruka_companion.math.distributed import (
    IdempotencyCache,
    VectorRelation,
    compare_version_vectors,
    merge_version_vectors,
)
from .classification import (
    NEVER_SYNC_KEYS,
    SyncClass,
    SyncClassifier,
)


@dataclass
class VersionVector:
    """Version Vector per-objek dengan operasi perbandingan kanonik."""

    vv: dict[str, int] = field(default_factory=dict)

    def inc(self, node: str) -> None:
        self.vv[node] = self.vv.get(node, 0) + 1

    def merge(self, other: dict[str, int] | VersionVector) -> None:
        ov = other.vv if isinstance(other, VersionVector) else other
        self.vv = merge_version_vectors(self.vv, ov)

    def dominates(self, remote: Mapping[str, int]) -> bool:
        rel = compare_version_vectors(self.vv, dict(remote))
        return rel == VectorRelation.GREATER

    def is_dominated_by(self, remote: Mapping[str, int]) -> bool:
        rel = compare_version_vectors(self.vv, dict(remote))
        return rel == VectorRelation.LESS

    def is_same(self, remote: Mapping[str, int]) -> bool:
        rel = compare_version_vectors(self.vv, dict(remote))
        return rel == VectorRelation.EQUAL

    def is_concurrent_with(self, remote: Mapping[str, int]) -> bool:
        rel = compare_version_vectors(self.vv, dict(remote))
        return rel == VectorRelation.CONCURRENT


class ConflictDetector:
    """Detektor konkurensi eksplisit berbasis version vector."""

    def outcome(
        self, lhs: Mapping[str, int], rhs: Mapping[str, int]
    ) -> str:
        rel = compare_version_vectors(dict(lhs), dict(rhs))
        if rel == VectorRelation.EQUAL:
            return "SAME"
        if rel == VectorRelation.GREATER:
            return "LHS_NEWER"
        if rel == VectorRelation.LESS:
            return "RHS_NEWER"
        return "CONCURRENT"


class LWWResolver:
    """Last-Writer-Wins deterministik: (timestamp, node_id) leksikografis."""

    def resolve(
        self,
        lhs: tuple[int, str, dict[str, Any]],
        rhs: tuple[int, str, dict[str, Any]],
    ) -> tuple[str, dict[str, Any]]:
        ts_l, node_l, val_l = lhs
        ts_r, node_r, val_r = rhs
        if ts_l > ts_r:
            return node_l, val_l
        if ts_r > ts_l:
            return node_r, val_r
        # Waktu persis sama -> tie-breaker ID node leksikografis
        if node_l >= node_r:
            return node_l, val_l
        return node_r, val_r


@dataclass(frozen=True)
class Tombstone:
    """Batu nisan memori — mencegah kebangkitan data terhapus (anti-resurrection)."""

    object_id: str
    node: str
    timestamp_ms: int
    vv: dict[str, int]


@dataclass(frozen=True)
class DeltaEvent:
    """Satu perubahan granular memori (offline-first)."""

    event_id: str
    memory_system: str
    object_id: str
    op: str  # 'upsert' | 'delete'
    payload: dict[str, Any]
    vv: dict[str, int]
    origin_node: str
    cls_int: int
    cls_name: str
    timestamp_ms: int

    @classmethod
    def mint(
        cls,
        memory_system: str,
        object_id: str,
        op: str,
        payload: dict[str, Any],
        vv: VersionVector,
        origin_node: str,
        cls_int: int,
        cls_name: str,
        clock: Callable[[], int],
    ) -> DeltaEvent:
        return cls(
            event_id=f"delta-{uuid.uuid4().hex}",
            memory_system=memory_system,
            object_id=object_id,
            op=op,
            payload=payload,
            vv=dict(vv.vv),
            origin_node=origin_node,
            cls_int=cls_int,
            cls_name=cls_name,
            timestamp_ms=clock(),
        )


@dataclass(frozen=True)
class SyncOutcome:
    applied: bool
    action: str  # APPLIED | IGNORED_STALE | CONFLICT_RESOLVED | IGNORED_TOMBSTONE | REJECTED_NEVER_SYNC | DUPLICATE
    detail: str = ""
    winner: str | None = None


@dataclass
class SyncState:
    """Objek sinkron: nilai + vv + tombstone."""

    object_id: str
    memory_system: str
    value: dict[str, Any]
    vv: VersionVector = field(default_factory=VersionVector)
    deleted: bool = False
    tombstone: Tombstone | None = None
    last_writer: str = ""
    last_timestamp_ms: int = 0


class MemorySyncEngine:
    """Mesin sync dua arah dengan aturan EKSPLISIT (Part XX)."""

    def __init__(
        self,
        node_id: str,
        classifier: SyncClassifier | None = None,
        clock: Callable[[], int] | None = None,
    ) -> None:
        self.node_id = node_id
        self.classifier = classifier or SyncClassifier()
        self._now = clock or (lambda: int(time.time() * 1000))
        self._objects: dict[tuple[str, str], SyncState] = {}
        self._outbox: list[DeltaEvent] = []
        self._idem = IdempotencyCache(max_entries=8192)
        self._detector = ConflictDetector()
        self._lww = LWWResolver()
        self.stats = {
            "applied": 0,
            "conflict_resolved": 0,
            "stale": 0,
            "duplicate": 0,
            "rejected": 0,
            "tombstone_blocked": 0,
        }

    # ------------------------------------------------------------- penulisan
    def local_upsert(
        self, memory_system: str, object_id: str, payload: dict[str, Any]
    ) -> DeltaEvent:
        """Tulis lokal (offline-first) → delta keluar antrean sync."""
        if set(payload) & NEVER_SYNC_KEYS:
            raise ValueError(
                f"payload mengandung kunci NEVER_SYNC: "
                f"{sorted(set(payload) & NEVER_SYNC_KEYS)}"
            )

        key = (memory_system, object_id)
        st = self._objects.get(key)
        if st is None:
            st = SyncState(
                object_id=object_id, memory_system=memory_system, value={}
            )
            self._objects[key] = st

        st.vv.inc(self.node_id)
        st.value = dict(payload)
        st.deleted = False
        st.tombstone = None
        st.last_writer = self.node_id
        st.last_timestamp_ms = self._now()

        cls_ = self.classifier.classify(memory_system, None, set(payload))
        delta = DeltaEvent.mint(
            memory_system=memory_system,
            object_id=object_id,
            op="upsert",
            payload=dict(payload),
            vv=st.vv,
            origin_node=self.node_id,
            cls_int=int(cls_),
            cls_name=cls_.name,
            clock=self._now,
        )
        self._outbox.append(delta)
        return delta

    def local_delete(
        self, memory_system: str, object_id: str
    ) -> DeltaEvent:
        """Hapus lokal → pasang tombstone dan delta delete."""
        key = (memory_system, object_id)
        st = self._objects.get(key)
        if st is None:
            st = SyncState(
                object_id=object_id, memory_system=memory_system, value={}
            )
            self._objects[key] = st

        st.vv.inc(self.node_id)
        st.deleted = True
        st.value = {}
        now = self._now()
        st.tombstone = Tombstone(
            object_id=object_id,
            node=self.node_id,
            timestamp_ms=now,
            vv=dict(st.vv.vv),
        )
        st.last_writer = self.node_id
        st.last_timestamp_ms = now

        cls_ = self.classifier.classify(memory_system, None, set(st.value))
        delta = DeltaEvent.mint(
            memory_system=memory_system,
            object_id=object_id,
            op="delete",
            payload={},
            vv=st.vv,
            origin_node=self.node_id,
            cls_int=int(cls_),
            cls_name=cls_.name,
            clock=self._now,
        )
        self._outbox.append(delta)
        return delta

    # ------------------------------------------------------------- penerimaan
    def apply_remote(self, delta: DeltaEvent) -> SyncOutcome:
        """Terapkan delta dari remote (cloud / perangkat lain) — SEMUA aturan."""
        # 1. batas klasifikasi
        if set(delta.payload) & NEVER_SYNC_KEYS:
            self.stats["rejected"] += 1
            return SyncOutcome(
                False, "REJECTED_NEVER_SYNC", "payload memuat kunci NEVER_SYNC"
            )

        # 2. idempotensi
        if self._idem.seen(delta.event_id, self._now()):
            self.stats["duplicate"] += 1
            return SyncOutcome(False, "DUPLICATE", f"event {delta.event_id}")

        self._idem.record(delta.event_id, self._now())
        key = (delta.memory_system, delta.object_id)
        st = self._objects.get(key)
        if st is None:
            st = SyncState(
                object_id=delta.object_id,
                memory_system=delta.memory_system,
                value={},
            )
            self._objects[key] = st

        # 3. hukum tombstone: hapus selamanya selamanya
        if st.tombstone is not None and delta.op == "upsert":
            tb_vv = st.tombstone.vv
            if not (
                VersionVector(dict(tb_vv)).is_dominated_by(delta.vv)
                and not VersionVector(dict(tb_vv)).is_same(delta.vv)
            ):
                self.stats["tombstone_blocked"] += 1
                return SyncOutcome(
                    False,
                    "IGNORED_TOMBSTONE",
                    "upsert kalah lawan tombstone (anti-resurrection)",
                )

        # 4-5. ordering vv
        outcome = self._detector.outcome(st.vv.vv, delta.vv)
        if outcome == "SAME":
            self.stats["duplicate"] += 1
            return SyncOutcome(False, "DUPLICATE", "versi sama")
        if outcome == "LHS_NEWER":
            self.stats["stale"] += 1
            return SyncOutcome(
                False,
                "IGNORED_STALE",
                f"vv lokal {st.vv.vv} ⊒ remote {delta.vv}",
            )
        if outcome == "RHS_NEWER":
            self._apply(st, delta)
            self.stats["applied"] += 1
            return SyncOutcome(True, "APPLIED", "remote lebih baru")

        # 6. konkuren → resolusi eksplisit
        return self._resolve_conflict(st, delta)

    def _apply(self, st: SyncState, delta: DeltaEvent) -> None:
        st.vv.merge(delta.vv)
        st.last_writer = delta.origin_node
        st.last_timestamp_ms = delta.timestamp_ms
        if delta.op == "delete":
            st.deleted = True
            st.tombstone = Tombstone(
                object_id=delta.object_id,
                node=delta.origin_node,
                timestamp_ms=delta.timestamp_ms,
                vv=dict(delta.vv),
            )
            st.value = {}
        else:
            st.value = dict(delta.payload)

    def _resolve_conflict(
        self, st: SyncState, delta: DeltaEvent
    ) -> SyncOutcome:
        """Konkuren: merge field disjoint; LWW untuk field sama (deterministik)."""
        local_keys = set(st.value)
        remote_keys = set(delta.payload)
        if delta.op == "delete" or st.deleted:
            # hapus vs tulis → tombstone menang (konservatif privasi)
            self._apply(st, delta)
            self.stats["conflict_resolved"] += 1
            return SyncOutcome(
                True,
                "CONFLICT_RESOLVED",
                "delete-vs-write → tombstone menang (konservatif)",
                winner="tombstone",
            )
        if not (local_keys & remote_keys):
            # field disjoint → merge
            merged = {**st.value, **delta.payload}
            st.value = merged
            st.vv.merge(delta.vv)
            st.last_writer = delta.origin_node
            st.last_timestamp_ms = delta.timestamp_ms
            self.stats["conflict_resolved"] += 1
            return SyncOutcome(
                True,
                "CONFLICT_RESOLVED",
                f"merge field disjoint {sorted(remote_keys - local_keys)}",
                winner="merge",
            )
        # field bertabrakan → LWW (ts, node-id) deterministik dua sisi
        winner, payload = self._lww.resolve(
            (
                st.last_timestamp_ms,
                st.last_writer or self.node_id,
                st.value,
            ),
            (delta.timestamp_ms, delta.origin_node, delta.payload),
        )
        st.value = payload
        st.vv.merge(delta.vv)
        st.last_writer = winner
        st.last_timestamp_ms = max(st.last_timestamp_ms, delta.timestamp_ms)
        self.stats["conflict_resolved"] += 1
        return SyncOutcome(
            True,
            "CONFLICT_RESOLVED",
            f"LWW winner: {winner}",
            winner=winner,
        )

    def drain_outbox(self) -> list[DeltaEvent]:
        out = list(self._outbox)
        self._outbox.clear()
        return out

    def get_state(
        self, memory_system: str, object_id: str
    ) -> SyncState | None:
        return self._objects.get((memory_system, object_id))

    get = get_state

