import pytest
from ruka_persistence.memory.preference import PreferencePipeline
from ruka_persistence.memory.types import PreferenceObservation

def test_preference_pipeline():
    pipeline = PreferencePipeline()
    
    # 1. New observation
    obs1 = PreferenceObservation(observed_behavior="Bos suka minum kopi", evidence_strength=1.0)
    p = pipeline.observe(obs1)
    
    assert p.status == "candidate"
    assert p.support == 1
    assert p.confidence == 0.12  # 0.0 + 0.12 * (0.5 + 0.5 * 1.0)
    
    # 2. Add two more positive observations to reach stable (need 3)
    pipeline.observe(PreferenceObservation(observed_behavior="Bos suka minum kopi", evidence_strength=1.0))
    p = pipeline.observe(PreferenceObservation(observed_behavior="Bos suka minum kopi", evidence_strength=1.0))
    
    assert p.support == 3
    assert p.status == "candidate" # Wait, candidate because confidence might not be >= 0.5?
    # Confidence: 0.12 + 0.12 + 0.12 = 0.36. 
    # To reach stable, confidence needs to be >= 0.5. Let's add more.
    pipeline.observe(PreferenceObservation(observed_behavior="Bos suka minum kopi", evidence_strength=1.0))
    p = pipeline.observe(PreferenceObservation(observed_behavior="Bos suka minum kopi", evidence_strength=1.0))
    
    assert p.status == "stable"
    
    # 3. Add contradiction
    obs_contra = PreferenceObservation(observed_behavior="Bos suka minum kopi", evidence_strength=0.1) # low evidence -> contra
    p = pipeline.observe(obs_contra)
    
    assert p.contradiction == 1
    # Check if ratio drops below 3.0. support=5, contra=1 -> ratio 5.0 (still stable)
    # BUT confidence drops from 0.60 to 0.30, which is < 0.5. So it drops to candidate!
    assert p.status == "candidate"
    
    # Add more contra to drop ratio
    pipeline.observe(PreferenceObservation(observed_behavior="Bos suka minum kopi", evidence_strength=0.1))
    p = pipeline.observe(PreferenceObservation(observed_behavior="Bos suka minum kopi", evidence_strength=0.1))
    
    # support=5, contra=3 -> ratio 1.66 < 3.0 -> retract to candidate (or retracted if criteria met)
    assert p.status == "candidate"
    
def test_preference_forget():
    pipeline = PreferencePipeline()
    pipeline.observe(PreferenceObservation(observed_behavior="Bos suka makan durian", evidence_strength=1.0))
    
    assert pipeline.summary()["total"] == 1
    
    res = pipeline.forget("Bos suka makan durian")
    assert res is True
    assert pipeline.summary()["total"] == 0
