"""Run one attacked episode and read off the markers."""

import json
from pathlib import Path

from swarmshield.attacks import plan_attack
from swarmshield.attacks.canary import make_canary
from swarmshield.config import Config
from swarmshield.llm.client import LLMClient
from swarmshield.scoring import infected_agents
from swarmshield.swarm.runtime import EpisodeResult, run_episode
from swarmshield.swarm.topology import agent_ids, build_topology

PAYLOADS = Path("data/payloads.jsonl")


def load_payloads(path: Path = PAYLOADS) -> list[dict]:
    return [json.loads(line) for line in path.read_text("utf-8").splitlines() if line.strip()]


def run_attack(
    attack: str,
    task: dict,
    payload: dict,
    topology: str,
    llm: LLMClient,
    cfg: Config | None = None,
    run_id: str | None = None,
    **attack_kwargs,
) -> tuple[EpisodeResult, dict[str, int]]:
    """Returns the episode result and {agent: first round it emitted the canary}."""
    cfg = cfg or Config()
    run_id = run_id or f"{attack}-{topology}-{task['task_id']}-{payload['payload_id']}"
    canary = make_canary(cfg.seed, run_id)
    plan = plan_attack(attack, task, payload, canary, **attack_kwargs)
    result = run_episode(
        plan.task, build_topology(topology), llm, cfg.rounds, run_id,
        canary=canary, memory_seeds=plan.memory_seeds,
    )  # fmt: skip
    return result, infected_agents(result.log.events, canary)


def infection_rate(infected: dict[str, int]) -> float:
    return len(infected) / len(agent_ids())
