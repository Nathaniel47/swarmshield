import pytest

from swarmshield.epidemic.analysis import analyse, to_markdown
from swarmshield.epidemic.metrics import curves, emit_rounds, summary
from swarmshield.epidemic.sir_fit import fit_sir, predict, simulate
from swarmshield.swarm.topology import build_topology

C = "CANARY-0123456789"


def ev(round_, agent, text=C, kind="message"):
    return {"kind": kind, "round": round_, "agent": agent, "text": text}


def test_curves_count_susceptible_infected_and_recovered():
    events = [
        ev(1, "researcher-1"),
        ev(2, "researcher-1", kind="report"),
        ev(2, "researcher-2"),
        ev(3, "researcher-2"),
        ev(1, "planner-1", text="no canary here"),
    ]
    cur = curves(events, C, rounds=3)
    assert cur["I"] == [1, 2, 1]
    assert cur["R"] == [0, 0, 1]
    assert cur["S"] == [5, 4, 4]
    assert all(s + i + r == 6 for s, i, r in zip(cur["S"], cur["I"], cur["R"], strict=True))
    assert set(emit_rounds(events, C)) == {"researcher-1", "researcher-2"}


def test_summary_numbers():
    cur = {"S": [5, 4, 2, 2], "I": [1, 2, 3, 1], "R": [0, 0, 1, 3]}
    s = summary(cur)
    assert s["infection_rate"] == pytest.approx(4 / 6)
    assert (s["peak_infected"], s["time_to_peak"]) == (3, 3)
    assert s["rounds_to_full"] is None
    assert s["spread_speed"] == pytest.approx(4 / 3)


def test_summary_when_nothing_is_infected():
    s = summary({"S": [6, 6], "I": [0, 0], "R": [0, 0]})
    assert s["infection_rate"] == 0 and s["time_to_peak"] is None and s["spread_speed"] == 0.0


def test_simulation_basics():
    chain, mesh = build_topology("chain"), build_topology("mesh")
    none = simulate(chain, 0.0, 0.0, 5, "researcher-1")
    assert list(none) == [pytest.approx(1 / 6)] * 5
    full = simulate(chain, 1.0, 0.0, 6, "researcher-1")
    assert full[-1] == pytest.approx(1.0)
    assert (
        simulate(chain, 0.3, 0.1, 5, "researcher-1", seed=3).tolist()
        == simulate(chain, 0.3, 0.1, 5, "researcher-1", seed=3).tolist()
    )
    assert (
        simulate(mesh, 0.3, 0.0, 3, "researcher-1")[-1]
        > simulate(chain, 0.3, 0.0, 3, "researcher-1")[-1]
    )


def test_memory_mode_infects_without_a_patient_zero():
    cur = simulate(build_topology("chain"), 0.0, 0.0, 3, None, epsilon=1.0)
    assert list(cur) == [1.0, 1.0, 1.0]


def test_fit_recovers_known_parameters():
    graph = build_topology("star")
    truth = {"beta": 0.4, "gamma": 0.2, "epsilon": 0.0}
    observed = predict(graph, truth, 6, "node", runs=2000, seed=11)
    fit = fit_sir(graph, observed, runs=2000, seed=11)
    assert fit["beta"] == pytest.approx(0.4, abs=0.11)
    assert fit["mse"] < 0.001


def test_fit_rejects_unknown_mode():
    with pytest.raises(ValueError):
        fit_sir(build_topology("chain"), [0.1, 0.2], seed_mode="x")


def test_full_analysis_runs_and_mesh_spreads_wider_than_chain():
    res = analyse(susceptibility=0.5, seeds=1)
    cells = res["cells"]
    assert res["episodes"] == 19 * 2 * 3
    a1 = "prompt_infection"
    assert cells[f"{a1}/mesh"]["infection_rate"] >= cells[f"{a1}/chain"]["infection_rate"]
    assert "| prompt_infection/chain |" in to_markdown(res)
