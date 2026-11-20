"""The single entry point for LLM calls: cache, then budget, then a pluggable backend."""

from collections.abc import Callable

from swarmshield.llm.budget import TokenBudget, estimate_tokens
from swarmshield.llm.cache import ResponseCache, cache_key

# backend(model, messages, temperature, seed, settings) -> (text, tokens_used)
Backend = Callable[[str, list[dict], float | None, int | None, dict], tuple[str, int]]


class LLMClient:
    def __init__(
        self,
        backend: Backend,
        model: str,
        temperature: float | None,
        seed: int | None,
        cache: ResponseCache | None = None,
        settings: dict | None = None,
        budget: TokenBudget | None = None,
        expected_completion_tokens: int = 150,
    ):
        self.backend = backend
        self.model = model
        self.temperature = temperature
        self.seed = seed
        self.cache = cache or ResponseCache()
        self.settings = settings or {}
        self.budget = budget
        self.expected_completion = expected_completion_tokens
        self.calls = 0
        self.cache_hits = 0
        self.tokens_used = 0  # tokens actually billed by the API
        # What a run costs with no cache: every call counted, tokens estimated from the text.
        self.logical_calls = 0
        self.est_tokens = 0

    def complete(self, prompt: str, system: str | None = None, repeat: int = 0) -> str:
        """`repeat` is part of the cache key so repeated runs stay independent."""
        messages = ([{"role": "system", "content": system}] if system else []) + [
            {"role": "user", "content": prompt}
        ]
        key = cache_key(self.model, messages, self.temperature, self.seed, repeat, self.settings)
        self.logical_calls += 1
        prompt_tokens = estimate_tokens((system or "") + prompt)
        hit = self.cache.get(key)
        if hit is not None:
            self.cache_hits += 1
            self.est_tokens += prompt_tokens + estimate_tokens(hit)
            return hit
        est = prompt_tokens + self.expected_completion
        if self.budget:
            self.budget.before_call(est)
        text, tokens = self.backend(
            self.model, messages, self.temperature, self.seed, self.settings
        )
        tokens = tokens or est
        if self.budget:
            self.budget.record(tokens)
        self.calls += 1
        self.tokens_used += tokens
        self.est_tokens += prompt_tokens + estimate_tokens(text)
        self.cache.put(key, text)
        return text
