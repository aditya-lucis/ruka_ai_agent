# -*- coding: utf-8 -*-
"""NOCTIS Memory Palace Engine (FR-ME-01 s.d. FR-ME-03 & Table 19).

Arsitektur 5 Sayap Memori Abadi di atas palace.db SQLite WAL:
- 5 Sayap: relationship, project, preference, daily, dream.
- 4 Operasi API Utama: remember, recall, forget, inspect (NOL raw SQL di luar istana).
- Temu balik hibrida 3 jalur paralel (BM25 FTS5, Vektor 512-dim, Graf Entitas)
  yang difusi Reciprocal Rank Fusion (k=60) mengembalikan 6 potongan teratas.
- Penghapusan lunak (soft-delete) dengan alasan wajib.
"""
from __future__ import annotations

import json
import logging
from pathlib import Path
import sqlite3
import threading
import time
from typing import Any

from src.gateway.events import Event, EventBus, OrganNamespace
from src.memory.palace.models import (
    DailyMemory,
    DreamMemory,
    MemoryWing,
    PreferenceMemory,
    ProjectMemory,
    RecallResult,
    RelationshipTriple,
)
from src.memory.palace.vector import (
    blob_to_embedding,
    cosine_similarity,
    embedding_to_blob,
    text_to_embedding,
)

log = logging.getLogger("ruka.memory.palace")


