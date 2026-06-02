import enum
import logging
from dataclasses import dataclass

log = logging.getLogger(__name__)


class Risk(enum.Enum):
    LOW    = "low"
    MEDIUM = "medium"
    HIGH   = "high"


# Action kind → Risk level (§8.1)
_RISK_TABLE: dict[str, Risk] = {
    # LOW — safe, informational
    "update_memory":      Risk.LOW,
    "create_observation": Risk.LOW,
    "summarize":          Risk.LOW,
    "log_risk":           Risk.LOW,
    # MEDIUM — changes state / proposes action
    "create_task":        Risk.MEDIUM,
    "modify_plan":        Risk.MEDIUM,
    "propose_trade":      Risk.MEDIUM,
    "update_strategy":    Risk.MEDIUM,
    # HIGH — external effect / irreversible
    "execute_live_trade": Risk.HIGH,
    "send_email":         Risk.HIGH,
    "spend_money":        Risk.HIGH,
    "delete_data":        Risk.HIGH,
    "execute_contract":   Risk.HIGH,
}

# work_style → which risk levels are auto-allowed
# HIGH is NEVER auto-allowed regardless of style
_THRESHOLDS: dict[str, set[Risk]] = {
    "conservative": set(),                          # ทุกอย่างต้อง confirm
    "balanced":     {Risk.LOW},                     # LOW auto, MEDIUM+ confirm
    "aggressive":   {Risk.LOW, Risk.MEDIUM},        # LOW+MEDIUM auto, HIGH block
}

_VALID_STYLES = set(_THRESHOLDS.keys())


@dataclass
class Action:
    kind:    str
    payload: dict
    agent:   str


@dataclass
class GateDecision:
    risk:    Risk
    allowed: bool
    reason:  str


def classify(action: Action) -> Risk:
    """Unknown action kinds default to MEDIUM (safe-side)."""
    return _RISK_TABLE.get(action.kind, Risk.MEDIUM)


class AutonomyGate:
    """Every agent action must pass through this gate before execution (§8).

    work_style controls which risk levels are auto-allowed:
      conservative → nothing auto (always confirm)
      balanced     → LOW auto, MEDIUM+ confirm   (default)
      aggressive   → LOW+MEDIUM auto, HIGH block

    HIGH is never auto-allowed regardless of work_style.
    """

    def __init__(self, work_style: str = "balanced") -> None:
        if work_style not in _VALID_STYLES:
            log.warning("Unknown work_style '%s' — defaulting to 'balanced'", work_style)
            work_style = "balanced"
        self._style    = work_style
        self._allowed  = _THRESHOLDS[work_style]

    @property
    def work_style(self) -> str:
        return self._style

    def evaluate(self, action: Action) -> GateDecision:
        risk    = classify(action)
        allowed = risk in self._allowed  # HIGH is never in any threshold set

        if allowed:
            reason = f"AUTO ({self._style}): '{action.kind}' [{risk.value}]"
        elif risk == Risk.HIGH:
            reason = f"BLOCKED: '{action.kind}' requires explicit human approval"
        else:
            reason = f"CONFIRM ({self._style}): '{action.kind}' [{risk.value}] queued for approval"

        log.debug(
            "[gate:%s] agent=%s kind=%s risk=%s allowed=%s",
            self._style, action.agent, action.kind, risk.value, allowed,
        )
        return GateDecision(risk=risk, allowed=allowed, reason=reason)
