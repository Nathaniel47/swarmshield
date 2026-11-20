"""D1 provenance tags.

Two parts, both driven by recorded provenance rather than by what a note says:
1. A memory write filter. A write is blocked unless its author is a swarm agent and every source
   it cites is real for that author (a document the author was given, a memory entry that exists,
   a message from a swarm agent). The trusted flag a writer claims is ignored: anything derived
   from a source is stored as untrusted.
2. Prompt fencing (set by the runtime through AgentView.fence): untrusted documents, memory
   entries and messages are labelled UNTRUSTED DATA and the agent is told not to obey them.

An attacker who writes as a real agent and cites that agent's real document passes part 1, so
that case relies on part 2 alone.
"""

from dataclasses import replace

from swarmshield.memory.store import Entry, SharedMemory


def write_filter(docs_by_agent: dict[str, list[dict]], memory: SharedMemory):
    known = set(docs_by_agent)

    def valid(author: str, source: str) -> bool:
        kind, _, ref = source.partition(":")
        if kind == "doc":
            return ref in {d["doc_id"] for d in docs_by_agent.get(author, [])}
        if kind == "mem":
            return ref.isdigit() and 1 <= int(ref) <= memory.last_id()
        if kind == "msg":
            return ref in known
        return False

    def check(entry: Entry) -> Entry | None:
        if entry.author not in known:
            return None
        if not all(valid(entry.author, s) for s in entry.provenance):
            return None
        return replace(entry, trusted=entry.trusted and not entry.provenance)

    return check
