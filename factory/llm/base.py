import typing
from dataclasses import dataclass


@dataclass
class LLMResponse:
    text: str
    input_tokens: int
    output_tokens: int


class LLMClient(typing.Protocol):
    """Structural interface every LLM backend must satisfy.

    tier ∈ {routine, reasoning, critical} — mapped to model names in company.yaml §14.6
    Add factory/llm/anthropic.py later to wire the real API without touching this interface.
    """

    def complete(
        self,
        *,
        system: str,
        messages: list[dict],
        tier: str,
        max_tokens: int = 1024,
    ) -> LLMResponse: ...
