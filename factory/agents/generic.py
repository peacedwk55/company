"""GenericAgent — works for any AI-generated company role.

Used for companies created via create_from_description().
Agent's behaviour is derived from its spec (role + responsibilities) in agents.yaml.
No hardcoded logic — Claude drives everything from the role description.
"""
import logging
from factory.agents.base import Agent, AgentResult, CycleContext
from factory.autonomy import Action

log = logging.getLogger(__name__)


class GenericAgent(Agent):
    """Dynamic agent that fulfills any role based on its spec from agents.yaml.

    Instead of hardcoded logic (like AnalystAgent/RiskAgent),
    this agent builds its system prompt from:
      - role: Job title
      - responsibilities: Daily task list
      - model_tier: Which Claude model to use
    """

    def __init__(self, spec: dict) -> None:
        self.name       = spec["id"]
        self.model_tier = spec.get("model_tier", "reasoning")
        self._role      = spec["role"]
        self._resps     = spec.get("responsibilities", [])

    def run(self, ctx: CycleContext) -> AgentResult:
        resp_list = "\n".join(f"- {r}" for r in self._resps)

        system = (
            f"You are {self._role}.\n\n"
            f"Your daily responsibilities:\n{resp_list}\n\n"
            f"Complete your daily tasks. Be specific, concise, and actionable.\n"
            f"Output 2-4 concrete findings, observations, or decisions.\n"
            f"Write in a professional style appropriate for your role."
        )

        messages = [
            {
                "role": "user",
                "content": (
                    f"Date: {ctx.date}\n"
                    f"Company: {ctx.company.get('description', ctx.company.get('name', ''))}\n\n"
                    f"What are your key outputs for today? "
                    f"Focus on what matters most for your role."
                ),
            }
        ]

        response = ctx.llm.complete(
            system=system,
            messages=messages,
            tier=self.model_tier,
        )
        output_text = response.text.strip()

        # Choose memory file by tier: critical → decisions, others → observations
        mem_file = "decisions.md" if self.model_tier == "critical" else "observations.md"
        mem_kind = "dec" if self.model_tier == "critical" else "obs"

        action = Action(kind="update_memory", payload={"body": output_text}, agent=self.name)
        decision = self.propose(ctx, action)
        if decision.allowed:
            ctx.memory.append(mem_file, output_text, agent=self.name, kind=mem_kind)

        # First non-empty line as summary (truncated)
        summary_lines = [l.strip() for l in output_text.split("\n") if l.strip()]
        summary = summary_lines[0][:60] if summary_lines else "completed tasks"

        return AgentResult(agent=self.name, summary=summary, actions=[decision])
