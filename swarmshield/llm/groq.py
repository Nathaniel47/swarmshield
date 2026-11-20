"""Groq backend. The SDK is imported lazily so tests and CI do not need it."""

import time

from swarmshield.config import RATE_LIMITS, Config, groq_api_key
from swarmshield.llm.budget import TokenBudget
from swarmshield.llm.cache import DEFAULT_DIR
from swarmshield.llm.client import LLMClient


def groq_backend(
    model: str, messages: list[dict], temperature: float | None, seed: int | None, settings: dict
) -> tuple[str, int]:
    from groq import Groq, RateLimitError

    key = groq_api_key()
    if not key:
        raise RuntimeError("SWARMSHIELD_GROQ_API_KEY is not set")
    client = Groq(api_key=key)
    kwargs = dict(settings)
    if temperature is not None:
        kwargs["temperature"] = temperature
    if seed is not None:
        kwargs["seed"] = seed
    for attempt in range(6):
        try:
            resp = client.chat.completions.create(model=model, messages=messages, **kwargs)
            return resp.choices[0].message.content or "", resp.usage.total_tokens
        except RateLimitError:
            time.sleep(min(60, 5 * 2**attempt))
    raise RuntimeError("Groq rate limit not clearing; resume later (responses are cached)")


def groq_client(cfg: Config | None = None) -> LLMClient:
    cfg = cfg or Config()
    return LLMClient(
        groq_backend,
        cfg.groq_model,
        cfg.temperature,
        cfg.seed,
        settings={
            "reasoning_effort": cfg.reasoning_effort,
            "max_completion_tokens": cfg.max_completion_tokens,
        },
        budget=TokenBudget(DEFAULT_DIR, cfg.groq_model, RATE_LIMITS[cfg.groq_model]),
        expected_completion_tokens=cfg.expected_completion_tokens,
    )
