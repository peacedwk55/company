import logging
from factory.agents.base import Agent, AgentResult, CycleContext
from factory.autonomy import Action

log = logging.getLogger(__name__)


class AnalystAgent(Agent):
    """Market intelligence agent — generates observations per cycle."""

    name = "analyst"
    model_tier = "reasoning"

    def run(self, ctx: CycleContext) -> AgentResult:
        system = (
            "You are a disciplined market analyst for an AI trading company. "
            "Generate exactly 2 concise market observations (one per line). "
            "Each observation should be specific and factual."
        )
        messages = [
            {
                "role": "user",
                "content": (
                    f"Date: {ctx.date}. "
                    f"Company risk level: {ctx.company.get('risk_level', 'low')}. "
                    "Analyze current market conditions and provide 2 observations."
                ),
            }
        ]

        response = ctx.llm.complete(
            system=system, messages=messages, tier=self.model_tier
        )

        # Parse observations — split on newlines, take non-empty lines
        lines = [l.strip() for l in response.text.split("\n") if l.strip()]
        observations = lines[:2] if len(lines) >= 2 else (lines if lines else ["No data available."])

        decisions = []
        for obs in observations:
            action = Action(
                kind="create_observation",
                payload={"body": obs},
                agent=self.name,
            )
            decision = self.propose(ctx, action)
            if decision.allowed:
                ctx.memory.append("observations.md", obs, agent=self.name, kind="obs")
            decisions.append(decision)

        return AgentResult(
            agent=self.name,
            summary=f"generated {len(observations)} observations",
            actions=decisions,
        )
