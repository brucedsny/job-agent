"""Thin wrapper over the Anthropic SDK for structured calls.

`messages.parse` + adaptive thinking, per-call cost tracking, a per-run spend
cap, model fallback on transient errors, and an injectable client for tests.
"""

from __future__ import annotations

from typing import Any, TypeVar

from pydantic import BaseModel

from .config import PRICES, Settings, get_settings
from .obs import get_logger

T = TypeVar("T", bound=BaseModel)
_log = get_logger()


class LLMError(RuntimeError):
    """No usable structured response."""


class SpendCapExceeded(RuntimeError):
    """Per-run LLM spend cap reached."""


class LLMResult:
    def __init__(self, value: Any, model: str, cost_usd: float) -> None:
        self.value = value
        self.model = model
        self.cost_usd = cost_usd


def _cost(model: str, usage: Any) -> float:
    price = PRICES.get(model)
    if price is None or usage is None:
        return 0.0
    inp = getattr(usage, "input_tokens", 0) or 0
    out = getattr(usage, "output_tokens", 0) or 0
    cache_read = getattr(usage, "cache_read_input_tokens", 0) or 0
    cache_write = getattr(usage, "cache_creation_input_tokens", 0) or 0
    return (
        inp / 1e6 * price["input"]
        + out / 1e6 * price["output"]
        + cache_read / 1e6 * price["input"] * 0.1
        + cache_write / 1e6 * price["input"] * 1.25
    )


class LLMClient:
    def __init__(self, settings: Settings | None = None, client: Any = None) -> None:
        self.settings = settings or get_settings()
        self._client = client
        self.spent_usd = 0.0
        self.calls = 0

    def _get_client(self) -> Any:
        if self._client is not None:
            return self._client
        if not self.settings.anthropic_api_key:
            raise LLMError("ANTHROPIC_API_KEY is not set (configure it in .env).")
        import anthropic  # lazy: package imports without the SDK

        self._client = anthropic.Anthropic(api_key=self.settings.anthropic_api_key)
        return self._client

    def _fallback_chain(self, model: str) -> list[str]:
        nxt = self.settings.llm_fallbacks.get(model)
        return [nxt] if nxt else []

    def structured(
        self,
        model: str,
        schema: type[T],
        system: str,
        user: str,
        *,
        max_tokens: int | None = None,
        thinking: bool = True,
        fallbacks: list[str] | None = None,
    ) -> LLMResult:
        if self.spent_usd >= self.settings.spend_cap_usd:
            raise SpendCapExceeded(
                f"Spend cap reached (${self.spent_usd:.2f} >= ${self.settings.spend_cap_usd:.2f})."
            )
        self._get_client()  # surface credential errors clearly, no fallback

        models = [model] + (fallbacks if fallbacks is not None else self._fallback_chain(model))
        last_err: Exception | None = None
        for m in models:
            try:
                return self._call_once(m, schema, system, user, max_tokens, thinking)
            except SpendCapExceeded:
                raise
            except Exception as exc:  # noqa: BLE001 — resilience fallback
                last_err = exc
                _log.warning("LLM failed on %s (%s); trying fallback", m, exc)
        raise LLMError(f"All LLM attempts failed: {last_err}") from last_err

    def _call_once(self, model, schema, system, user, max_tokens, thinking) -> LLMResult:
        kwargs: dict[str, Any] = {
            "model": model,
            "max_tokens": max_tokens or self.settings.max_tokens_default,
            "system": system,
            "messages": [{"role": "user", "content": user}],
            "output_format": schema,
        }
        if thinking:
            kwargs["thinking"] = {"type": "adaptive"}
        resp = self._get_client().messages.parse(**kwargs)
        parsed = getattr(resp, "parsed_output", None)
        if parsed is None:
            raise LLMError(f"No structured output (stop_reason={getattr(resp, 'stop_reason', None)}).")
        cost = _cost(model, getattr(resp, "usage", None))
        self.spent_usd += cost
        self.calls += 1
        _log.info("LLM %s ok: $%.4f (total $%.4f)", model, cost, self.spent_usd)
        return LLMResult(parsed, model, cost)
