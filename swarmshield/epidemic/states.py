"""Per-agent infection state in each round, for drawing the graph."""

from swarmshield.epidemic.metrics import emit_rounds
from swarmshield.swarm.topology import agent_ids


def agent_states(events: list[dict], canary: str, rounds: int) -> list[dict[str, str]]:
    """Index 0 is the state before round 1 (everyone S); index r is the state after round r.
    I: emitted the canary in round r. R: emitted it in an earlier round, quiet in round r.
    S: has not emitted it yet."""
    emitted = emit_rounds(events, canary)
    frames = [{a: "S" for a in agent_ids()}]
    for r in range(1, rounds + 1):
        frame = {}
        for agent in agent_ids():
            seen = emitted.get(agent, set())
            frame[agent] = "I" if r in seen else "R" if seen and min(seen) < r else "S"
        frames.append(frame)
    return frames
