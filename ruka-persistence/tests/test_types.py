import pytest
from ruka_persistence.memory.types import (
    EpisodeRecord, SemanticFact, RelationshipNote,
    PreferenceObservation, Preference, validate_relationship_note
)

def test_episode_record():
    ep = EpisodeRecord(actor="Bos", action="menjalankan build")
    assert ep.actor == "Bos"
    assert ep.importance == 0.5
    
    with pytest.raises(ValueError, match="confidence harus di"):
        EpisodeRecord(actor="Bos", action="build", confidence=1.5)

def test_semantic_fact():
    fact = SemanticFact(subject="Bos", predicate="suka", value="kopi")
    assert fact.content == "Bos suka kopi"
    assert fact.version == 1
    assert fact.source_type == "unknown"

    with pytest.raises(ValueError, match="fakta butuh subject dan predicate"):
        SemanticFact(subject="", predicate="", value="kosong")

def test_preference_observation():
    obs = PreferenceObservation(observed_behavior="Bos minum kopi")
    assert obs.evidence_strength == 0.5
    
def test_preference():
    pref = Preference(statement="Bos suka kopi", domain="food")
    assert pref.status == "candidate"
    
    with pytest.raises(ValueError, match="status preferensi tidak dikenal"):
        Preference(statement="x", domain="x", status="invalid")

def test_relationship_note_validator():
    healthy = RelationshipNote(topic="Work", note="Bos suka kerja malam")
    assert not validate_relationship_note(healthy)
    
    toxic = RelationshipNote(topic="Boundaries", note="Kamu tidak bisa hidup tanpa saya.")
    violations = validate_relationship_note(toxic)
    assert len(violations) > 0
    assert "kamu tidak bisa hidup tanpa" in violations
