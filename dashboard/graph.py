"""Plotly figures: the animated agent graph and the S/I/R curves."""

import math

import networkx as nx
import plotly.graph_objects as go

STATE_COLOURS = {"S": "#2e9e6b", "I": "#d6402f", "R": "#8a8f98"}
STATE_NAMES = {"S": "Susceptible", "I": "Infected now", "R": "Quiet after infection"}


def positions(graph: nx.Graph, topology: str) -> dict[str, tuple[float, float]]:
    nodes = list(graph)
    if topology == "chain":
        return {n: (i, 0.0) for i, n in enumerate(nodes)}
    if topology == "star":
        hub, rest = nodes[0], nodes[1:]
        pos = {hub: (0.0, 0.0)}
        for i, n in enumerate(rest):
            angle = 2 * math.pi * i / len(rest)
            pos[n] = (math.cos(angle), math.sin(angle))
        return pos
    return {
        n: (math.cos(2 * math.pi * i / len(nodes)), math.sin(2 * math.pi * i / len(nodes)))
        for i, n in enumerate(nodes)
    }


def _node_trace(pos, states: dict[str, str]) -> go.Scatter:
    nodes = list(pos)
    return go.Scatter(
        x=[pos[n][0] for n in nodes],
        y=[pos[n][1] for n in nodes],
        mode="markers+text",
        text=[n.replace("-", " ") for n in nodes],
        textposition="top center",
        marker={
            "size": 34,
            "color": [STATE_COLOURS[states[n]] for n in nodes],
            "line": {"width": 2, "color": "#1f2933"},
        },
        hovertext=[f"{n}: {STATE_NAMES[states[n]]}" for n in nodes],
        hoverinfo="text",
        showlegend=False,
    )


def graph_figure(graph: nx.Graph, topology: str, frames: list[dict[str, str]]) -> go.Figure:
    """One frame per entry of `frames` (index 0 = before round 1), with play and a slider."""
    pos = positions(graph, topology)
    edges = go.Scatter(
        x=[c for u, v in graph.edges for c in (pos[u][0], pos[v][0], None)],
        y=[c for u, v in graph.edges for c in (pos[u][1], pos[v][1], None)],
        mode="lines",
        line={"width": 2, "color": "#9aa5b1"},
        hoverinfo="skip",
        showlegend=False,
    )
    fig = go.Figure(
        data=[edges, _node_trace(pos, frames[0])],
        frames=[
            go.Frame(data=[edges, _node_trace(pos, f)], name=str(i), traces=[0, 1])
            for i, f in enumerate(frames)
        ],
    )
    steps = [
        {
            "label": "start" if i == 0 else f"round {i}",
            "method": "animate",
            "args": [[str(i)], {"mode": "immediate", "frame": {"duration": 0, "redraw": True}}],
        }
        for i in range(len(frames))
    ]
    fig.update_layout(
        height=380,
        margin={"l": 10, "r": 10, "t": 10, "b": 10},
        xaxis={"visible": False},
        yaxis={"visible": False, "scaleanchor": "x"},
        sliders=[{"steps": steps, "currentvalue": {"prefix": "Showing: "}}],
        updatemenus=[
            {
                "type": "buttons",
                "showactive": False,
                "x": 0.0,
                "y": 1.12,
                "buttons": [
                    {
                        "label": "Play",
                        "method": "animate",
                        "args": [
                            None,
                            {"frame": {"duration": 900, "redraw": True}, "fromcurrent": True},
                        ],  # fmt: skip
                    }
                ],
            }
        ],
    )
    return fig


def curves_figure(cur: dict[str, list[int]]) -> go.Figure:
    rounds = list(range(1, len(cur["S"]) + 1))
    fig = go.Figure()
    for key in ("S", "I", "R"):
        fig.add_scatter(
            x=rounds, y=cur[key], mode="lines+markers", name=STATE_NAMES[key],
            line={"color": STATE_COLOURS[key], "width": 3},
        )  # fmt: skip
    fig.update_layout(
        height=300,
        margin={"l": 10, "r": 10, "t": 10, "b": 10},
        xaxis={"title": "round", "dtick": 1},
        yaxis={"title": "agents", "range": [0, 6.2], "dtick": 1},
        legend={"orientation": "h", "y": -0.3},
    )
    return fig
