"""Run the swarm on one task, or measure the cost of a full grid.

python -m swarmshield.run_episode --task t000 --topology chain --backend scripted
python -m swarmshield.run_episode --measure          # all tasks x 3 topologies, offline
"""

import argparse
import json
import statistics
from pathlib import Path

from swarmshield.agents.scripted import scripted_backend
from swarmshield.config import TOPOLOGIES, Config, load_env
from swarmshield.llm.cache import MemoryCache
from swarmshield.llm.client import LLMClient
from swarmshield.llm.meta import update_run_meta
from swarmshield.swarm.runtime import EpisodeResult, run_episode
from swarmshield.swarm.topology import build_topology

TASKS = Path("data/tasks.jsonl")


def load_tasks(path: Path = TASKS) -> list[dict]:
    return [json.loads(line) for line in path.read_text("utf-8").splitlines() if line.strip()]


def make_client(
    backend: str, cfg: Config, susceptibility: float = 1.0, fence_effect: float = 0.2
) -> LLMClient:
    if backend == "scripted":
        return LLMClient(
            scripted_backend(susceptibility, fence_effect), "scripted", cfg.temperature, cfg.seed,
            cache=MemoryCache(),
        )  # fmt: skip
    if backend == "groq":
        from swarmshield.llm.groq import groq_client

        return groq_client(cfg)
    if backend == "gemini":
        from swarmshield.llm.gemini import gemini_client

        return gemini_client(cfg)
    raise ValueError(f"unknown backend {backend!r}")


def summarise(result: EpisodeResult) -> dict:
    return {
        "run_id": result.run_id,
        "success": result.success,
        "llm_calls": result.llm_calls,
        "est_tokens": result.est_tokens,
        "tokens_used": result.tokens_used,
        "cache_hits": result.cache_hits,
        "report": result.report,
    }


def measure(cfg: Config, tasks: list[dict]) -> dict:
    """Offline cost and success of every task on every topology with the scripted agent."""
    rows = []
    for topology in TOPOLOGIES:
        graph = build_topology(topology)
        for task in tasks:
            client = make_client("scripted", cfg)
            res = run_episode(task, graph, client, cfg.rounds, f"{topology}-{task['task_id']}")
            rows.append({"topology": topology, **summarise(res)})
    return {
        "rounds": cfg.rounds,
        "episodes": len(rows),
        "task_success_rate": sum(r["success"] for r in rows) / len(rows),
        "llm_calls_per_episode": statistics.mean(r["llm_calls"] for r in rows),
        "est_tokens_per_episode": statistics.mean(r["est_tokens"] for r in rows),
        "note": "tokens are characters/4 of prompt plus the scripted reply; real replies are "
        "longer, so treat this as a lower bound on real-LLM cost",
    }


def main() -> None:
    load_env()
    ap = argparse.ArgumentParser()
    ap.add_argument("--task", default="t000")
    ap.add_argument("--topology", default="chain", choices=TOPOLOGIES)
    ap.add_argument("--backend", default="scripted", choices=["scripted", "groq", "gemini"])
    ap.add_argument("--rounds", type=int, default=Config().rounds)
    ap.add_argument("--repeat", type=int, default=0)
    ap.add_argument("--measure", action="store_true")
    args = ap.parse_args()
    cfg = Config(rounds=args.rounds)
    tasks = load_tasks()
    if args.measure:
        out = measure(cfg, tasks)
        Path("results").mkdir(exist_ok=True)
        Path("results/episode_cost.json").write_text(json.dumps(out, indent=2) + "\n", "utf-8")
        print(json.dumps(out, indent=2))
        return
    task = next(t for t in tasks if t["task_id"] == args.task)
    client = make_client(args.backend, cfg)
    result = run_episode(
        task, build_topology(args.topology), client, cfg.rounds, args.task, args.repeat
    )
    update_run_meta(
        backend=args.backend, model=client.model, temperature=cfg.temperature, seed=cfg.seed,
        rounds=cfg.rounds, topology=args.topology,
    )  # fmt: skip
    print(json.dumps(summarise(result), indent=2))


if __name__ == "__main__":
    main()
