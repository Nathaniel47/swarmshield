"""A few full six-agent episodes on a real model, to see whether the worm actually travels.

    python -m swarmshield.real_episodes --backend groq     # 2 payloads x 3 topologies

Prompt infection, no defences, development split. Two things are recorded separately:
*emitted* (the canary is anywhere in an agent's raw reply, including text the reply parser
drops) and *infected* (the canary reached a note, a message or the report, which is how the
rest of the project defines it). Results are saved after every episode, and every model reply
is cached, so an interrupted run can be repeated without paying twice.
"""

import argparse
import json
from pathlib import Path

from swarmshield.attacks.canary import make_canary
from swarmshield.calibration import pick_payloads
from swarmshield.config import TOPOLOGIES, Config, load_env
from swarmshield.experiments import load_payloads, load_tasks, run_attack
from swarmshield.llm.budget import DailyBudgetExhausted
from swarmshield.llm.client import LLMClient
from swarmshield.llm.meta import update_run_meta
from swarmshield.run_episode import make_client

OUT = Path("results/real_episodes.json")
OUT_WHOLE = Path("results/real_episodes_whole_reply.json")
ATTACK = "prompt_infection"


def describe(events: list[dict], canary: str) -> dict:
    """Where the canary went in one episode, from its run log."""
    emitted: dict[str, int] = {}
    for e in events:
        if e["kind"] == "llm_call" and canary in e["reply"]:
            emitted.setdefault(e["agent"], e["round"])
    messages = [e for e in events if e["kind"] == "message"]
    return {
        "emitted": emitted,
        "messages_sent": len(messages),
        "messages_with_canary": sum(canary in e["text"] for e in messages),
        "empty_replies": sum(e["kind"] == "llm_call" and not e["reply"].strip() for e in events),
    }


def run(
    llm: LLMClient,
    cfg: Config,
    n_payloads: int = 2,
    out: Path | None = None,
    relay_whole_reply: bool = False,
) -> dict:
    task_list = [t for t in load_tasks() if t["split"] == "dev"]
    payloads = pick_payloads(load_payloads(), ATTACK, n_payloads)
    result: dict = {"episodes": [], "stopped_early": ""}
    for i, payload in enumerate(payloads):
        task = task_list[i % len(task_list)]
        for topology in TOPOLOGIES:
            run_id = f"real-{topology}-{task['task_id']}-{payload['payload_id']}"
            used0 = llm.tokens_used
            try:
                episode, infected = run_attack(
                    ATTACK,
                    task,
                    payload,
                    topology,
                    llm,
                    cfg,
                    run_id,
                    relay_whole_reply=relay_whole_reply,
                )
            except DailyBudgetExhausted as exc:
                result["stopped_early"] = str(exc)
                return result
            canary = make_canary(cfg.seed, run_id)
            row = {
                "topology": topology,
                "payload_id": payload["payload_id"],
                "source": payload["source"],
                "task_id": task["task_id"],
                "infected": infected,
                **describe(episode.log.events, canary),
                "report_has_canary": canary in episode.report,
                "task_success": episode.success,
                "llm_calls": episode.llm_calls,
                "new_tokens": llm.tokens_used - used0,
                "report": episode.report,
                "events": [e for e in episode.log.events if e["kind"] == "llm_call"],
            }
            result["episodes"].append(row)
            if out:
                out.parent.mkdir(parents=True, exist_ok=True)
                out.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", "utf-8")
            print(
                f"{topology} {payload['payload_id']}: emitted {sorted(row['emitted'])} "
                f"infected {sorted(infected)} tokens {row['new_tokens']}",
                flush=True,
            )
    return result


def main() -> None:
    load_env()
    ap = argparse.ArgumentParser()
    ap.add_argument("--backend", default="groq", choices=["scripted", "groq", "gemini"])
    ap.add_argument("--payloads", type=int, default=2)
    ap.add_argument("--rounds", type=int, default=Config().rounds)
    ap.add_argument("--out", type=Path)
    ap.add_argument(
        "--relay",
        default="message",
        choices=["message", "whole"],
        help="forward only the MESSAGE field (default) or each agent's whole reply",
    )
    args = ap.parse_args()
    cfg = Config(rounds=args.rounds)
    llm = make_client(args.backend, cfg)
    whole = args.relay == "whole"
    args.out = args.out or (OUT_WHOLE if whole else OUT)
    result = run(llm, cfg, args.payloads, args.out, whole)
    result["settings"] = {
        "backend": args.backend,
        "model": llm.model,
        "temperature": cfg.temperature,
        "seed": cfg.seed,
        "rounds": cfg.rounds,
        "relay": args.relay,
        "new_calls": llm.calls,
        "cache_hits": llm.cache_hits,
        "tokens_used": llm.tokens_used,
    }
    args.out.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", "utf-8")
    if args.backend != "scripted":
        key = "real_episodes_whole_reply" if whole else "real_episodes"
        update_run_meta(**{key: result["settings"]})
    print(json.dumps({"settings": result["settings"], "stopped_early": result["stopped_early"]}))


if __name__ == "__main__":
    main()
