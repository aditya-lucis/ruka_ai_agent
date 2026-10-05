# -*- coding: utf-8 -*-
"""Unit tests for NOCTIS Memory Palace (Milestone B.2 — FR-ME-01 to FR-ME-03)."""
from __future__ import annotations

from pathlib import Path
import time
import pytest

from src.gateway.events import EventBus
from src.memory.palace import (
    MemoryPalace,
    MemoryWing,
    RelationshipTriple,
    ProjectMemory,
    PreferenceMemory,
    DailyMemory,
    DreamMemory,
    RecallResult,
)


class TestMemoryPalaceCore:
    def test_remember_all_five_wings(self, tmp_path: Path) -> None:
        bus = EventBus()
        db_file = tmp_path / "palace.db"
        palace = MemoryPalace(db_file, event_bus=bus)

        # 1. Relationship
        rel_id = palace.remember(
            MemoryWing.RELATIONSHIP,
            ("Young Lord", "loves", "system architecture"),
            confidence=0.95,
            provenance="dialogue_turn_1",
        )
        assert rel_id.startswith("rel_")

        # 2. Project
        proj_id = palace.remember(
            MemoryWing.PROJECT,
            {"body": "Mengadopsi EventBus V3 dengan namespace per organ", "rationale": "Decoupling mutlak"},
            repo="ruka",
            kind="decision",
        )
        assert proj_id.startswith("proj_")

        # 3. Preference
        pref_id = palace.remember(
            MemoryWing.PREFERENCE,
            {"key": "code_style", "value": "clean_architecture"},
        )
        assert pref_id.startswith("pref_")

        # 4. Daily
        day_id = palace.remember(
            MemoryWing.DAILY,
            {"summary": "Diskusi arsitektur NOCTIS bersama Young Lord", "session_id": "sess_01", "highlights": ["Fase B", "palace.db"]},
        )
        assert day_id.startswith("day_")

        # 5. Dream
        drm_id = palace.remember(
            MemoryWing.DREAM,
            {"topic": "Kedaulatan Lokal", "reflection": "Ruka menjaga seluruh data di mesin pengguna tanpa bocor"},
            abstraction_level=2,
        )
        assert drm_id.startswith("drm_")

        # Cek inspect
        audit = palace.inspect()
        assert audit["wings"]["relationship"]["total_count"] == 1
        assert audit["wings"]["project"]["total_count"] == 1
        assert audit["wings"]["preference"]["total_count"] == 1
        assert audit["wings"]["daily"]["total_count"] == 1
        assert audit["wings"]["dream"]["total_count"] == 1

    def test_preference_conservative_learner_threshold(self, tmp_path: Path) -> None:
        db_file = tmp_path / "palace.db"
        palace = MemoryPalace(db_file)

        # Sinyal 1
        palace.remember(MemoryWing.PREFERENCE, key="tone", value="aristocratic")
        recalled_1 = palace.recall("tone", wings=[MemoryWing.PREFERENCE])
        # Belum aktif karena ambang signal_count < 3
        assert len(recalled_1) == 0

        # Sinyal 2
        palace.remember(MemoryWing.PREFERENCE, key="tone", value="aristocratic")
        recalled_2 = palace.recall("tone", wings=[MemoryWing.PREFERENCE])
        assert len(recalled_2) == 0

        # Sinyal 3 (ambang tercapai!)
        palace.remember(MemoryWing.PREFERENCE, key="tone", value="aristocratic")
        recalled_3 = palace.recall("tone", wings=[MemoryWing.PREFERENCE])
        assert len(recalled_3) == 1
        assert "aristocratic" in recalled_3[0].content

    def test_project_decision_superseded_by_chain(self, tmp_path: Path) -> None:
        db_file = tmp_path / "palace.db"
        palace = MemoryPalace(db_file)

        id1 = palace.remember(
            MemoryWing.PROJECT,
            body="Menggunakan memory v1 lama",
            kind="decision",
        )

        id2 = palace.remember(
            MemoryWing.PROJECT,
            body="Bermigrasi ke Memory Palace 5 sayap",
            kind="decision",
            supersedes=id1,
        )

        audit = palace.inspect(wing=MemoryWing.PROJECT)
        items = audit["wings"]["project"]["sample_items"]
        old_item = next(it for it in items if it["id"] == id1)
        new_item = next(it for it in items if it["id"] == id2)

        assert old_item["status"] == "superseded"
        assert old_item["superseded_by"] == id2
        assert new_item["status"] == "active"

    def test_hybrid_recall_and_rrf_scoring(self, tmp_path: Path) -> None:
        db_file = tmp_path / "palace.db"
        palace = MemoryPalace(db_file)

        palace.remember(
            MemoryWing.PROJECT,
            body="Implementasi SQLite WAL mode dengan FTS5 dan vektor",
            repo="ruka_persistence",
        )
        palace.remember(
            MemoryWing.RELATIONSHIP,
            ("Young Lord", "membangun", "proyek Noctis"),
            confidence=1.0,
        )
        palace.remember(
            MemoryWing.DAILY,
            summary="Diskusi implementasi EventBus dan Memory Palace",
            highlights=["FTS5", "RRF"],
        )

        # Temu balik dengan kueri yang relevan
        results = palace.recall("proyek Noctis dan Memory Palace SQLite")
        assert len(results) > 0
        assert len(results) <= 6

        # Pastikan ada provenance dan score RRF
        top = results[0]
        assert isinstance(top, RecallResult)
        assert top.score > 0
        assert isinstance(top.provenance, dict)
        assert len(top.match_sources) > 0

    def test_forget_requires_reason_and_soft_deletes(self, tmp_path: Path) -> None:
        db_file = tmp_path / "palace.db"
        palace = MemoryPalace(db_file)

        rel_id = palace.remember(MemoryWing.RELATIONSHIP, ("Alice", "teman", "Bob"))

        # Forget tanpa alasan harus gagal
        with pytest.raises(ValueError, match="alasan"):
            palace.forget(rel_id, reason="")

        with pytest.raises(ValueError, match="alasan"):
            palace.forget(rel_id, reason="   ")

        # Forget dengan alasan sah
        assert palace.forget(rel_id, reason="Perubahan relasi sosial")

        # Tidak muncul lagi di recall
        res = palace.recall("Alice teman Bob", wings=[MemoryWing.RELATIONSHIP])
        assert len(res) == 0

        # Muncul di inspect jika include_deleted=True
        audit_live = palace.inspect(include_deleted=False)
        assert audit_live["wings"]["relationship"]["total_count"] == 0

        audit_all = palace.inspect(include_deleted=True)
        assert audit_all["wings"]["relationship"]["total_count"] == 1
        deleted_item = audit_all["wings"]["relationship"]["sample_items"][0]
        assert deleted_item["is_deleted"] == 1
        assert deleted_item["delete_reason"] == "Perubahan relasi sosial"


