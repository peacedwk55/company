import pytest
from pathlib import Path
from factory.memory import MemoryManager
from factory.autonomy import AutonomyGate
from factory.llm.mock import MockLLMClient
from factory.agents.base import CycleContext
from factory.agents.analyst import AnalystAgent
from factory.agents.risk import RiskAgent
from factory.agents.ceo import CEOAgent


@pytest.fixture
def ctx(tmp_path: Path) -> CycleContext:
    company_dir = tmp_path / "company"
    company_dir.mkdir()
    (company_dir / "memory").mkdir()
    memory = MemoryManager(company_dir, date="20260601")
    return CycleContext(
        company={"name": "test", "risk_level": "low", "execution_mode": "paper"},
        memory=memory,
        gate=AutonomyGate(),
        llm=MockLLMClient(),
        date="2026-06-01",
    )


# ------------------------------------------------------------------
# AnalystAgent
# ------------------------------------------------------------------

def test_analyst_returns_correct_agent_name(ctx: CycleContext) -> None:
    result = AnalystAgent().run(ctx)
    assert result.agent == "analyst"


def test_analyst_summary_mentions_observations(ctx: CycleContext) -> None:
    result = AnalystAgent().run(ctx)
    assert "observations" in result.summary


def test_analyst_writes_to_memory(ctx: CycleContext) -> None:
    AnalystAgent().run(ctx)
    entries = ctx.memory.entries("observations.md")
    assert len(entries) >= 1


def test_analyst_all_actions_low_risk(ctx: CycleContext) -> None:
    from factory.autonomy import Risk
    result = AnalystAgent().run(ctx)
    for dec in result.actions:
        assert dec.risk == Risk.LOW, f"Expected LOW but got {dec.risk}"


def test_analyst_with_scripted_llm(tmp_path: Path) -> None:
    company_dir = tmp_path / "co"
    company_dir.mkdir()
    (company_dir / "memory").mkdir()
    llm = MockLLMClient(scripted={"analyst": "BTC up 5%.\nETH volume rising."})
    ctx = CycleContext(
        company={"name": "co", "risk_level": "low", "execution_mode": "paper"},
        memory=MemoryManager(company_dir, date="20260601"),
        gate=AutonomyGate(),
        llm=llm,
        date="2026-06-01",
    )
    AnalystAgent().run(ctx)
    entries = ctx.memory.entries("observations.md")
    assert any("BTC" in e.body for e in entries)


# ------------------------------------------------------------------
# RiskAgent
# ------------------------------------------------------------------

def test_risk_agent_returns_correct_name(ctx: CycleContext) -> None:
    # Need at least one observation
    ctx.memory.append("observations.md", "Stable market", agent="analyst", kind="obs")
    result = RiskAgent().run(ctx)
    assert result.agent == "risk"


def test_risk_agent_summary_contains_score(ctx: CycleContext) -> None:
    result = RiskAgent().run(ctx)
    assert "risk score" in result.summary


def test_risk_agent_writes_to_risk_log(ctx: CycleContext) -> None:
    RiskAgent().run(ctx)
    entries = ctx.memory.entries("risk_log.md")
    assert len(entries) >= 1


def test_risk_agent_valid_score_values(ctx: CycleContext) -> None:
    result = RiskAgent().run(ctx)
    score = result.summary.split(": ")[1].strip()
    assert score in ("LOW", "MEDIUM", "HIGH")


# ------------------------------------------------------------------
# CEOAgent
# ------------------------------------------------------------------

def test_ceo_agent_returns_correct_name(ctx: CycleContext) -> None:
    result = CEOAgent().run(ctx)
    assert result.agent == "ceo"


def test_ceo_agent_summary_contains_stance(ctx: CycleContext) -> None:
    result = CEOAgent().run(ctx)
    assert "stance" in result.summary


def test_ceo_agent_writes_to_decisions(ctx: CycleContext) -> None:
    CEOAgent().run(ctx)
    entries = ctx.memory.entries("decisions.md")
    assert len(entries) >= 1


def test_ceo_valid_stance_values(ctx: CycleContext) -> None:
    result = CEOAgent().run(ctx)
    stance = result.summary.split(": ")[1].strip()
    assert stance in ("BULLISH", "BEARISH", "NEUTRAL")


# ------------------------------------------------------------------
# AutonomyGate integration
# ------------------------------------------------------------------

def test_gate_blocks_high_risk_action() -> None:
    from factory.autonomy import Action, AutonomyGate, Risk
    gate = AutonomyGate()                                          # balanced default
    action = Action(kind="execute_live_trade", payload={}, agent="test")
    decision = gate.evaluate(action)
    assert decision.risk == Risk.HIGH
    assert not decision.allowed


def test_gate_allows_low_risk_action() -> None:
    from factory.autonomy import Action, AutonomyGate, Risk
    gate = AutonomyGate()
    action = Action(kind="create_observation", payload={}, agent="test")
    decision = gate.evaluate(action)
    assert decision.risk == Risk.LOW
    assert decision.allowed


# ------------------------------------------------------------------
# work_style binds correctly to AutonomyGate
# ------------------------------------------------------------------

def test_conservative_blocks_low_risk() -> None:
    from factory.autonomy import Action, AutonomyGate, Risk
    gate   = AutonomyGate(work_style="conservative")
    action = Action(kind="create_observation", payload={}, agent="test")
    dec    = gate.evaluate(action)
    assert dec.risk == Risk.LOW
    assert not dec.allowed          # conservative: even LOW needs confirm


def test_balanced_allows_low_blocks_medium() -> None:
    from factory.autonomy import Action, AutonomyGate, Risk
    gate = AutonomyGate(work_style="balanced")
    low  = gate.evaluate(Action(kind="create_observation", payload={}, agent="test"))
    med  = gate.evaluate(Action(kind="create_task",        payload={}, agent="test"))
    assert low.allowed              # LOW auto
    assert not med.allowed          # MEDIUM confirm


def test_aggressive_allows_medium_blocks_high() -> None:
    from factory.autonomy import Action, AutonomyGate, Risk
    gate = AutonomyGate(work_style="aggressive")
    med  = gate.evaluate(Action(kind="create_task",        payload={}, agent="test"))
    high = gate.evaluate(Action(kind="execute_live_trade", payload={}, agent="test"))
    assert med.allowed              # MEDIUM auto
    assert not high.allowed         # HIGH always blocked


def test_high_risk_always_blocked_regardless_of_style() -> None:
    from factory.autonomy import Action, AutonomyGate
    for style in ("conservative", "balanced", "aggressive"):
        gate = AutonomyGate(work_style=style)
        dec  = gate.evaluate(Action(kind="execute_live_trade", payload={}, agent="test"))
        assert not dec.allowed, f"HIGH should be blocked for style={style}"


def test_gate_work_style_property() -> None:
    from factory.autonomy import AutonomyGate
    assert AutonomyGate(work_style="aggressive").work_style == "aggressive"


def test_invalid_work_style_defaults_to_balanced() -> None:
    from factory.autonomy import Action, AutonomyGate, Risk
    gate = AutonomyGate(work_style="turbo_ultra")   # invalid → balanced
    dec  = gate.evaluate(Action(kind="create_observation", payload={}, agent="test"))
    assert dec.allowed                              # balanced allows LOW
