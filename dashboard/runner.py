"""Run one scripted episode for the dashboard and return everything it draws."""

from swarmshield.attacks.canary import make_canary
from swarmshield.config import Config
from swarmshield.defences import DefenceSet
from swarmshield.epidemic.metrics import curves, summary
from swarmshield.epidemic.states import agent_states
from swarmshield.experiments import load_payloads, load_tasks, run_attack
from swarmshield.run_episode import make_client

ATTACK_LABELS = {
    "prompt_infection": "Prompt infection (worm in a document)",
    "memory_poisoning": "Memory poisoning (note in shared memory)",
}


def simulate_run(
    topology: str,
    attack: str,
    defences: tuple[str, ...],
    susceptibility: float,
    fence_effect: float,
    rounds: int,
    seed: int,
    payload_id: str,
    task_id: str,
    style: str = "forged",
) -> dict:
    payload = next(p for p in load_payloads() if p["payload_id"] == payload_id)
    task = next(t for t in load_tasks() if t["task_id"] == task_id)
    cfg = Config(rounds=rounds, seed=seed)
    run_id = f"demo-{attack}-{topology}-{task_id}-{payload_id}-s{seed}"
    llm = make_client("scripted", cfg, susceptibility, fence_effect)
    kwargs = {"style": style} if attack == "memory_poisoning" else {}
    result, infected = run_attack(
        attack, task, payload, topology, llm, cfg, run_id, DefenceSet(frozenset(defences)), **kwargs
    )
    canary = make_canary(seed, run_id)
    cur = curves(result.log.events, canary, rounds)
    carried = [
        {"round": e["round"], "from": e["agent"], "to": e["to"], "text": e["text"]}
        for e in result.log.events
        if e["kind"] == "message" and canary in e["text"]
    ]
    return {
        "states": agent_states(result.log.events, canary, rounds),
        "curves": cur,
        "summary": summary(cur),
        "infected": infected,
        "report": result.report,
        "success": result.success,
        "llm_calls": result.llm_calls,
        "carried_messages": carried,
        "canary": canary,
    }