class TestAmnesiaVerification2020:
    """Uji amnesia 20 dari 20 (SAD 5.2 & Kriteria Boss Fight 4):
    Simpan 20 memori beragam, matikan koneksi/restart instance, dan pastikan seluruh 20/20 terbaca akurat.
    """

    def test_amnesia_test_20_of_20(self, tmp_path: Path) -> None:
        db_file = tmp_path / "palace.db"
        p1 = MemoryPalace(db_file)

        saved_ids = []
        # Tulis 20 memori spesifik
        for i in range(1, 21):
            eid = p1.remember(
                MemoryWing.RELATIONSHIP,
                (f"Entitas_{i}", "terhubung_dengan", f"Node_{i}"),
                provenance=f"test_run_{i}",
            )
            saved_ids.append((eid, f"Entitas_{i} terhubung_dengan Node_{i}"))

        assert len(saved_ids) == 20

        # Restart palace dengan instans baru
        del p1
        p2 = MemoryPalace(db_file)

        # Verifikasi bahwa seluruh 20 memori terselamatkan (20/20)
        audit = p2.inspect(wing=MemoryWing.RELATIONSHIP)
        assert audit["wings"]["relationship"]["total_count"] == 20

        for eid, text in saved_ids:
            found = p2.recall(text, wings=[MemoryWing.RELATIONSHIP], top_k=1)
            assert len(found) == 1
            assert found[0].entry_id == eid


class TestSleepConsolidator:
    def test_sleep_consolidation_three_stages(self, tmp_path: Path) -> None:
        from src.memory.palace import SleepConsolidator
        bus = EventBus()
        db_file = tmp_path / "palace_sleep.db"
        palace = MemoryPalace(db_file, event_bus=bus)

        # 1. Masukkan daily digest
        palace.remember(MemoryWing.DAILY, {"summary": "Diskusi arsitektur dan EventBus V3"})
        palace.remember(MemoryWing.DAILY, {"summary": "Pengujian 13 alat Blood Contract"})

        # 2. Masukkan konflik preferensi (key sama, value beda)
        p1 = palace.remember(MemoryWing.PREFERENCE, {"key": "theme", "value": "light"})
        time.sleep(0.01)
        p2 = palace.remember(MemoryWing.PREFERENCE, {"key": "theme", "value": "dark"})

        # 3. Masukkan relasi lama dan duplikatnya untuk memicu resolusi konflik stage 2
        rel_id1 = palace.remember(
            MemoryWing.RELATIONSHIP,
            ("Lord", "trusts", "Ruka"),
            confidence=0.7,
        )
        time.sleep(0.01)
        rel_id2 = palace.remember(
            MemoryWing.RELATIONSHIP,
            ("Lord", "trusts", "Ruka"),
            confidence=1.0,
        )

        consolidator = SleepConsolidator(palace=palace, event_bus=bus, half_life_days=10.0)

        # Simulasikan waktu 20 hari kemudian
        now_future = time.time() + (20 * 86400.0)
        events = []
        bus.subscribe("palace.*", lambda e: events.append(e))

        report = consolidator.run_consolidation(current_time=now_future)
        assert report.daily_summaries_processed == 2
        assert report.dreams_generated == 1
        assert report.conflicts_resolved >= 1
        assert report.decayed_memories_count >= 1

        bus.drain()
        assert any(e.event_type == "palace.consolidate" for e in events)

        # Verifikasi bahwa mimpi baru tercipta di sayap DREAM
        audit = palace.inspect(wing=MemoryWing.DREAM)
        assert audit["wings"]["dream"]["total_count"] >= 1

        # Verifikasi bahwa preferensi lama di-soft delete
        audit_pref = palace.inspect(wing=MemoryWing.PREFERENCE, include_deleted=False)
        assert audit_pref["wings"]["preference"]["total_count"] == 1

