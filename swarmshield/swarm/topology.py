"""Agent networks. Edges say who may message whom; shared memory is global and ignores them."""

import networkx as nx

from swarmshield.config import SWARM_ROLES, TOPOLOGIES


def agent_ids() -> list[str]:
    """Stable order: planner, then researchers, then writers (also the order they act in)."""
    return [f"{role}-{i}" for role, n in SWARM_ROLES.items() for i in range(1, n + 1)]


def role_of(agent_id: str) -> str:
    return agent_id.rsplit("-", 1)[0]


def build_topology(name: str) -> nx.Graph:
    if name not in TOPOLOGIES:
        raise ValueError(f"unknown topology {name!r}; choose from {TOPOLOGIES}")
    ids = agent_ids()
    graph = nx.Graph()
    graph.add_nodes_from(ids)
    if name == "chain":
        graph.add_edges_from(zip(ids, ids[1:], strict=False))
    elif name == "star":
        graph.add_edges_from((ids[0], other) for other in ids[1:])
    else:
        graph = nx.complete_graph(ids)
    for node in graph:
        graph.nodes[node]["role"] = role_of(node)
    return graph
