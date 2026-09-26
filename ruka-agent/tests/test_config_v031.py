import pytest
from src.config import ConfigError, load_settings

BASE = {
    "GEMINI_API_KEY": "test-key-not-real",
    "RUKA_MODEL": "gemini-3.8-flash",
}

def test_missing_key_fails_fast():
    with pytest.raises(ConfigError, match="GEMINI_API_KEY"):
        load_settings(env={})

def test_invalid_environment_rejected():
    with pytest.raises(ConfigError, match="RUKA_ENVIRONMENT"):
        load_settings(env={**BASE, "RUKA_ENVIRONMENT": "prod"})

def test_model_falls_back_to_default():
    s = load_settings(env={**BASE, "RUKA_MODEL": " "})
    assert s.model == "gemini-3.8-flash"

def test_bad_budget_rejected():
    with pytest.raises(ConfigError, match="positif"):
        load_settings(env={**BASE, "RUKA_TOKEN_BUDGET": "-5"})

def test_snapshot_never_leaks_key():
    s = load_settings(env=BASE)
    snap = s.safe_snapshot()
    assert "test-key-not-real" not in str(snap)
    assert snap["api_key_present"] is True
