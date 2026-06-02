from factory.memory import MemoryManager


def generate_brief(
    *,
    company: dict,
    cycle_result,          # CycleResult | None — used for agent summaries
    memory: MemoryManager,
    date: str,
) -> str:
    """Generate a daily markdown brief from memory contents.

    Reads from memory files (observations, decisions, risk_log, task_queue).
    Written to companies/{name}/memory/briefings/{date}.md by run_cycle().
    """
    observations = memory.entries("observations.md")
    decisions = memory.entries("decisions.md")
    risk_entries = memory.entries("risk_log.md")
    open_tasks = memory.open_tasks()

    company_name = company.get("name", "Unknown")
    exec_mode = company.get("execution_mode", "paper")
    risk_level = company.get("risk_level", "low")

    # Latest entries only (avoid overlong brief)
    recent_obs = observations[-5:]
    recent_dec = decisions[-3:]
    latest_risk = risk_entries[-1].body if risk_entries else f"default ({risk_level})"

    lines: list[str] = [
        f"# Daily Brief — {company_name} — {date}",
        "",
        f"**Execution mode:** {exec_mode} | **Risk level:** {risk_level}",
        "",
    ]

    # -- Agent cycle summaries --
    if cycle_result and hasattr(cycle_result, "agent_results"):
        lines.append("## Cycle Summary")
        for r in cycle_result.agent_results:
            lines.append(f"- **[{r.agent}]** {r.summary}")
        lines.append("")

    # -- Market Observations --
    lines.append("## Market Observations")
    if recent_obs:
        for e in recent_obs:
            lines.append(f"- {e.body}")
    else:
        lines.append("- No observations recorded today.")
    lines.append("")

    # -- Strategic Decisions --
    lines.append("## Decisions")
    if recent_dec:
        for e in recent_dec:
            lines.append(f"- {e.body}")
    else:
        lines.append("- No decisions recorded.")
    lines.append("")

    # -- Risk Status --
    lines.append("## Risk Status")
    lines.append(f"- {latest_risk}")
    lines.append("")

    # -- Open Tasks --
    lines.append("## Open Tasks")
    if open_tasks:
        for t in open_tasks[:5]:
            title_line = next(
                (l.split(": ", 1)[1] for l in t.body.splitlines() if l.startswith("Title:")),
                t.body[:60],
            )
            lines.append(f"- {title_line}")
    else:
        lines.append("- No open tasks.")
    lines.append("")

    lines.append(f"*Generated: {date} | Mode: {exec_mode}*")

    return "\n".join(lines) + "\n"
