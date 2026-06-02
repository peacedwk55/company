from factory.llm.base import LLMClient, LLMResponse

_DEFAULTS: dict[str, str] = {
    "analyst": (
        "Market momentum is stable with volume above 30-day average.\n"
        "Sentiment remains cautious amid macro uncertainty and rate expectations."
    ),
    "risk": "LOW",
    "ceo": "NEUTRAL",
}


class MockLLMClient:
    """Offline, deterministic LLM for development and testing (§15).

    Contract:
    - No network calls — works fully offline.
    - Deterministic: same inputs → same output (suitable for snapshot tests).
    - Scriptable: inject {key: response} to override by keyword match in system prompt.
    - Token counts are approximations for budget-guard testing.
    - Never raises unless simulate_error=True.
    """

    def __init__(
        self,
        scripted: dict[str, str] | None = None,
        simulate_error: bool = False,
    ) -> None:
        self._scripted = scripted or {}
        self._simulate_error = simulate_error

    def complete(
        self,
        *,
        system: str,
        messages: list[dict],
        tier: str,
        max_tokens: int = 1024,
    ) -> LLMResponse:
        if self._simulate_error:
            raise RuntimeError("MockLLMClient: simulated error")

        # 1. Check user-supplied scripted overrides first
        combined = system.lower() + " ".join(
            m.get("content", "").lower() for m in messages
        )
        for key, response in self._scripted.items():
            if key.lower() in combined:
                return self._make_response(system, messages, response)

        # 2. Fall back to keyword-matched defaults
        for key, response in _DEFAULTS.items():
            if key in system.lower():
                return self._make_response(system, messages, response)

        return self._make_response(system, messages, f"[mock:{tier}] ok")

    @staticmethod
    def _make_response(system: str, messages: list[dict], text: str) -> LLMResponse:
        all_input = system + " ".join(m.get("content", "") for m in messages)
        input_tokens = max(1, len(all_input) // 4)
        output_tokens = max(1, len(text) // 4)
        return LLMResponse(text=text, input_tokens=input_tokens, output_tokens=output_tokens)
