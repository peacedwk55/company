import abc
import logging
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from factory.memory import MemoryManager
    from factory.autonomy import AutonomyGate, Action, GateDecision
    from factory.llm.base import LLMClient

log = logging.getLogger(__name__)


@dataclass
class CycleContext:
    """Everything an agent needs for one execution cycle (§13.8).

    date: YYYY-MM-DD string — injected from run_cycle() (never call datetime.now() here)
    """
    company: dict
    memory: "MemoryManager"
    gate: "AutonomyGate"
    llm: "LLMClient"
    date: str


@dataclass
class AgentResult:
    agent: str
    summary: str
    actions: list["GateDecision"] = field(default_factory=list)


class Agent(abc.ABC):
    name: str = ""
    model_tier: str = "routine"

    @abc.abstractmethod
    def run(self, ctx: CycleContext) -> AgentResult: ...

    def propose(self, ctx: CycleContext, action: "Action") -> "GateDecision":
        """Route every action through the Autonomy Gate (no bypassing)."""
        decision = ctx.gate.evaluate(action)
        log.debug("[%s] proposed '%s' → %s", self.name, action.kind, decision.risk.value)
        return decision
