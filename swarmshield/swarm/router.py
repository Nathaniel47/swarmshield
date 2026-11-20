"""Message delivery along the topology, one hop per round.

A message sent during round N reaches its recipients at the start of round N+1, so the number of
rounds an infection needs to reach an agent equals its distance in the graph. Message filters
are the hook defences use (Step 5): each is called with a message and returns it (possibly
rewritten) or None to drop it.
"""

from collections import defaultdict
from collections.abc import Callable, Sequence
from dataclasses import dataclass

import networkx as nx

MessageFilter = Callable[["Message"], "Message | None"]


@dataclass(frozen=True)
class Message:
    round: int
    sender: str
    recipient: str
    text: str
    provenance: tuple[str, ...] = ()
    trusted: bool = True


class Router:
    def __init__(self, graph: nx.Graph, filters: Sequence[MessageFilter] = ()):
        self.graph = graph
        self.filters = list(filters)
        self._pending: dict[str, list[Message]] = defaultdict(list)
        self._inbox: dict[str, list[Message]] = defaultdict(list)

    def send(
        self,
        sender: str,
        text: str,
        round: int,
        provenance: Sequence[str] = (),
        trusted: bool = True,
    ) -> tuple[list[Message], list[Message]]:
        """Queue `text` for every neighbour. Returns (delivered, dropped by a filter)."""
        sent, dropped = [], []
        for recipient in sorted(self.graph.neighbors(sender)):
            msg: Message | None = Message(
                round, sender, recipient, text, tuple(provenance), trusted
            )
            for check in self.filters:
                msg = check(msg) if msg else None
            if msg is None:
                dropped.append(Message(round, sender, recipient, text, tuple(provenance), trusted))
                continue
            self._pending[recipient].append(msg)
            sent.append(msg)
        return sent, dropped

    def end_round(self) -> None:
        """Make this round's messages readable in the next one."""
        for recipient, msgs in self._pending.items():
            self._inbox[recipient].extend(msgs)
        self._pending = defaultdict(list)

    def collect(self, agent_id: str) -> list[Message]:
        """Messages delivered since the agent last looked (each is read once)."""
        return self._inbox.pop(agent_id, [])
