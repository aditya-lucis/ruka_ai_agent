import pytest
from src.ruka_perception.perception.types import Modality, PerceptionInput, PerceptionResult
from src.ruka_perception.perception.router import PerceptionRouter
from src.ruka_perception.perception.context import MultimodalContext

def test_router_valid_input():
    router = PerceptionRouter()
    inp = PerceptionInput(modality=Modality.TEXT, text="hello")
    decision = router.route(inp)
    assert decision.modality == Modality.TEXT
    assert decision.handler == "text.represent"

def test_router_override_route():
    router = PerceptionRouter({Modality.TEXT: "custom.text"})
    inp = PerceptionInput(modality=Modality.TEXT, text="hello")
    decision = router.route(inp)
    assert decision.handler == "custom.text"

def test_context_builder_ordering():
    ctx = MultimodalContext()
    ctx.add(PerceptionResult(modality=Modality.AUDIO, summary="audio summary"))
    ctx.add(PerceptionResult(modality=Modality.IMAGE, summary="image summary"))
    ctx.add(PerceptionResult(modality=Modality.TEXT, summary="text summary"))
    
    blocks = ctx.ordered_blocks()
    # text first, then image, then audio
    assert blocks[0]["type"] == "text"
    assert blocks[1]["type"] == "visual"
    assert blocks[2]["type"] == "audio"

def test_context_budget():
    ctx = MultimodalContext()
    ctx.add(PerceptionResult(modality=Modality.TEXT, summary="abcd")) # 4 chars = 1 token
    ctx.add(PerceptionResult(modality=Modality.AUDIO, transcript="abcdefgh")) # 8 chars = 2 tokens (summary) + 2 tokens (transcript) = 4 tokens
    assert ctx.budget_tokens() == 5
