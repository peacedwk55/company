"""Real Claude API client with prompt caching (§7, §15).

ใช้แทน MockLLMClient เมื่อตั้งค่า ANTHROPIC_API_KEY
- System prompt ใช้ cache_control: ephemeral → Claude cache ไว้ 5 นาที
- ทุก agent ใน 1 cycle ได้ประโยชน์จาก cache (รันภายในไม่กี่วินาที)
- model tier ดึงจาก company.yaml budget.model_tier
"""
import os
import logging
from factory.llm.base import LLMClient, LLMResponse

log = logging.getLogger(__name__)

_DEFAULT_TIERS: dict[str, str] = {
    "routine":   "claude-haiku-4-5-20251001",
    "reasoning": "claude-sonnet-4-6",
    "critical":  "claude-opus-4-8",
}


class AnthropicLLMClient:
    """Production LLM client — wraps Anthropic SDK with prompt caching."""

    def __init__(
        self,
        api_key: str | None = None,
        model_tiers: dict[str, str] | None = None,
    ) -> None:
        try:
            import anthropic as _anthropic
            self._anthropic = _anthropic
        except ImportError:
            raise ImportError(
                "anthropic package not installed.\n"
                "Run: pip install anthropic"
            )

        key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        if not key:
            raise ValueError(
                "ANTHROPIC_API_KEY not set.\n"
                "Set it with: $env:ANTHROPIC_API_KEY = 'sk-ant-...'"
            )

        self._client = self._anthropic.Anthropic(api_key=key)
        self._tiers = {**_DEFAULT_TIERS, **(model_tiers or {})}

    def complete(
        self,
        *,
        system: str,
        messages: list[dict],
        tier: str,
        max_tokens: int = 1024,
    ) -> LLMResponse:
        model = self._tiers.get(tier, _DEFAULT_TIERS["reasoning"])

        # cache_control: ephemeral → Claude caches system prompt 5 นาที
        # ทุก agent ใน cycle เดียวกันได้ cache hit เพราะรันภายใน ~วินาที
        response = self._client.messages.create(
            model=model,
            max_tokens=max_tokens,
            system=[
                {
                    "type": "text",
                    "text": system,
                    "cache_control": {"type": "ephemeral"},
                }
            ],
            messages=messages,
        )

        text = response.content[0].text if response.content else ""
        usage = response.usage

        # Log cache hit/miss เพื่อ debug ค่าใช้จ่าย
        cached = getattr(usage, "cache_read_input_tokens", 0) or 0
        if cached:
            log.debug("[llm] %s | tier=%s | in=%d out=%d cached=%d (cache HIT)",
                      model, tier, usage.input_tokens, usage.output_tokens, cached)
        else:
            log.debug("[llm] %s | tier=%s | in=%d out=%d (cache MISS)",
                      model, tier, usage.input_tokens, usage.output_tokens)

        return LLMResponse(
            text=text,
            input_tokens=usage.input_tokens,
            output_tokens=usage.output_tokens,
        )