class MemoryPalace:
    """Mesin Istana Memori (Memory Palace) PROJECT NOCTIS."""

    def __init__(self, db_path: str | Path, event_bus: EventBus | None = None) -> None:
        self.db_path = Path(db_path).resolve()
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.event_bus = event_bus
        self._lock = threading.RLock()
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path), timeout=15.0)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA synchronous=NORMAL;")
        return conn

    def _init_db(self) -> None:
        with self._lock, self._get_connection() as conn:
            # Metadata
            conn.execute("""
                CREATE TABLE IF NOT EXISTS palace_meta (
                    key TEXT PRIMARY KEY,
                    value TEXT
                );
            """)

            # 1. Sayap Hubungan (palace_relationship)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS palace_relationship (
                    id TEXT PRIMARY KEY,
                    subject TEXT NOT NULL,
                    predicate TEXT NOT NULL,
                    object TEXT NOT NULL,
                    confidence REAL DEFAULT 1.0,
                    provenance TEXT DEFAULT '',
                    created_at REAL NOT NULL,
                    is_deleted INTEGER DEFAULT 0,
                    delete_reason TEXT
                );
            """)

            # 2. Sayap Proyek (palace_project)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS palace_project (
                    id TEXT PRIMARY KEY,
                    repo TEXT NOT NULL,
                    kind TEXT NOT NULL,
                    body TEXT NOT NULL,
                    rationale TEXT DEFAULT '',
                    status TEXT DEFAULT 'active',
                    superseded_by TEXT,
                    embedding BLOB,
                    created_at REAL NOT NULL,
                    is_deleted INTEGER DEFAULT 0,
                    delete_reason TEXT
                );
            """)

            # 3. Sayap Preferensi (palace_preference)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS palace_preference (
                    id TEXT PRIMARY KEY,
                    key TEXT UNIQUE NOT NULL,
                    value TEXT NOT NULL,
                    signal_count INTEGER DEFAULT 1,
                    confidence REAL DEFAULT 0.5,
                    created_at REAL NOT NULL,
                    is_deleted INTEGER DEFAULT 0,
                    delete_reason TEXT
                );
            """)

            # 4. Sayap Harian (palace_daily)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS palace_daily (
                    id TEXT PRIMARY KEY,
                    timestamp REAL NOT NULL,
                    session_id TEXT DEFAULT '',
                    summary TEXT NOT NULL,
                    highlights_json TEXT DEFAULT '[]',
                    embedding BLOB,
                    is_deleted INTEGER DEFAULT 0,
                    delete_reason TEXT
                );
            """)

            # 5. Sayap Mimpi (palace_dream)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS palace_dream (
                    id TEXT PRIMARY KEY,
                    topic TEXT NOT NULL,
                    reflection TEXT NOT NULL,
                    abstraction_level INTEGER DEFAULT 1,
                    created_at REAL NOT NULL,
                    is_deleted INTEGER DEFAULT 0,
                    delete_reason TEXT
                );
            """)

            # FTS5 Virtual Table untuk BM25 Full-Text Search lintas sayap
            try:
                conn.execute("""
                    CREATE VIRTUAL TABLE IF NOT EXISTS palace_fts USING fts5(
                        entry_id UNINDEXED,
                        wing UNINDEXED,
                        content,
                        tokenize = 'unicode61'
                    );
                """)
            except sqlite3.OperationalError:
                # Fallback jika module fts5 belum aktif di build sqlite tertentu
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS palace_fts (
                        entry_id TEXT,
                        wing TEXT,
                        content TEXT
                    );
                """)

            conn.commit()

    # --------------------------------------------------------------------------
    # 1. API: remember (Penyimpanan Memori Berstruktur)
    # --------------------------------------------------------------------------

    def remember(
        self,
        wing: str | MemoryWing,
        content: Any = None,
        **kwargs: Any,
    ) -> str:
        """Menyimpan ingatan baru ke salah satu dari 5 sayap Memory Palace."""
        wing_enum = MemoryWing(wing) if not isinstance(wing, MemoryWing) else wing
        if content is None:
            content = kwargs
        elif isinstance(content, dict) and kwargs:
            content = {**content, **kwargs}

        with self._lock, self._get_connection() as conn:
            entry_id = ""
            fts_content = ""

            if wing_enum == MemoryWing.RELATIONSHIP:
                # content: dict atau tuple (subject, predicate, object)
                if isinstance(content, (tuple, list)) and len(content) >= 3:
                    s, p, o = content[0], content[1], content[2]
                elif isinstance(content, dict):
                    s = content["subject"]
                    p = content["predicate"]
                    o = content.get("object", content.get("object_", content.get("obj", "")))
                else:
                    raise ValueError("Konten hubungan harus berupa tuple (s, p, o) atau dict.")

                item = RelationshipTriple(
                    subject=str(s),
                    predicate=str(p),
                    object=str(o),
                    confidence=float(kwargs.get("confidence", 1.0)),
                    provenance=str(kwargs.get("provenance", "conversation")),
                )
                entry_id = item.id
                fts_content = item.text_representation()
                conn.execute(
                    """
                    INSERT INTO palace_relationship (id, subject, predicate, object, confidence, provenance, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (item.id, item.subject, item.predicate, item.object, item.confidence, item.provenance, item.created_at),
                )

            elif wing_enum == MemoryWing.PROJECT:
                repo = str(kwargs.get("repo", content.get("repo", "current") if isinstance(content, dict) else "current"))
                kind = str(kwargs.get("kind", content.get("kind", "decision") if isinstance(content, dict) else "decision"))
                body = str(content if isinstance(content, str) else content.get("body", ""))
                rationale = str(kwargs.get("rationale", content.get("rationale", "") if isinstance(content, dict) else ""))

                item = ProjectMemory(repo=repo, kind=kind, body=body, rationale=rationale)
                entry_id = item.id
                fts_content = item.text_representation()
                vec = text_to_embedding(fts_content)
                blob = embedding_to_blob(vec)

                # Jika menggantikan keputusan lama
                supersedes = kwargs.get("supersedes")
                if supersedes:
                    conn.execute(
                        "UPDATE palace_project SET status = 'superseded', superseded_by = ? WHERE id = ?",
                        (entry_id, supersedes),
                    )

                conn.execute(
                    """
                    INSERT INTO palace_project (id, repo, kind, body, rationale, status, embedding, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (item.id, item.repo, item.kind, item.body, item.rationale, item.status, blob, item.created_at),
                )

            elif wing_enum == MemoryWing.PREFERENCE:
                key = str(kwargs.get("key", content.get("key", "") if isinstance(content, dict) else ""))
                val = str(kwargs.get("value", content.get("value", "") if isinstance(content, dict) else (content if isinstance(content, str) else "")))
                if not key:
                    raise ValueError("Preferensi membutuhkan parameter 'key'.")

                row = conn.execute("SELECT id, signal_count, confidence FROM palace_preference WHERE key = ?", (key,)).fetchone()
                if row:
                    entry_id = row["id"]
                    new_signals = row["signal_count"] + 1
                    new_conf = min(1.0, 0.4 + (new_signals * 0.2))
                    conn.execute(
                        "UPDATE palace_preference SET value = ?, signal_count = ?, confidence = ?, is_deleted = 0 WHERE id = ?",
                        (val, new_signals, new_conf, entry_id),
                    )
                    if new_signals >= 3:
                        fts_content = f"Preferensi {key}: {val}"
                else:
                    item = PreferenceMemory(key=key, value=val, signal_count=1, confidence=0.5)
                    entry_id = item.id
                    conn.execute(
                        """
                        INSERT INTO palace_preference (id, key, value, signal_count, confidence, created_at)
                        VALUES (?, ?, ?, ?, ?, ?)
                        """,
                        (item.id, item.key, item.value, item.signal_count, item.confidence, item.created_at),
                    )

            elif wing_enum == MemoryWing.DAILY:
                summary = str(content if isinstance(content, str) else content.get("summary", ""))
                session_id = str(kwargs.get("session_id", content.get("session_id", "") if isinstance(content, dict) else ""))
                highlights = kwargs.get("highlights", content.get("highlights", []) if isinstance(content, dict) else [])

                item = DailyMemory(summary=summary, session_id=session_id, highlights=highlights)
                entry_id = item.id
                fts_content = item.text_representation()
                vec = text_to_embedding(fts_content)
                blob = embedding_to_blob(vec)

                conn.execute(
                    """
                    INSERT INTO palace_daily (id, timestamp, session_id, summary, highlights_json, embedding)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (item.id, item.timestamp, item.session_id, item.summary, json.dumps(item.highlights), blob),
                )

            elif wing_enum == MemoryWing.DREAM:
                topic = str(kwargs.get("topic", content.get("topic", "reflection") if isinstance(content, dict) else "reflection"))
                reflection = str(content if isinstance(content, str) else content.get("reflection", ""))
                abs_lvl = int(kwargs.get("abstraction_level", 1))

                item = DreamMemory(topic=topic, reflection=reflection, abstraction_level=abs_lvl)
                entry_id = item.id
                fts_content = item.text_representation()

                conn.execute(
                    """
                    INSERT INTO palace_dream (id, topic, reflection, abstraction_level, created_at)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (item.id, item.topic, item.reflection, item.abstraction_level, item.created_at),
                )

            # Indeks FTS5
            if entry_id and fts_content:
                conn.execute("DELETE FROM palace_fts WHERE entry_id = ?", (entry_id,))
                conn.execute(
                    "INSERT INTO palace_fts (entry_id, wing, content) VALUES (?, ?, ?)",
                    (entry_id, wing_enum.value, fts_content),
                )

            conn.commit()

        # Pancarkan event ke EventBus V3
        if self.event_bus:
            self.event_bus.publish(
                Event(
                    event_type="memory.remembered",
                    source="memory_palace",
                    namespace=OrganNamespace.MEMORY.value,
                    payload={"wing": wing_enum.value, "entry_id": entry_id},
                )
            )

        return entry_id

    # --------------------------------------------------------------------------
    # 2. API: recall (Hybrid Retrieval + Reciprocal Rank Fusion k=60)
    # --------------------------------------------------------------------------

    def recall(
        self,
        query: str,
        wings: list[str | MemoryWing] | None = None,
        top_k: int = 6,
    ) -> list[RecallResult]:
        """Temu-balik hibrida 3-jalur (BM25 + Vektor 512-dim + Graf Entitas) dengan RRF k=60 (FR-ME-03)."""
        if not query or not query.strip():
            return []

        target_wings = {MemoryWing(w).value if isinstance(w, MemoryWing) else str(w) for w in wings} if wings else None
        q_tokens = [t.lower() for t in query.split() if len(t) >= 2]
        query_vec = text_to_embedding(query)

        candidates: dict[str, dict[str, Any]] = {}
        bm25_ranks: dict[str, int] = {}
        vector_ranks: dict[str, int] = {}
        graph_ranks: dict[str, int] = {}

        with self._lock, self._get_connection() as conn:
            # === JALUR 1: BM25 (FTS5) ===
            try:
                # Sanitasi query FTS5
                clean_q = " OR ".join(f'"{t}"' for t in q_tokens if t.isalnum())
                if clean_q:
                    cursor = conn.execute(
                        """
                        SELECT entry_id, wing, content, rank
                        FROM palace_fts
                        WHERE palace_fts MATCH ?
                        ORDER BY rank
                        LIMIT 20
                        """,
                        (clean_q,),
                    )
                    for rank_idx, row in enumerate(cursor.fetchall(), start=1):
                        eid = row["entry_id"]
                        w = row["wing"]
                        if target_wings and w not in target_wings:
                            continue
                        if w == MemoryWing.PREFERENCE.value:
                            pref_row = conn.execute("SELECT signal_count FROM palace_preference WHERE id = ?", (eid,)).fetchone()
                            if pref_row and pref_row["signal_count"] < 3:
                                continue
                        bm25_ranks[eid] = rank_idx
                        candidates[eid] = {
                            "entry_id": eid,
                            "wing": MemoryWing(w),
                            "content": row["content"],
                            "provenance": {"bm25_match": True},
                            "sources": {"bm25"},
                        }
            except Exception as e_fts:
                log.debug("BM25 FTS5 fallback query: %s", e_fts)

            # === JALUR 2: Vektor Kosinus (512-Dim BLOB) ===
            vec_scored: list[tuple[str, str, str, float]] = []

            # Proyek
            if not target_wings or MemoryWing.PROJECT.value in target_wings:
                cur = conn.execute(
                    "SELECT id, repo, kind, body, rationale, embedding FROM palace_project WHERE is_deleted = 0"
                )
                for r in cur.fetchall():
                    blob = r["embedding"]
                    if blob:
                        v = blob_to_embedding(blob)
                        sim = cosine_similarity(query_vec, v)
                        if sim > 0.15:
                            c_str = f"[{r['repo']}] [{r['kind']}] {r['body']}"
                            vec_scored.append((r["id"], MemoryWing.PROJECT.value, c_str, sim))

            # Harian
            if not target_wings or MemoryWing.DAILY.value in target_wings:
                cur = conn.execute(
                    "SELECT id, summary, embedding FROM palace_daily WHERE is_deleted = 0"
                )
                for r in cur.fetchall():
                    blob = r["embedding"]
                    if blob:
                        v = blob_to_embedding(blob)
                        sim = cosine_similarity(query_vec, v)
                        if sim > 0.15:
                            vec_scored.append((r["id"], MemoryWing.DAILY.value, r["summary"], sim))

            # Urutkan berdasarkan similarity tertinggi
            vec_scored.sort(key=lambda x: x[3], reverse=True)
            for rank_idx, (eid, w_str, content_str, score) in enumerate(vec_scored[:20], start=1):
                vector_ranks[eid] = rank_idx
                if eid not in candidates:
                    candidates[eid] = {
                        "entry_id": eid,
                        "wing": MemoryWing(w_str),
                        "content": content_str,
                        "provenance": {"vector_score": round(score, 3)},
                        "sources": {"vector"},
                    }
                else:
                    candidates[eid]["sources"].add("vector")
                    candidates[eid]["provenance"]["vector_score"] = round(score, 3)

            # === JALUR 3: Graf Entitas (palace_relationship) ===
            if not target_wings or MemoryWing.RELATIONSHIP.value in target_wings:
                graph_matches: list[tuple[str, str, float]] = []
                cur = conn.execute(
                    "SELECT id, subject, predicate, object, confidence, provenance FROM palace_relationship WHERE is_deleted = 0"
                )
                for r in cur.fetchall():
                    s_low, p_low, o_low = r["subject"].lower(), r["predicate"].lower(), r["object"].lower()
                    overlap = sum(1 for tok in q_tokens if tok in s_low or tok in p_low or tok in o_low)
                    if overlap > 0:
                        score = float(r["confidence"]) * (overlap / max(1, len(q_tokens)))
                        c_str = f"{r['subject']} {r['predicate']} {r['object']}"
                        graph_matches.append((r["id"], c_str, score))

                graph_matches.sort(key=lambda x: x[2], reverse=True)
                for rank_idx, (eid, c_str, score) in enumerate(graph_matches[:20], start=1):
                    graph_ranks[eid] = rank_idx
                    if eid not in candidates:
                        candidates[eid] = {
                            "entry_id": eid,
                            "wing": MemoryWing.RELATIONSHIP,
                            "content": c_str,
                            "provenance": {"graph_score": round(score, 3)},
                            "sources": {"graph"},
                        }
                    else:
                        candidates[eid]["sources"].add("graph")
                        candidates[eid]["provenance"]["graph_score"] = round(score, 3)

            # === JALUR PREFERENSI (Tambahan untuk gaya & preferensi aktif) ===
            if not target_wings or MemoryWing.PREFERENCE.value in target_wings:
                cur = conn.execute(
                    "SELECT id, key, value, signal_count, confidence FROM palace_preference WHERE is_deleted = 0 AND signal_count >= 3"
                )
                for r in cur.fetchall():
                    k_low, v_low = r["key"].lower(), r["value"].lower()
                    if any(tok in k_low or tok in v_low for tok in q_tokens):
                        eid = r["id"]
                        c_str = f"Preferensi {r['key']}: {r['value']}"
                        graph_ranks[eid] = 1  # Prioritas tinggi untuk preferensi konsisten
                        if eid not in candidates:
                            candidates[eid] = {
                                "entry_id": eid,
                                "wing": MemoryWing.PREFERENCE,
                                "content": c_str,
                                "provenance": {"signals": r["signal_count"], "confidence": r["confidence"]},
                                "sources": {"preference"},
                            }
                        else:
                            candidates[eid]["sources"].add("preference")

        # === FUSI RECIPROCAL RANK FUSION (RRF k = 60) ===
        K = 60.0
        final_scores: list[RecallResult] = []

        for eid, item in candidates.items():
            rrf_score = 0.0
            if eid in bm25_ranks:
                rrf_score += 1.0 / (K + bm25_ranks[eid])
            if eid in vector_ranks:
                rrf_score += 1.0 / (K + vector_ranks[eid])
            if eid in graph_ranks:
                rrf_score += 1.0 / (K + graph_ranks[eid])

            final_scores.append(
                RecallResult(
                    entry_id=eid,
                    wing=item["wing"],
                    content=item["content"],
                    score=round(rrf_score, 5),
                    provenance=item["provenance"],
                    match_sources=sorted(list(item["sources"])),
                )
            )

        # Urutkan berdasarkan skor RRF dan ambil 6 potongan memori terbaik (FR-ME-03)
        final_scores.sort(key=lambda x: x.score, reverse=True)
        top_results = final_scores[:top_k]

        if self.event_bus:
            self.event_bus.publish(
                Event(
                    event_type="memory.recalled",
                    source="memory_palace",
                    namespace=OrganNamespace.MEMORY.value,
                    payload={"query": query, "found_count": len(top_results)},
                )
            )

        return top_results

    # --------------------------------------------------------------------------
    # 3. API: forget (Penghapusan Lunak / Soft-Delete dengan Alasan Wajib)
    # --------------------------------------------------------------------------

    def forget(
        self,
        entry_id: str,
        reason: str,
        wing: str | MemoryWing | None = None,
    ) -> bool:
        """Melakukan soft-delete pada rekaman memori. Wajib menyertakan alasan penghapusan (FR-ME-02)."""
        if not reason or not reason.strip():
            raise ValueError("alasan penghapusan (reason) wajib diisi untuk soft-delete.")

        found = False
        tables = [
            "palace_relationship",
            "palace_project",
            "palace_preference",
            "palace_daily",
            "palace_dream",
        ]
        if wing:
            w_str = MemoryWing(wing).value if isinstance(wing, MemoryWing) else str(wing)
            tables = [f"palace_{w_str}"]

        with self._lock, self._get_connection() as conn:
            for tbl in tables:
                cursor = conn.execute(
                    f"UPDATE {tbl} SET is_deleted = 1, delete_reason = ? WHERE id = ? AND is_deleted = 0",
                    (reason.strip(), entry_id),
                )
                if cursor.rowcount > 0:
                    found = True
                    break

            # Bersihkan dari FTS agar tidak lagi muncul di pencarian
            if found:
                conn.execute("DELETE FROM palace_fts WHERE entry_id = ?", (entry_id,))
                conn.commit()

        if found and self.event_bus:
            self.event_bus.publish(
                Event(
                    event_type="memory.forgotten",
                    source="memory_palace",
                    namespace=OrganNamespace.MEMORY.value,
                    payload={"entry_id": entry_id, "reason": reason},
                )
            )

        return found

    # --------------------------------------------------------------------------
    # 4. API: inspect (Audit & Introspeksi Memori Tanpa Kebocoran SQL)
    # --------------------------------------------------------------------------

    def inspect(
        self,
        wing: str | MemoryWing | None = None,
        include_deleted: bool = False,
    ) -> dict[str, Any]:
        """Melakukan audit transparansi isi Memory Palace untuk Young Lord (FR-ME-02)."""
        res: dict[str, Any] = {"database": str(self.db_path), "wings": {}}

        wing_targets = [
            MemoryWing.RELATIONSHIP,
            MemoryWing.PROJECT,
            MemoryWing.PREFERENCE,
            MemoryWing.DAILY,
            MemoryWing.DREAM,
        ]
        if wing:
            w_enum = MemoryWing(wing) if not isinstance(wing, MemoryWing) else wing
            wing_targets = [w_enum]

        del_filter = "" if include_deleted else "WHERE is_deleted = 0"

        with self._lock, self._get_connection() as conn:
            for w in wing_targets:
                tbl = f"palace_{w.value}"
                rows = conn.execute(f"SELECT * FROM {tbl} {del_filter} ORDER BY rowid DESC LIMIT 50").fetchall()
                count = conn.execute(f"SELECT COUNT(*) as c FROM {tbl} {del_filter}").fetchone()["c"]

                items: list[dict[str, Any]] = []
                for r in rows:
                    d = dict(r)
                    if "embedding" in d:
                        del d["embedding"]  # Sembunyikan binary blob dari json inspect
                    items.append(d)

                res["wings"][w.value] = {
                    "total_count": count,
                    "sample_items": items,
                }

        return res
