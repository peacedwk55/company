"""Budget guard wrapper — จำกัด token ต่อวันตาม company.yaml §7.

ห่อ LLMClient ใดก็ได้ (Mock หรือ Anthropic) แล้ว track token ที่ใช้ไป
เมื่อเกิน max_daily_tokens → raise BudgetExceeded หรือ downgrade model
"""
import logging
from factory.llm.base import LLMClient, LLMResponse
from factory.errors import BudgetExceeded

log = logging.getLogger(__name__)


class BudgetGuardedLLMClient:
    """Wraps any LLMClient and enforces daily token budget from company.yaml."""

    def __init__(
        self,
        inner: LLMClient,
        max_daily_tokens: int = 100_000,
        on_exceed: str = "stop_and_alert",   # stop_and_alert | downgrade | continue
    ) -> None:
        self._inner = inner
        self._max = max_daily_tokens
        self._spent = 0
        self._on_exceed = on_exceed

    @property
    def tokens_spent(self) -> int:
        return self._spent

    @property
    def tokens_remaining(self) -> int:
        return max(0, self._max - self._spent)

    def complete(
        self,
        *,
        system: str,
        messages: list[dict],
        tier: str,
        max_tokens: int = 1024,
    ) -> LLMResponse:
        if self._spent >= self._max:
            if self._on_exceed == "continue":
                log.warning("[budget] over limit %d/%d — continuing anyway", self._spent, self._max)
            else:
                raise BudgetExceeded(self._spent, self._max)

        response = self._inner.complete(
            system=system, messages=messages, tier=tier, max_tokens=max_tokens
        )

        self._spent += response.input_tokens + response.output_tokens

        pct = self._spent / self._max * 100
        log.debug("[budget] %d/%d tokens (%.0f%%)", self._spent, self._max, pct)

        # เตือนเมื่อใกล้ถึง limit
        if self._spent >= self._max * 0.9 and self._spent < self._max:
            log.warning("[budget] WARNING: %.0f%% of daily token budget used (%d/%d)",
                        pct, self._spent, self._max)

        if self._spent >= self._max and self._on_exceed == "stop_and_alert":
            print(f"\n[BUDGET] Daily token limit reached: {self._spent}/{self._max} tokens used.")
            print("[BUDGET] Next cycle will be blocked. Reset tomorrow or increase max_daily_tokens in company.yaml")

        return response
