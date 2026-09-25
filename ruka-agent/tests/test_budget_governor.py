import pytest
from src.agent.budget import (Budget, BudgetExceeded,
                              BudgetGovernor)

def test_iteration_budget_stops_with_report():
    gov = BudgetGovernor(Budget(max_iterations=3, max_seconds=10))
    with pytest.raises(BudgetExceeded, match="iterations") as ei:
        for i in range(5):
            gov.check_iteration(progress_note=f"langkah {i}")
    assert "langkah" in ei.value.report          # laporan bawa konteks

def test_token_budget_exceeded():
    gov = BudgetGovernor(Budget(max_tokens=100, max_seconds=10))
    with pytest.raises(BudgetExceeded, match="tokens"):
        gov.add_tokens(60)
        gov.add_tokens(60)                       # 120 > 100

def test_pressure_ratio_and_threshold():
    gov = BudgetGovernor(Budget(max_iterations=10, max_seconds=60))
    for _ in range(7):
        gov.check_iteration()
    assert gov.pressure()["iterations"] == pytest.approx(0.7)
    assert gov.is_pressured(0.75) is False
    gov.check_iteration()
    assert gov.is_pressured(0.75) is True        # 0.8 >= 0.75

def test_task_spread_guard():
    gov = BudgetGovernor(Budget(max_tasks=2, max_seconds=10))
    gov.add_task()
    with pytest.raises(BudgetExceeded, match="melebar"):
        gov.add_task()
