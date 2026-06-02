"""Integration test: create → run → brief end-to-end (§3 MVP acceptance criteria)."""
import pytest
from pathlib import Path
from factory.create import create
from factory.run import run_cycle
from factory.llm.mock import MockLLMClient


@pytest.fixture
def company(tmp_path: Path):
    output_dir = tmp_path / "output"
    return create("trading", {"name": "myfund"}, output_dir=output_dir, register=False)


@pytest.fixture
def companies_dir(company) -> Path:
    return company.path.parent


# ------------------------------------------------------------------
# Full cycle correctness
# ------------------------------------------------------------------

def test_run_cycle_returns_correct_company_and_date(companies_dir) -> None:
    result = run_cycle("myfund", companies_dir=companies_dir,
                       llm=MockLLMClient(), date="2026-06-01")
    assert result.company == "myfund"
    assert result.date == "2026-06-01"


def test_run_cycle_produces_agent_results(companies_dir) -> None:
    result = run_cycle("myfund", companies_dir=companies_dir,
                       llm=MockLLMClient(), date="2026-06-01")
    assert len(result.agent_results) >= 2


def test_run_cycle_agents_match_workflow(companies_dir) -> None:
    result = run_cycle("myfund", companies_dir=companies_dir,
                       llm=MockLLMClient(), date="2026-06-01")
    agent_names = [r.agent for r in result.agent_results]
    assert "analyst" in agent_names
    assert "risk" in agent_names
    assert "ceo" in agent_names


# ------------------------------------------------------------------
# Brief file
# ------------------------------------------------------------------

def test_brief_file_created(companies_dir) -> None:
    result = run_cycle("myfund", companies_dir=companies_dir,
                       llm=MockLLMClient(), date="2026-06-01")
    assert result.brief_path.exists()


def test_brief_file_named_by_date(companies_dir) -> None:
    result = run_cycle("myfund", companies_dir=companies_dir,
                       llm=MockLLMClient(), date="2026-06-01")
    assert result.brief_path.name == "2026-06-01.md"


def test_brief_contains_company_name(companies_dir) -> None:
    result = run_cycle("myfund", companies_dir=companies_dir,
                       llm=MockLLMClient(), date="2026-06-01")
    assert "myfund" in result.brief_path.read_text()


def test_brief_contains_market_section(companies_dir) -> None:
    result = run_cycle("myfund", companies_dir=companies_dir,
                       llm=MockLLMClient(), date="2026-06-01")
    text = result.brief_path.read_text()
    assert "Market Observations" in text
    assert "Risk Status" in text


def test_brief_saved_in_briefings_dir(companies_dir) -> None:
    result = run_cycle("myfund", companies_dir=companies_dir,
                       llm=MockLLMClient(), date="2026-06-01")
    assert result.brief_path.parent.name == "briefings"


# ------------------------------------------------------------------
# Memory state after cycle
# ------------------------------------------------------------------

def test_observations_written_to_memory(company, companies_dir) -> None:
    from factory.memory import MemoryManager
    run_cycle("myfund", companies_dir=companies_dir,
              llm=MockLLMClient(), date="2026-06-01")
    mm = MemoryManager(company.path, date="20260601")
    assert len(mm.entries("observations.md")) >= 1


def test_risk_log_written(company, companies_dir) -> None:
    from factory.memory import MemoryManager
    run_cycle("myfund", companies_dir=companies_dir,
              llm=MockLLMClient(), date="2026-06-01")
    mm = MemoryManager(company.path, date="20260601")
    assert len(mm.entries("risk_log.md")) >= 1


def test_decisions_written(company, companies_dir) -> None:
    from factory.memory import MemoryManager
    run_cycle("myfund", companies_dir=companies_dir,
              llm=MockLLMClient(), date="2026-06-01")
    mm = MemoryManager(company.path, date="20260601")
    assert len(mm.entries("decisions.md")) >= 1


def test_second_cycle_appends_not_overwrites(company, companies_dir) -> None:
    from factory.memory import MemoryManager
    llm = MockLLMClient()
    run_cycle("myfund", companies_dir=companies_dir, llm=llm, date="2026-06-01")
    run_cycle("myfund", companies_dir=companies_dir, llm=llm, date="2026-06-02")
    mm = MemoryManager(company.path)
    assert len(mm.entries("observations.md")) >= 2


def test_missing_company_raises(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        run_cycle("myfund", companies_dir=tmp_path / "empty")
