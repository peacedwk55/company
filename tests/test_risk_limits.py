"""⚠️ CRITICAL — Risk limits must block in code, not just in prompts (§8.2, §9, §16).

These tests prove that RiskAgent.check_limits() raises RiskBlocked
when limits are exceeded. Passing these tests = trading guardrails work.
"""
import pytest
from factory.agents.risk import RiskAgent
from factory.errors import RiskBlocked


@pytest.fixture
def agent() -> RiskAgent:
    return RiskAgent(max_risk_per_trade_pct=5.0, max_daily_drawdown_pct=10.0)


# ------------------------------------------------------------------
# risk_pct limits
# ------------------------------------------------------------------

def test_risk_at_limit_is_allowed(agent: RiskAgent) -> None:
    agent.check_limits(risk_pct=5.0, drawdown_pct=0.0)  # must not raise


def test_risk_below_limit_is_allowed(agent: RiskAgent) -> None:
    agent.check_limits(risk_pct=2.0, drawdown_pct=0.0)  # must not raise


def test_risk_exceeds_limit_raises(agent: RiskAgent) -> None:
    with pytest.raises(RiskBlocked, match="risk_pct"):
        agent.check_limits(risk_pct=5.1, drawdown_pct=0.0)


def test_risk_far_exceeds_limit_raises(agent: RiskAgent) -> None:
    with pytest.raises(RiskBlocked):
        agent.check_limits(risk_pct=50.0, drawdown_pct=0.0)


# ------------------------------------------------------------------
# drawdown limits
# ------------------------------------------------------------------

def test_drawdown_at_limit_is_allowed(agent: RiskAgent) -> None:
    agent.check_limits(risk_pct=0.0, drawdown_pct=10.0)  # must not raise


def test_drawdown_below_limit_is_allowed(agent: RiskAgent) -> None:
    agent.check_limits(risk_pct=0.0, drawdown_pct=5.0)  # must not raise


def test_drawdown_11_pct_halts_trading(agent: RiskAgent) -> None:
    """The spec (§8.2) requires: drawdown > 10% → stop trading immediately."""
    with pytest.raises(RiskBlocked, match="drawdown"):
        agent.check_limits(risk_pct=0.0, drawdown_pct=11.0)


def test_drawdown_100_pct_raises(agent: RiskAgent) -> None:
    with pytest.raises(RiskBlocked):
        agent.check_limits(risk_pct=0.0, drawdown_pct=100.0)


# ------------------------------------------------------------------
# Both limits simultaneously
# ------------------------------------------------------------------

def test_both_within_limits_allowed(agent: RiskAgent) -> None:
    agent.check_limits(risk_pct=3.0, drawdown_pct=7.0)  # must not raise


def test_risk_exceeded_even_if_drawdown_ok_raises(agent: RiskAgent) -> None:
    with pytest.raises(RiskBlocked, match="risk_pct"):
        agent.check_limits(risk_pct=6.0, drawdown_pct=5.0)


def test_drawdown_exceeded_even_if_risk_ok_raises(agent: RiskAgent) -> None:
    with pytest.raises(RiskBlocked, match="drawdown"):
        agent.check_limits(risk_pct=2.0, drawdown_pct=10.1)


# ------------------------------------------------------------------
# Custom limits
# ------------------------------------------------------------------

def test_custom_conservative_limits() -> None:
    conservative = RiskAgent(max_risk_per_trade_pct=1.0, max_daily_drawdown_pct=3.0)
    with pytest.raises(RiskBlocked):
        conservative.check_limits(risk_pct=1.5, drawdown_pct=0.0)


def test_custom_limits_allow_within_range() -> None:
    permissive = RiskAgent(max_risk_per_trade_pct=10.0, max_daily_drawdown_pct=20.0)
    permissive.check_limits(risk_pct=9.9, drawdown_pct=19.9)  # must not raise
