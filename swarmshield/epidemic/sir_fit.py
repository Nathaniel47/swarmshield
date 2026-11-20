"""A discrete-time SIR model on the agent graph, and a grid-search fit to observed curves.

Each round, a susceptible agent with k infected neighbours is infected with probability
1-(1-beta)^k; an infected agent recovers (and stays immune) with probability gamma. In
`seed="node"` mode the model starts with one infected agent (patient zero, the attack's entry
point). In `seed="memory"` mode, which models a poisoned shared store, every agent is infected in
round 1 with probability epsilon instead (exposure that does not travel along edges).
Simulation is Monte Carlo over `runs` seeded runs; the fit minimises the squared error between
the simulated and observed mean fraction of agents ever infected by each round. The cumulative
curve is fitted because an agent in the scripted system can fall quiet for a round and speak
again, so "currently infectious" flickers while "ever infected" is monotone.
"""

import itertools

import networkx as nx
import numpy as np

BETAS = np.round(np.linspace(0.0, 1.0, 11), 2)
GAMMAS = np.round(np.linspace(0.0, 1.0, 6), 2)
EPSILONS = np.round(np.linspace(0.0, 1.0, 6), 2)


def simulate(
    graph: nx.Graph,
    beta: float,
    gamma: float,
    rounds: int,
    patient_zero: str | None = None,
    epsilon: float = 0.0,
    runs: int = 200,
    seed: int = 0,
) -> np.ndarray:
    """Mean fraction of agents ever infected (infected or recovered) by each round 1..rounds."""
    rng = np.random.default_rng(seed)
    nodes = list(graph)
    adj = nx.to_numpy_array(graph, nodelist=nodes)
    n = len(nodes)
    infected = np.zeros((runs, n), dtype=bool)
    removed = np.zeros((runs, n), dtype=bool)
    if patient_zero is not None:
        infected[:, nodes.index(patient_zero)] = True
    else:
        infected = rng.random((runs, n)) < epsilon
    curve = [(infected | removed).mean()]
    for _ in range(rounds - 1):
        k = infected.astype(float) @ adj
        p_new = 1 - (1 - beta) ** k
        new = (rng.random((runs, n)) < p_new) & ~infected & ~removed
        recover = infected & (rng.random((runs, n)) < gamma)
        removed |= recover
        infected = (infected & ~recover) | new
        curve.append((infected | removed).mean())
    return np.array(curve)


def fit_sir(
    graph: nx.Graph,
    observed: list[float],
    seed_mode: str = "node",
    patient_zero: str | None = "researcher-1",
    runs: int = 200,
    seed: int = 0,
) -> dict:
    """Best (beta, gamma, epsilon) and its mean squared error against `observed` (fraction ever
    infected by each round)."""
    if seed_mode not in ("node", "memory"):
        raise ValueError("seed_mode must be 'node' or 'memory'")
    rounds = len(observed)
    obs = np.array(observed)
    eps_grid = EPSILONS if seed_mode == "memory" else [0.0]
    best = None
    for beta, gamma, eps in itertools.product(BETAS, GAMMAS, eps_grid):
        sim = simulate(
            graph, beta, gamma, rounds,
            patient_zero if seed_mode == "node" else None, eps, runs, seed,
        )  # fmt: skip
        mse = float(np.mean((sim - obs) ** 2))
        if best is None or mse < best["mse"] - 1e-12:
            best = {"beta": float(beta), "gamma": float(gamma), "epsilon": float(eps), "mse": mse}
    return best


def predict(graph: nx.Graph, params: dict, rounds: int, seed_mode: str = "node", **kw) -> list:
    pz = "researcher-1" if seed_mode == "node" else None
    sim = simulate(graph, params["beta"], params["gamma"], rounds, pz, params["epsilon"], **kw)
    return sim.tolist()
