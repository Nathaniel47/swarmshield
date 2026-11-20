import pytest

from swarmshield.llm.budget import DailyBudgetExhausted, TokenBudget


def test_daily_limit_stops_the_run(tmp_path):
    limits = {"rpm": 100, "rpd": 100, "tpm": 10_000, "tpd": 100}
    budget = TokenBudget(tmp_path, "m", limits)
    budget.before_call(50)
    budget.record(50)
    with pytest.raises(DailyBudgetExhausted):
        budget.before_call(50)
