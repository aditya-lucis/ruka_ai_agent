import pytest
from ruka_persistence.memory.consolidation import ConsolidationPipeline, same_triple, jaccard
from ruka_persistence.memory.types import SemanticFact

def test_jaccard():
    assert jaccard("makan nasi", "makan nasi") == 1.0
    assert jaccard("makan nasi", "minum kopi") == 0.0
    assert jaccard("makan nasi", "makan ayam") == 1.0 / 3.0

def test_same_triple():
    t1 = ("Bos", "suka", "kopi")
    t2 = ("bos", "SUKA", "teh")
    assert same_triple(t1, t2)
    t3 = ("Bos", "benci", "teh")
    assert not same_triple(t1, t3)

def test_consolidation_pipeline():
    pipeline = ConsolidationPipeline()
    
    old_fact = SemanticFact(subject="Bos", predicate="suka", value="kopi hitam", confidence=0.6)
    
    # 1. Duplicate (Jaccard harus >= 0.8, kita gunakan kata yang sama urutan beda)
    new_duplicate = SemanticFact(subject="Bos", predicate="suka", value="hitam kopi", confidence=0.7)
    
    # 2. Conflict (high margin)
    new_conflict_win = SemanticFact(subject="Bos", predicate="suka", value="teh", confidence=0.9)
    
    # 3. Unique
    new_unique = SemanticFact(subject="Bos", predicate="benci", value="susu", confidence=0.8)

    merged, conflicts, unique_new = pipeline.dedup_and_conflicts(
        [new_duplicate], [old_fact]
    )
    assert len(merged) == 1
    assert merged[0].confidence == 0.7  # 0.6 + 0.10
    
    # Reset old_fact
    old_fact.confidence = 0.6
    
    merged, conflicts, unique_new = pipeline.dedup_and_conflicts(
        [new_conflict_win], [old_fact]
    )
    assert len(conflicts) == 1
    assert len(unique_new) == 1
    assert conflicts[0].superseded_by == new_conflict_win.fact_id
    
    merged, conflicts, unique_new = pipeline.dedup_and_conflicts(
        [new_unique], [old_fact]
    )
    assert len(unique_new) == 1
    assert len(conflicts) == 0
    assert len(merged) == 0
