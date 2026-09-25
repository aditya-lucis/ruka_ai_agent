from pathlib import Path
import pytest
from src.identity.self_model import SelfModel, build_self_model, save, load

def test_capabilities_grounded_from_registry():
    m = build_self_model(tool_names=["calculator", "search_docs"],
                         has_memory=True, has_rag=True, user_name="Aditya")
    assert "calculator" in m.capabilities[0]
    assert "mengingat" in " ".join(m.capabilities)
    assert "tidak sadar" in " ".join(m.limitations)

def test_identity_card_always_lists_claim_rules():
    m = build_self_model(tool_names=[], has_memory=False, has_rag=False)
    card = m.identity_card()
    assert "JANGAN klaim" in card
    assert "sadar" in card

def test_roundtrip_persistence(tmp_path: Path):
    m = build_self_model(tool_names=["calculator"],
                         has_memory=True, has_rag=True, user_name="Aditya")
    p = tmp_path / "identity.json"
    save(m, p)
    m2 = load(p)
    assert m2.user_name == "Aditya"
    assert m2.capabilities == m.capabilities

def test_inflated_capabilities_are_rejected():
    """Boot guard: klaim yang melebihi kenyataan harus GAGAL."""
    truth = build_self_model(tool_names=["calculator"],
                             has_memory=False, has_rag=False)
    inflated = truth.model_copy(update={"capabilities": truth.capabilities + ["membaca email Bos"]})
    with pytest.raises(ValueError):
        verify_against_reality(inflated, tool_names=["calculator"],
                               has_memory=False, has_rag=False)

def verify_against_reality(model: SelfModel, tool_names: list[str],
                           has_memory: bool, has_rag: bool) -> None:
    rebuilt = build_self_model(tool_names=tool_names,
                               has_memory=has_memory, has_rag=has_rag)
    allowed = set(rebuilt.capabilities)
    claimed = set(model.capabilities)
    if not claimed <= allowed:
        raise ValueError(
            f"Self-model mengklaim kapabilitas tanpa ground: "
            f"{sorted(claimed - allowed)}"
        )
