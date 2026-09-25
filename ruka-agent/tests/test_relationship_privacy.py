import json
from pathlib import Path
import pytest
from src.relationship.preference import (
    CommunicationPreference, PrivacyBoundary, ProjectContext,
    RelationshipModel, TaskPattern)

class FakeMemStore:
    def __init__(self):
        self.deleted = False

    def query_memories(self, kinds, active_only=True):
        return []

    def delete_all_user_memories(self):
        self.deleted = True
        return 0

def _model():
    return RelationshipModel(
        user_name="Aditya",
        communication=CommunicationPreference(verbosity="terse"),
        projects=[ProjectContext(project_name="ruka-agent",
                                 stack=["python", "sqlite"],
                                 decisions=["Interactions API stateless"])],
        task_pattern=TaskPattern(research_before_code=True,
                                 sample_n_interactions=9),
    )

def test_directives_shape_only_whitelist():
    """INVARIAN ANTI-MANIPULASI: hanya bentuk penyajian yang keluar."""
    d = _model().presentation_directives()
    allowed = {"verbosity", "language", "evidence_first",
               "active_project", "research_first"}
    assert set(d) <= allowed
    assert d["verbosity"] == "terse"

def test_export_contains_everything_including_archives():
    m = _model()
    out = PrivacyBoundary(Path("/tmp"), m, FakeMemStore()).export_user_data()
    assert out["format"] == "ruka-export-v1"
    assert out["relationship"]["user_name"] == "Aditya"
    assert "memories" in out

def test_delete_is_complete_and_certified(tmp_path: Path):
    m = _model()
    (tmp_path / "relationship.json").write_text("{}", encoding="utf-8")
    store = FakeMemStore()
    out = PrivacyBoundary(tmp_path, m, store).delete_user_data()
    assert out["deleted"] is True
    assert out["memories_removed"] == 0 and store.deleted
    assert out["certificate"].startswith("ruka-del-Aditya")
    assert not (tmp_path / "relationship.json").exists()

def test_permissions_off_keeps_system_alive():
    m = _model()
    PrivacyBoundary(Path("/tmp"), m, FakeMemStore()).set_permissions(
        task_pattern=False, project_context=False)
    d = m.presentation_directives()
    assert "research_first" not in d and "active_project" not in d
    assert d["verbosity"] == "terse"          # inti tetap hidup
