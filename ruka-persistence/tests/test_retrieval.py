import pytest
from ruka_persistence.memory.retrieval import HybridRetriever, RetrievalCandidate

def test_hybrid_retriever_ranking():
    retriever = HybridRetriever()
    
    # Create mock candidates
    c1 = RetrievalCandidate("c1", "content1", "episodic", [0.1], importance=1.0, age_days=0.0, confidence=1.0)
    c2 = RetrievalCandidate("c2", "content2", "episodic", [0.1], importance=0.5, age_days=30.0, confidence=0.8)
    
    hits = retriever.search("query", [c1, c2], top_k=2)
    
    assert len(hits) == 2
    assert hits[0].memory_id == "c1"  # c1 is fresher and more important
    assert hits[0].rank == 1
    assert hits[1].rank == 2

def test_weight_sensitivity():
    retriever = HybridRetriever()
    
    # 5 candidates to allow tau calculations
    candidates = [
        RetrievalCandidate(f"c{i}", f"content {i}", "episodic", [0.1], importance=0.2*i, age_days=10.0*i, confidence=0.5)
        for i in range(5)
    ]
    
    report = retriever.weight_sensitivity("query", candidates, perturbation=0.10, top_k=5)
    
    # report should have keys like 'alpha+', 'alpha-', etc
    assert "alpha+" in report
    assert "tau" in report["alpha+"]
    assert "beta-" in report
