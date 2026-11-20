"""SwarmShield live graph dashboard: watch an attack spread through a simulated agent swarm.

    streamlit run dashboard/app.py

Runs the offline scripted agent (instant, no API key). Everything shown is synthetic.
"""

from pathlib import Path

import streamlit as st

from dashboard.graph import STATE_COLOURS, STATE_NAMES, curves_figure, graph_figure
from dashboard.runner import ATTACK_LABELS, simulate_run
from swarmshield.config import CONFIGS, DEFENCES, TOPOLOGIES
from swarmshield.experiments import load_payloads, load_tasks
from swarmshield.swarm.topology import build_topology

st.set_page_config(page_title="SwarmShield", layout="wide")

PAYLOADS = load_payloads()
TASKS = load_tasks()
DEFENCE_LABELS = {
    "d1_provenance": "D1 provenance tags",
    "d2_sanitiser": "D2 message sanitiser",
    "d3_majority": "D3 majority check",
}
PRESETS = {
    "Worm on a mesh, no defence": {
        "topology": "mesh", "attack": "prompt_infection", "defences": [], "susceptibility": 1.0,
    },
    "Worm on a chain, no defence": {
        "topology": "chain", "attack": "prompt_infection", "defences": [], "susceptibility": 1.0,
    },
    "Worm on a mesh, all defences": {
        "topology": "mesh", "attack": "prompt_infection", "defences": list(DEFENCES),
        "susceptibility": 1.0,
    },
    "Poisoned memory, sanitiser only": {
        "topology": "star", "attack": "memory_poisoning", "defences": ["d2_sanitiser"],
        "susceptibility": 1.0,
    },
}  # fmt: skip
DEFAULTS = PRESETS["Worm on a mesh, no defence"]


def apply_preset(name: str) -> None:
    for key, value in PRESETS[name].items():
        st.session_state[key] = value


for key, value in DEFAULTS.items():
    st.session_state.setdefault(key, value)

st.title("SwarmShield")
st.caption(
    "A malicious instruction spreading between cooperating LLM agents, modelled like an "
    "epidemic. A simulated swarm with a scripted stand-in for the model; all data is synthetic."
)

with st.sidebar:
    st.subheader("Try an example")
    for name in PRESETS:
        st.button(name, on_click=apply_preset, args=(name,), use_container_width=True)
    st.subheader("Or set it up")
    topology = st.selectbox("Network shape", TOPOLOGIES, key="topology")
    attack = st.radio("Attack", list(ATTACK_LABELS), format_func=ATTACK_LABELS.get, key="attack")
    style = "forged"
    if attack == "memory_poisoning":
        style = st.radio(
            "Poison written by", ["forged", "direct"],
            format_func=lambda s: {"forged": "a forged agent note (hard)",
                                   "direct": "an unknown author (easy)"}[s],
        )  # fmt: skip
    defences = tuple(
        st.multiselect("Defences", list(DEFENCES), format_func=DEFENCE_LABELS.get, key="defences")
    )
    susceptibility = st.slider(
        "How often an agent obeys planted text", 0.0, 1.0, step=0.05, key="susceptibility"
    )
    with st.expander("More settings"):
        fence_effect = st.slider(
            "Obedience left when text is fenced as untrusted (D1)", 0.0, 1.0, 0.2, 0.05
        )
        rounds = st.slider("Rounds", 3, 8, 6)
        seed = st.number_input("Random seed", 0, 999, 0)
        by_source = {p["payload_id"]: p for p in PAYLOADS if p["attack"] == attack}
        payload_id = st.selectbox(
            "Attack wording",
            list(by_source),
            format_func=lambda i: f"{i} ({by_source[i]['source']})",
        )
        task_id = st.selectbox("Task", [t["task_id"] for t in TASKS])

run_args = (topology, attack, defences, susceptibility, fence_effect, rounds, int(seed))
run = st.cache_data(simulate_run, show_spinner=False)(*run_args, payload_id, task_id, style)

tab_live, tab_compare, tab_results = st.tabs(["Live graph", "Compare defences", "Results"])

with tab_live:
    n_inf = len(run["infected"])
    s = run["summary"]
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Agents ever infected", f"{n_inf} of 6")
    c2.metric("Time to peak", f"round {s['time_to_peak']}" if s["time_to_peak"] else "none")
    c3.metric("Final report", "Clean" if run["success"] else "Compromised")
    c4.metric("LLM calls", run["llm_calls"])
    left, right = st.columns([3, 2])
    with left:
        st.plotly_chart(
            graph_figure(build_topology(topology), topology, run["states"]),
            use_container_width=True,
        )
        st.markdown(
            " ".join(
                f"<span style='color:{STATE_COLOURS[k]}'>&#9679;</span> {STATE_NAMES[k]}"
                for k in "SIR"
            ),
            unsafe_allow_html=True,
        )
    with right:
        st.plotly_chart(curves_figure(run["curves"]), use_container_width=True)
    with st.expander("Final report"):
        st.write(run["report"] or "(empty)")
    with st.expander(f"Messages that carried the infection ({len(run['carried_messages'])})"):
        st.dataframe(run["carried_messages"], use_container_width=True)

with tab_compare:
    st.write("The same attack, topology and settings under each defence setting.")
    rows = []
    for name, names in CONFIGS.items():
        r = simulate_run(
            topology, attack, tuple(names), susceptibility, fence_effect, rounds, int(seed),
            payload_id, task_id, style,
        )  # fmt: skip
        rows.append(
            {
                "defences": name,
                "agents infected": len(r["infected"]),
                "time to peak": r["summary"]["time_to_peak"],
                "report clean and correct": r["success"],
                "LLM calls": r["llm_calls"],
            }
        )
    st.dataframe(rows, use_container_width=True, hide_index=True)
    st.caption("One run per row. The Results tab has averages over many runs.")

with tab_results:
    for name in ("defences_dev.md", "epidemic_dev.md"):
        path = Path("results") / name
        if path.exists():
            st.markdown(path.read_text(encoding="utf-8"))
        else:
            st.info(f"{name} has not been generated yet.")
