"""Central settings: topologies, defences, run limits and secrets from the environment."""

import os
from dataclasses import dataclass, field, replace
from pathlib import Path

GROQ_MODEL = "openai/gpt-oss-20b"

# Placeholder limits copied from the owner's AgentGuard project (Groq free tier, per organisation,
# reported 2026-10-16). Recheck in Step 4 and record the real ones in results/run_meta.json.
# rpm/rpd = requests per minute/day, tpm/tpd = tokens per minute/day (UTC reset).
RATE_LIMITS: dict[str, dict[str, int]] = {
    GROQ_MODEL: {"rpm": 30, "rpd": 1000, "tpm": 8000, "tpd": 200_000},
}
# Assumed, not verified. Deliberately low.
GEMINI_LIMITS = {"rpm": 10, "rpd": 200, "tpm": 100_000, "tpd": 1_000_000}

TOPOLOGIES = ("chain", "star", "mesh")
ATTACKS = ("prompt_infection", "memory_poisoning")
DEFENCES = ("d1_provenance", "d2_sanitiser", "d3_majority")

# Evaluated defence settings: none, each one alone, and all three together.
CONFIGS: dict[str, tuple[str, ...]] = {
    "none": (),
    **{name.split("_")[0]: (name,) for name in DEFENCES},
    "all": DEFENCES,
}

# The 6-agent swarm used for topology experiments (PLAN.md): roles and how many of each.
SWARM_ROLES: dict[str, int] = {"planner": 1, "researcher": 3, "writer": 2}


@dataclass(frozen=True)
class Config:
    rounds: int = 4
    temperature: float = 0.0
    seed: int = 42
    groq_model: str = GROQ_MODEL
    reasoning_effort: str = "low"
    max_completion_tokens: int = 400
    expected_completion_tokens: int = 150
    gemini_model: str = "gemini-3.5-flash-lite"
    defences: frozenset[str] = field(default_factory=frozenset)

    def with_defences(self, *names: str) -> "Config":
        unknown = set(names) - set(DEFENCES)
        if unknown:
            raise ValueError(f"unknown defences: {sorted(unknown)}")
        return replace(self, defences=frozenset(names))

    def enabled(self, name: str) -> bool:
        return name in self.defences


def load_env(path: Path = Path(".env")) -> None:
    """Copy SWARMSHIELD_* lines from a local .env into the environment (never overriding it)."""
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        name, sep, value = line.partition("=")
        name = name.strip()
        if sep and name.startswith("SWARMSHIELD_") and value.strip():
            os.environ.setdefault(name, value.strip().strip("\"'"))


def groq_api_key() -> str | None:
    return os.environ.get("SWARMSHIELD_GROQ_API_KEY") or None


def gemini_api_key() -> str | None:
    return os.environ.get("SWARMSHIELD_GEMINI_API_KEY") or None
