import logging
from factory.agents.base import Agent, AgentResult, CycleContext
from factory.autonomy import Action

log = logging.getLogger(__name__)

_VALID_STANCES = {"BULLISH", "BEARISH", "NEUTRAL"}


class CEOAgent(Agent):
    """Strategic decision maker — sets daily market stance."""

    name = "ceo"
    model_tier = "critical"

    def run(self, ctx: CycleContext) -> AgentResult:
        # Read latest risk assessment to inform stance
        risk_entries = ctx.memory.entries("risk_log.md")
        risk_summary = risk_entries[-1].body if risk_entries else "No risk data."

        system = (
            "You are the CEO of an AI trading company. "
            "Based on the risk assessment, set the market stance. "
            "Reply with exactly one word: BULLISH, BEARISH, or NEUTRAL."
        )
        messages = [
            {
                "role": "user",
                "content": (
                    f"Date: {ctx.date}. "
                    f"Risk assessment: {risk_summary}. "
                    "What is today's market stance?"
                ),
            }
        ]

        response = ctx.llm.complete(
            system=system, messages=messages, tier=self.model_tier
        )

        stance = response.text.strip().upper().split()[0] if response.text.strip() else "NEUTRAL"
        if stance not in _VALID_STANCES:
            stance = "NEUTRAL"

        action = Action(
            kind="update_memory",
            payload={"stance": stance},
            agent=self.name,
        )
        decision = self.propose(ctx, action)
        if decision.allowed:
            ctx.memory.append(
                "decisions.md",
                f"Market stance: {stance}",
                agent=self.name,
                kind="dec",
            )

        return AgentResult(
            agent=self.name,
            summary=f"stance: {stance}",
            actions=[decision],
        )
