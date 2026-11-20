"""Run one attacked episode and read off the markers."""

import json
from pathlib import Path

from swarmshield.attacks import plan_attack
from swarmshield.attacks.canary import make_canary
from swarmshield.config import Config
from swarmshield.defences import DefenceSet
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
    defences: DefenceSet | None = None,
    **attack_kwargs,
) -> tuple[EpisodeResult, dict[str, int]]:
    """Returns the episode result and {agent: first round it emitted the canary}."""
    cfg = cfg or Config()
    run_id = run_id or f"{attack}-{topology}-{task['task_id']}-{payload['payload_id']}"
    canary = make_canary(cfg.seed, run_id)
    plan = plan_attack(attack, task, payload, canary, **attack_kwargs)
    result = run_episode(
        plan.task, build_topology(topology), llm, cfg.rounds, run_id,
        canary=canary, memory_seeds=plan.memory_seeds, defences=defences,
    )  # fmt: skip
    return result, infected_agents(result.log.events, canary)


def infection_rate(infected: dict[str, int]) -> float:
    return len(infected) / len(agent_ids())


def load_tasks(path: Path = Path("data/tasks.jsonl")) -> list[dict]:
    return [json.loads(line) for line in path.read_text("utf-8").splitlines() if line.strip()]


def run_grid(
    tasks: list[dict],
    payloads: list[dict],
    topologies: tuple[str, ...],
    susceptibility: float,
    seeds: int,
    rounds: int,
    attack_kwargs: dict | None = None,
    defences: tuple[str, ...] = (),
    fence_effect: float = 0.2,
) -> list[dict]:
    """Scripted-agent grid: every payload on every topology for `seeds` seeds. Payload i uses
    task i mod len(tasks). One row per episode, with S/I/R curves and summary numbers."""
    from swarmshield.epidemic.metrics import curves, summary
    from swarmshield.run_episode import make_client

    rows = []
    for seed in range(seeds):
        cfg = Config(rounds=rounds, seed=seed)
        for i, payload in enumerate(payloads):
            task = tasks[i % len(tasks)]
            for topology in topologies:
                llm = make_client("scripted", cfg, susceptibility, fence_effect)
                attack = payload["attack"]
                kw = (attack_kwargs or {}).get(attack, {})
                run_id = f"{attack}-{topology}-{task['task_id']}-{payload['payload_id']}-s{seed}"
                result, infected = run_attack(
                    attack,
                    task,
                    payload,
                    topology,
                    llm,
                    cfg,
                    run_id,
                    DefenceSet(frozenset(defences)),
                    **kw,
                )
                canary = make_canary(cfg.seed, run_id)
                cur = curves(result.log.events, canary, rounds)
                rows.append(
                    {
                        "topology": topology, "attack": attack, "payload_id": payload["payload_id"],
                        "source": payload["source"], "split": payload["split"],
                        "task_id": task["task_id"], "seed": seed,
                        "susceptibility": susceptibility, "defences": "+".join(defences) or "none",
                        "success": result.success, "compromised": canary in result.report,
                        "llm_calls": result.llm_calls, "curves": cur, **summary(cur),
                    }
                )  # fmt: skip
    return rows
