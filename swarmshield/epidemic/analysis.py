"""Epidemic analysis on the dev split with the scripted agent:

    python -m swarmshield.epidemic.analysis

Writes results/epidemic_dev.json and results/epidemic_dev.md. The test split is reserved for the
final evaluation (Step 6), so nothing here is tuned on it.
"""

import json
import statistics
from pathlib import Path

from swarmshield.config import TOPOLOGIES
from swarmshield.epidemic.sir_fit import fit_sir, predict
from swarmshield.experiments import load_payloads, load_tasks, run_grid
from swarmshield.swarm.topology import agent_ids, build_topology

SUSCEPTIBILITY = 0.5
SEEDS = 10
ROUNDS = 6
OUT = Path("results")


def mean_fraction_ever_infected(rows: list[dict]) -> list[float]:
    n = len(agent_ids())
    return [statistics.mean(n - r["curves"]["S"][i] for r in rows) / n for i in range(ROUNDS)]


def _mean(rows: list[dict], key: str) -> float | None:
    vals = [r[key] for r in rows if r[key] is not None]
    return statistics.mean(vals) if vals else None


def analyse(susceptibility: float = SUSCEPTIBILITY, seeds: int = SEEDS) -> dict:
    tasks = [t for t in load_tasks() if t["split"] == "dev"]
    payloads = [p for p in load_payloads() if p["split"] == "dev"]
    rows = run_grid(tasks, payloads, TOPOLOGIES, susceptibility, seeds, ROUNDS)
    result: dict = {
        "susceptibility": susceptibility, "seeds": seeds, "rounds": ROUNDS,
        "episodes": len(rows), "cells": {}, "fits": {}, "cross_topology": {},
    }  # fmt: skip
    fits: dict = {}
    for attack in ("prompt_infection", "memory_poisoning"):
        mode = "node" if attack == "prompt_infection" else "memory"
        for topology in TOPOLOGIES:
            cell = [r for r in rows if r["attack"] == attack and r["topology"] == topology]
            observed = mean_fraction_ever_infected(cell)
            result["cells"][f"{attack}/{topology}"] = {
                "episodes": len(cell),
                "infection_rate": _mean(cell, "infection_rate"),
                "time_to_peak": _mean(cell, "time_to_peak"),
                "peak_infected": _mean(cell, "peak_infected"),
                "spread_speed": _mean(cell, "spread_speed"),
                "task_success": statistics.mean(r["success"] for r in cell),
                "mean_fraction_ever_infected": observed,
            }
            fit = fit_sir(build_topology(topology), observed, seed_mode=mode)
            fits[(attack, topology)] = fit
            result["fits"][f"{attack}/{topology}"] = fit
        # Fit on the chain only, then predict the other topologies with the same parameters.
        for topology in TOPOLOGIES:
            observed = result["cells"][f"{attack}/{topology}"]["mean_fraction_ever_infected"]
            pred = predict(build_topology(topology), fits[(attack, "chain")], ROUNDS, mode)
            result["cross_topology"][f"{attack}/{topology}"] = sum(
                (p - o) ** 2 for p, o in zip(pred, observed, strict=True)
            ) / len(observed)
    return result


def to_markdown(res: dict) -> str:
    def f(x, nd=2):
        return "-" if x is None else f"{x:.{nd}f}"

    lines = [
        "# Epidemic analysis (dev split, scripted agent)",
        "",
        f"Susceptibility {res['susceptibility']}, {res['seeds']} seeds, {res['rounds']} rounds, "
        f"{res['episodes']} episodes, no defences. Dev split only; test is reserved for Step 6.",
        "",
        "| attack / topology | infection rate | time to peak | peak infected | spread speed "
        "| task success |",
        "|---|---|---|---|---|---|",
    ]
    for key, c in res["cells"].items():
        lines.append(
            f"| {key} | {f(c['infection_rate'])} | {f(c['time_to_peak'])} | "
            f"{f(c['peak_infected'])} | {f(c['spread_speed'])} | {f(c['task_success'])} |"
        )
    lines += [
        "",
        "## SIR fit",
        "",
        "Per-cell grid-search fit to the share of agents ever infected by each round (beta: "
        "per-contact infection chance, gamma: recovery chance, epsilon: round-1 exposure from "
        "the shared store, used for memory poisoning only), with its mean squared error. The "
        "last column predicts each topology from the parameters fitted on the chain alone.",
        "",
        "| attack / topology | beta | gamma | epsilon | fit MSE | MSE predicting from chain fit |",
        "|---|---|---|---|---|---|",
    ]
    for key, fit in res["fits"].items():
        lines.append(
            f"| {key} | {f(fit['beta'])} | {f(fit['gamma'])} | {f(fit['epsilon'])} | "
            f"{fit['mse']:.4f} | {res['cross_topology'][key]:.4f} |"
        )
    lines.append("")
    return "\n".join(lines)


def main() -> None:
    res = analyse()
    OUT.mkdir(exist_ok=True)
    (OUT / "epidemic_dev.json").write_text(json.dumps(res, indent=2) + "\n", "utf-8")
    text = to_markdown(res)
    (OUT / "epidemic_dev.md").write_text(text, "utf-8")
    print(text)


if __name__ == "__main__":
    main()
