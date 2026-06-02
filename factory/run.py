import argparse
import logging
import os
from dataclasses import dataclass, field
from pathlib import Path
from datetime import datetime, timezone

import yaml

from factory.memory import MemoryManager
from factory.autonomy import AutonomyGate
from factory.brief import generate_brief
from factory.agents.base import CycleContext, AgentResult

log = logging.getLogger(__name__)

_AGENT_REGISTRY: dict = {}  # populated lazily to avoid circular imports


def _make_llm_client(company: dict):
    """Auto-detect LLM backend.

    - ANTHROPIC_API_KEY set → AnthropicLLMClient (real AI) + BudgetGuard
    - ไม่มี key          → MockLLMClient (offline, deterministic)
    """
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        log.info("[llm] ANTHROPIC_API_KEY not set — using MockLLMClient")
        from factory.llm.mock import MockLLMClient
        return MockLLMClient()

    from factory.llm.anthropic_client import AnthropicLLMClient
    from factory.llm.budget_guard import BudgetGuardedLLMClient

    budget_cfg = company.get("budget", {})
    model_tiers = budget_cfg.get("model_tier") or {}
    max_tokens = budget_cfg.get("max_daily_tokens", 100_000)
    on_exceed = budget_cfg.get("on_exceed", "stop_and_alert")

    client = AnthropicLLMClient(api_key=api_key, model_tiers=model_tiers)
    log.info("[llm] Using AnthropicLLMClient (budget: %d tokens/day)", max_tokens)
    return BudgetGuardedLLMClient(client, max_daily_tokens=max_tokens, on_exceed=on_exceed)


def _get_registry() -> dict:
    if not _AGENT_REGISTRY:
        from factory.agents.analyst import AnalystAgent
        from factory.agents.risk import RiskAgent
        from factory.agents.ceo import CEOAgent
        _AGENT_REGISTRY.update({
            "analyst": AnalystAgent,
            "risk": RiskAgent,
            "ceo": CEOAgent,
        })
    return _AGENT_REGISTRY


@dataclass
class CycleResult:
    company: str
    date: str
    agent_results: list[AgentResult] = field(default_factory=list)
    brief_path: Path = field(default_factory=lambda: Path("."))


def run_cycle(
    company_name: str,
    *,
    companies_dir: Path | None = None,
    llm=None,
    date: str | None = None,
    on_progress=None,
) -> CycleResult:
    """Execute one daily cycle for a company instance (§13.4).

    companies_dir=None → lookup path from registry
    llm=None           → auto-detect (real API if key set, else Mock)
    date=None          → today (inject for deterministic tests)
    """
    if date is None:
        date = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    # Resolve company directory
    if companies_dir is not None:
        company_dir = Path(companies_dir) / company_name
    else:
        from factory.registry import registry
        record = registry.get(company_name)
        if record is None:
            raise FileNotFoundError(
                f"Company '{company_name}' not found in registry. "
                "Run `python -m factory list` to see available companies."
            )
        company_dir = Path(record.path)

    if not company_dir.exists():
        raise FileNotFoundError(
            f"Company folder missing: {company_dir}\n"
            "The project may have been moved or deleted."
        )

    # Load config files
    company = _load_yaml(company_dir / "company.yaml")

    if llm is None:
        llm = _make_llm_client(company)
    workflow = _load_yaml(company_dir / "workflow.yaml")
    agents_meta = _load_yaml(company_dir / "agents.yaml")

    # Setup shared objects
    date_compact = date.replace("-", "")
    memory     = MemoryManager(company_dir, date=date_compact)
    work_style = company.get("work_style", "balanced")
    gate       = AutonomyGate(work_style=work_style)
    log.debug("AutonomyGate: work_style=%s", work_style)
    ctx = CycleContext(company=company, memory=memory, gate=gate, llm=llm, date=date)

    # Instantiate agents from agents.yaml roster
    registry = _get_registry()
    agents: dict[str, object] = {}
    for spec in agents_meta.get("agents", []):
        agent_id: str = spec["id"]
        cls = registry.get(agent_id)
        if cls is None:
            # Fallback: GenericAgent for any AI-generated company role
            from factory.agents.generic import GenericAgent
            agents[agent_id] = GenericAgent(spec)
            log.debug("Using GenericAgent for '%s'", agent_id)
            continue
        limits = spec.get("hard_limits", {})
        if agent_id == "risk" and limits:
            agents[agent_id] = cls(
                max_risk_per_trade_pct=limits.get("max_risk_per_trade_pct", 5),
                max_daily_drawdown_pct=limits.get("max_daily_drawdown_pct", 10),
            )
        else:
            agents[agent_id] = cls()

    # Execute workflow steps
    result = CycleResult(company=company_name, date=date)
    for step in workflow.get("steps", []):
        agent_id = step.get("agent")
        if agent_id is None:
            continue  # brief step — handled after the loop
        agent = agents.get(agent_id)
        if agent is None:
            log.warning("Agent '%s' not instantiated — skipped", agent_id)
            continue
        agent_result: AgentResult = agent.run(ctx)
        result.agent_results.append(agent_result)
        print(f"  [{agent_result.agent:<8}] {agent_result.summary}")
        if on_progress:
            on_progress({"type": "agent", "agent": agent_result.agent, "summary": agent_result.summary})

    # Generate and save daily brief
    brief_md = generate_brief(
        company=company, cycle_result=result, memory=memory, date=date
    )
    brief_dir = company_dir / "memory" / "briefings"
    brief_dir.mkdir(parents=True, exist_ok=True)
    brief_path = brief_dir / f"{date}.md"
    brief_path.write_text(brief_md, encoding="utf-8")
    result.brief_path = brief_path
    print(f"  [brief   ] saved -> {brief_path}")

    return result


def _load_yaml(path: Path) -> dict:
    if not path.exists():
        raise FileNotFoundError(f"Required file not found: {path}")
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    return data if isinstance(data, dict) else {}


# ------------------------------------------------------------------
# CLI entrypoint
# ------------------------------------------------------------------

def main(argv: list[str] | None = None) -> int:
    from factory.config import setup_logging
    setup_logging()

    parser = argparse.ArgumentParser(description="Run one daily cycle for an AI company")
    parser.add_argument("--company", required=True, help="Company name (must exist in companies/)")
    parser.add_argument("--dry-run", action="store_true", help="Parse only; no writes")
    args = parser.parse_args(argv)

    try:
        result = run_cycle(args.company)
        print(f"\n[OK] Cycle complete for '{result.company}' on {result.date}")
        return 0
    except FileNotFoundError as e:
        print(f"[ERROR] {e}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
