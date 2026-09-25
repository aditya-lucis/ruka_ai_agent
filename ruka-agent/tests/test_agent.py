import pytest
import os
import tempfile
from datetime import datetime
from src.tools.builtin import CalculatorTool, DateTimeTool
from src.tools.registry import ToolRegistry
from src.domain.models import Intent, IntentResult, ToolDecision, TaskPlan, PlanStep
from src.memory.models import MemoryRecord, MemoryKind
from src.retrieval.chunker import chunk_markdown
from src.retrieval.store import VectorStore

def test_calculator_tool():
    calc = CalculatorTool()
    res = calc.execute({"expression": "25 * 4 + 10"}, granted=set())
    assert res == 110.0

def test_calculator_invalid():
    calc = CalculatorTool()
    with pytest.raises(Exception):
        calc.execute({"expression": "import os; os.system('echo hi')"}, granted=set())

def test_datetime_tool():
    dt_tool = DateTimeTool()
    res = dt_tool.execute({"tz": "Asia/Jakarta"}, granted=set())
    assert len(res) > 0

def test_tool_registry():
    registry = ToolRegistry()
    registry.register(CalculatorTool())
    
    decls = registry.declarations()
    assert len(decls) == 1
    assert decls[0]["name"] == "calculator"
    
    exec_res = registry.execute("calculator", {"expression": "100 / 5"}, granted=set())
    assert "result" in exec_res
    assert exec_res["result"] == 20.0

def test_memory_models():
    rec = MemoryRecord(
        id="u1:123:0",
        kind=MemoryKind.SEMANTIC,
        content="User menyukai Python",
        user_id="u1",
        created_at=datetime.utcnow()
    )
    assert rec.kind == MemoryKind.SEMANTIC
    assert rec.user_id == "u1"

def test_task_plan_structure():
    plan = TaskPlan(
        goal="Hitung 10+20 dan cari info Ruka",
        steps=[
            PlanStep(step_id=1, description="Hitung 10+20", requires_tool="calculator"),
            PlanStep(step_id=2, description="Rangkum hasil")
        ]
    )
    assert len(plan.steps) == 2
    assert plan.steps[0].requires_tool == "calculator"

def test_vector_store_and_chunker():
    md = "# Ruka AI\nRuka adalah agent AI modular berbasis Aljabar Linier."
    chunks = chunk_markdown(md, source="test.md")
    assert len(chunks) > 0
    assert chunks[0].source == "test.md"

    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
        
    try:
        store = VectorStore(dim=4, path=db_path)
        vecs = [[1.0, 0.0, 0.0, 0.0]]
        store.add(chunks, vecs)
        
        results = store.search([1.0, 0.0, 0.0, 0.0], top_k=1, min_score=0.1)
        assert len(results) == 1
        assert results[0].chunk.source == "test.md"
        assert results[0].score >= 0.99
        store.conn.close()
    finally:
        if os.path.exists(db_path):
            os.remove(db_path)
