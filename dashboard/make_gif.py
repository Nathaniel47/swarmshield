"""Render docs/demo.gif: the same worm on a mesh, with no defence and with all three.

    python -m dashboard.make_gif

This is drawn from real simulator runs (the same `simulate_run` the dashboard uses), not a screen
recording. It shows the scripted agent, and says so in the picture. Needs requirements-dev.
"""

from pathlib import Path

from dashboard.graph import STATE_COLOURS, STATE_NAMES, positions
from dashboard.runner import simulate_run
from swarmshield.config import DEFENCES
from swarmshield.swarm.topology import build_topology

OUT = Path("docs/demo.gif")
TOPOLOGY = "mesh"
ROUNDS = 6
PANELS = (("No defence", ()), ("All three defences", DEFENCES))


def panel_runs() -> list[tuple[str, dict]]:
    return [
        (
            title,
            simulate_run(
                TOPOLOGY,
                "prompt_infection",
                tuple(names),
                1.0,
                0.2,
                ROUNDS,
                0,
                "a1-g000",
                "t000",
            ),  # fmt: skip
        )
        for title, names in PANELS
    ]


def make_gif(out: Path = OUT) -> Path:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.animation import FuncAnimation, PillowWriter
    from matplotlib.lines import Line2D

    graph = build_topology(TOPOLOGY)
    pos = positions(graph, TOPOLOGY)
    runs = panel_runs()
    fig, axes = plt.subplots(1, len(runs), figsize=(9, 4.8))

    def draw(frame: int):
        index = min(frame, ROUNDS)  # the extra frames hold the final state
        for ax, (title, run) in zip(axes, runs, strict=True):
            ax.clear()
            states = run["states"][index]
            for u, v in graph.edges:
                ax.plot(*zip(pos[u], pos[v], strict=True), color="#c3ccd5", lw=1.2, zorder=1)
            for node, (x, y) in pos.items():
                ax.scatter(
                    x, y, s=620, color=STATE_COLOURS[states[node]], edgecolor="#1f2933", zorder=2
                )
                ax.text(x, y + 0.22, node.replace("-", " "), ha="center", fontsize=8)
            verdict = ""
            if index == ROUNDS:
                verdict = "\nfinal report: " + ("OK" if run["success"] else "hijacked")
            ax.set_title(f"{title}{verdict}", fontsize=11)
            ax.set_xlim(-1.5, 1.5)
            ax.set_ylim(-1.35, 1.5)
            ax.set_aspect("equal")
            ax.axis("off")
        fig.suptitle(
            f"Prompt infection on a mesh, {'start' if index == 0 else f'round {index}'}",
            fontsize=13,
        )

    legend = [
        Line2D([], [], marker="o", ls="", markersize=9, color=STATE_COLOURS[k], label=v)
        for k, v in STATE_NAMES.items()
    ]
    fig.legend(
        handles=legend, loc="lower center", ncol=3, frameon=False, bbox_to_anchor=(0.5, 0.05)
    )
    fig.text(
        0.5, 0.015, "Simulation with a scripted stand-in agent, not a real language model.",
        ha="center", fontsize=8, color="#52606d",
    )  # fmt: skip
    fig.subplots_adjust(left=0.02, right=0.98, bottom=0.15, top=0.82, wspace=0.05)
    out.parent.mkdir(parents=True, exist_ok=True)
    FuncAnimation(fig, draw, frames=ROUNDS + 4).save(out, writer=PillowWriter(fps=1), dpi=100)
    plt.close(fig)
    return out


if __name__ == "__main__":
    print(make_gif())
