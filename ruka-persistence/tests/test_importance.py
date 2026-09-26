import pytest
from ruka_persistence.memory.importance import ImportanceScorer, DEFAULT_HALF_LIFE_DAYS

def test_importance_scorer_floor():
    scorer = ImportanceScorer()
    
    # Fresh event, 0 everything else
    score = scorer.score(
        age_days=0.0,
        frequency=0,
        emotional=0.0,
        task_relevance=0.0,
        user_importance=0.0,
        memory_kind="episodic"
    )
    
    # Weights: recency=0.25, freq=0.25, emo=0.15, task=0.20, user=0.15
    # Recency (age=0) -> 1.0. Score = 0.25 * 1.0 = 0.25
    assert score == 0.25

def test_importance_scorer_full():
    scorer = ImportanceScorer()
    score = scorer.score(
        age_days=0.0,
        frequency=20,
        emotional=1.0,
        task_relevance=1.0,
        user_importance=1.0,
        memory_kind="episodic"
    )
    # Freq(20) -> ~1.0
    # Everything is 1.0 -> max score ~ 1.0
    assert score > 0.95

def test_importance_decay():
    scorer = ImportanceScorer()
    hl = DEFAULT_HALF_LIFE_DAYS["episodic"] # 30 days
    
    score_fresh = scorer.score(age_days=0.0)
    score_half = scorer.score(age_days=hl)
    
    # Only recency changes from 1.0 to 0.5. Weight is 0.25. So diff should be 0.125
    assert abs(score_fresh - score_half - 0.125) < 0.01

def test_invalid_weights():
    with pytest.raises(ValueError, match="harus berjumlah 1.0"):
        ImportanceScorer(weights={"recency": 0.5, "frequency": 0.5, "emotional": 0.5}) # sum = 1.5
