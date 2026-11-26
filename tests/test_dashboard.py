from pathlib import Path

import networkx as nx
import pytest
from streamlit.testing.v1 import AppTest

from dashboard.graph import curves_figure, graph_figure, positions
from dashboard.runner import simulate_run
from swarmshield.config import TOPOLOGIES
from swarmshield.epidemic.states import agent_states
from swarmshield.swarm.topology import agent_ids, build_topology

APP = Path(__file__).resolve().parent.parent / "dashboard" / "app.py"


def run(defences=(), **kw):
    args = ("mesh", "prompt_infection", defences, 1.0, 0.2, 6, 0)
    return simulate_run(*args, "a1-g000", "t000", **kw)


def test_agent_states_follow_the_log():
    c = "CANARY-0123456789"
    events = [
        {"kind": "message", "round": 1, "agent": "researcher-1", "text": c},
        {"kind": "message", "round": 3, "agent": "researcher-1", "text": c},
    ]
    frames = agent_states(events, c, 3)
    assert len(frames) == 4
    assert {v for v in frames[0].values()} == {"S"}
    assert [f["researcher-1"] for f in frames] == ["S", "I", "R", "I"]
    assert frames[3]["planner-1"] == "S"


def test_simulate_run_returns_what_the_dashboard_draws():
    out = run()
    assert len(out["states"]) == 7 and set(out["states"][0]) == set(agent_ids())
    assert out["states"][-1]["researcher-1"] in ("I", "R")
    assert len(out["infected"]) == 6 and not out["success"]
    assert out["carried_messages"] and out["canary"] in out["carried_messages"][0]["text"]
    defended = run(("d1_provenance", "d2_sanitiser", "d3_majority"))
    assert defended["success"] and len(defended["infected"]) < 6


@pytest.mark.parametrize("topology", TOPOLOGIES)
def test_figures_have_one_frame_per_round_and_a_node_per_agent(topology):
    graph = build_topology(topology)
    pos = positions(graph, topology)
    assert set(pos) == set(graph) and len(set(pos.values())) == 6
    fig = graph_figure(graph, topology, run()["states"])
    assert len(fig.frames) == 7
    assert len(fig.data[1].x) == 6
    assert len(curves_figure(run()["curves"]).data) == 3


def test_positions_are_a_line_for_a_chain():
    pos = positions(nx.path_graph(["a", "b", "c"]), "chain")
    assert [pos[n][1] for n in "abc"] == [0, 0, 0]


def test_app_runs_without_errors_and_presets_change_the_setup():
    at = AppTest.from_file(str(APP), default_timeout=60).run()
    assert not at.exception
    assert at.session_state["topology"] == "mesh"
    chain = next(b for b in at.sidebar.button if b.label == "Worm on a chain, no defence")
    chain.click().run()
    assert not at.exception
    assert at.session_state["topology"] == "chain"
    allm = next(b for b in at.sidebar.button if b.label == "Worm on a mesh, all defences")
    allm.click().run()
    assert at.session_state["defences"] == ["d1_provenance", "d2_sanitiser", "d3_majority"]
    assert not at.exception


def test_results_tab_warns_that_real_model_checks_disagree():
    at = AppTest.from_file(str(APP), default_timeout=60).run()
    assert any("real model" in w.value for w in at.warning)


def test_demo_gif_panels_match_what_the_gif_claims():
    from dashboard.make_gif import panel_runs

    (_, undefended), (_, defended) = panel_runs()
    assert not undefended["success"] and len(undefended["infected"]) == 6
    assert defended["success"] and not defended["infected"]
