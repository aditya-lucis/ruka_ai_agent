"""Relationship model — personalisasi dengan pagar privasi.
INVARIAN DESAIN: output model HANYA memengaruhi penyajian
(bentuk, panjang, formalitas) — tidak pernah isi keyakinan
atau keputusan. Test menjaga invarian ini secara struktural.
"""
from __future__ import annotations
import json
from pathlib import Path
from pydantic import BaseModel, Field

class CommunicationPreference(BaseModel):
    verbosity: str = "balanced"            # terse | balanced | thorough
    style: str = "santai-sopan"            # formal | santai-sopan | keduanya
    evidence_first: bool = True             # angka/bukti sebelum opini
    language: str = "id"                    # kode bahasa utama
    updated_via: str = "observed"

class ProjectContext(BaseModel):
    project_name: str
    repo_path: str | None = None
    stack: list[str] = Field(default_factory=list)
    decisions: list[str] = Field(default_factory=list)   # keputusan arsitektur tercatat
    active: bool = True

class TaskPattern(BaseModel):
    """Pola URUTAN cara meminta — bukan profil psikologis."""
    research_before_code: bool | None = None
    prefers_demo_first: bool | None = None
    sample_n_interactions: int = 0

class RelationshipModel(BaseModel):
    user_name: str
    communication: CommunicationPreference = Field(default_factory=CommunicationPreference)
    projects: list[ProjectContext] = Field(default_factory=list)
    task_pattern: TaskPattern | None = None

    # -- modul penyajian: SATU-SATUNYA konsumen yang sah --
    def presentation_directives(self) -> dict[str, object]:
        """Konsumsi hanya untuk penyajian. Bentuk, bukan isi."""
        c = self.communication
        out: dict[str, object] = {
            "verbosity": c.verbosity,
            "language": c.language,
            "evidence_first": c.evidence_first,
        }
        active = [p for p in self.projects if p.active]
        if active:
            out["active_project"] = active[0].project_name
        if self.task_pattern and self.task_pattern.sample_n_interactions >= 5:
            out["research_first"] = self.task_pattern.research_before_code
        return out

class PrivacyBoundary:
    """Hak user sebagai operasi kelas satu — bukan halaman FAQ."""
    def __init__(self, data_dir: Path, model: RelationshipModel,
                 memory_store) -> None:
        self._dir = Path(data_dir)
        self._model = model
        self._memories = memory_store

    def export_user_data(self) -> dict:
        """HAK LIHAT: seluruh data user dalam format terbaca."""
        prefs = self._model.model_dump()
        memories = [r.model_dump() for r in self._memories.query_memories(
            kinds=["preference", "episodic", "project", "identity"],
            active_only=False)]      # termasuk arsip — transparan
        return {
            "relationship": prefs,
            "memories": memories,
            "format": "ruka-export-v1",
        }

    def delete_user_data(self) -> dict:
        """HAK HAPUS: hilangkan relasi + memori user; sertifikat
        deletion dikembalikan. Log audit tetap (anonim, tanpa isi)."""
        removed_mem = self._memories.delete_all_user_memories()
        rel_path = self._dir / "relationship.json"
        if rel_path.exists():
            rel_path.unlink()
        return {
            "deleted": True,
            "relationship_removed": True,
            "memories_removed": removed_mem,
            "certificate": f"ruka-del-{self._model.user_name}-complete",
        }

    def set_permissions(self, *, task_pattern: bool = True,
                          project_context: bool = True) -> RelationshipModel:
        """HAK UBAH IZIN: matikan komponen; sistem tetap hidup."""
        if not task_pattern:
            self._model.task_pattern = None
        if not project_context:
            self._model.projects = [p for p in self._model.projects if not p.active]
        return self._model
