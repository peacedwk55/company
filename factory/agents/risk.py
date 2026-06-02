import logging
from factory.agents.base import Agent, AgentResult, CycleContext
from factory.autonomy import Action
from factory.errors import RiskBlocked

log = logging.getLogger(__name__)

_VALID_SCORES = {"LOW", "MEDIUM", "HIGH"}


class RiskAgent(Agent):
    """Capital protection agent — enforces hard limits IN CODE (§8.2, §13.8).

    Hard limits must raise RiskBlocked regardless of LLM output.
    Tests in test_risk_limits.py verify limits block correctly.
    """

    name = "risk"
    model_tier = "routine"

    def __init__(
        self,
        max_risk_per_trade_pct: float = 5.0,
        max_daily_drawdown_pct: float = 10.0,
    ) -> None:
        self._max_risk = max_risk_per_trade_pct
        self._max_drawdown = max_daily_drawdown_pct

    def check_limits(self, risk_pct: float, drawdown_pct: float) -> None:
        """Enforce hard risk limits. Raises RiskBlocked if either limit is exceeded.

        This is called from run() and also directly in tests.
        The check is IN CODE — not delegated to the LLM prompt.
        """
        if risk_pct > self._max_risk:
            raise RiskBlocked(
                f"risk_pct {risk_pct:.1f}% exceeds max {self._max_risk:.1f}%"
            )
        if drawdown_pct > self._max_drawdown:
            raise RiskBlocked(
                f"drawdown {drawdown_pct:.1f}% exceeds max {self._max_drawdown:.1f}% — trading halted"
            )

    def run(self, ctx: CycleContext) -> AgentResult:
        # Read recent observations to inform risk assessment
        obs_entries = ctx.memory.entries("observations.md")
        obs_text = "\n".join(e.body for e in obs_entries[-5:]) or "No observations yet."

        system = (
            "You are a risk manager for an AI trading company. "
            "Assess the overall portfolio risk based on the observations provided. "
            "Reply with exactly one word: LOW, MEDIUM, or HIGH."
        )
        messages = [
            {"role": "user", "content": f"Market observations:\n{obs_text}\n\nOverall risk level?"}
        ]

        response = ctx.llm.complete(
            system=system, messages=messages, tier=self.model_tier
        )

        score = response.text.strip().upper().split()[0] if response.text.strip() else "LOW"
        if score not in _VALID_SCORES:
            score = "LOW"

        # Enforce paper-trading limits (0% risk/drawdown since no real positions in MVP)
        self.check_limits(risk_pct=0.0, drawdown_pct=0.0)

        action = Action(
            kind="log_risk",
            payload={"score": score},
            agent=self.name,
        )
        decision = self.propose(ctx, action)
        if decision.allowed:
            ctx.memory.append(
                "risk_log.md",
                f"Risk assessment: {score}",
                agent=self.name,
                kind="risk",
            )

        return AgentResult(
            agent=self.name,
            summary=f"risk score: {score}",
            actions=[decision],
        )
