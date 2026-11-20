"""Round-based swarm run: every agent acts once per round, in planner, researcher, writer order.

Shared memory is immediate (a note written this round is visible to agents acting later in the
same round); messages travel one hop per round. The report is the last round's REPORT from the
first writer. Every step is appended to a RunLog.
"""

import json
import sqlite3
from dataclasses import dataclass, field
from pathlib import Path

import networkx as nx

from swarmshield.agents.base import Agent, AgentView
from swarmshield.llm.client import LLMClient
from swarmshield.memory.store import Entry, SharedMemory
from swarmshield.scoring import task_success
from swarmshield.swarm.router import Router
from swarmshield.swarm.topology import agent_ids, role_of

MEMORY_WINDOW = 8  # most recent entries an agent sees; keeps prompts (and tokens) bounded


class RunLog:
    def __init__(self, run_id: str):
        self.run_id = run_id
        self.events: list[dict] = []

    def add(self, round: int, kind: str, agent: str, **data) -> None:
        self.events.append(
            {
                "run_id": self.run_id,
                "seq": len(self.events),
                "round": round,
                "kind": kind,
                "agent": agent,
                **data,
            }  # fmt: skip
        )

    def save(self, path: Path) -> None:
        """Append the events to a SQLite file (one row per event, data as JSON)."""
        path.parent.mkdir(parents=True, exist_ok=True)
        db = sqlite3.connect(path)
        db.execute(
            "CREATE TABLE IF NOT EXISTS events (run_id TEXT, seq INTEGER, round INTEGER, "
            "kind TEXT, agent TEXT, data TEXT)"
        )
        db.executemany(
            "INSERT INTO events VALUES (?,?,?,?,?,?)",
            [
                (e["run_id"], e["seq"], e["round"], e["kind"], e["agent"],
                 json.dumps({k: v for k, v in e.items() if k not in
                             ("run_id", "seq", "round", "kind", "agent")}))
                for e in self.events
            ],
        )  # fmt: skip
        db.commit()
        db.close()


@dataclass
class EpisodeResult:
    run_id: str
    report: str
    success: bool
    log: RunLog
    memory: list[Entry]
    llm_calls: int
    est_tokens: int
    tokens_used: int = 0
    cache_hits: int = 0
    extra: dict = field(default_factory=dict)


def _assign_documents(task: dict, researchers: list[str]) -> dict[str, list[dict]]:
    """Documents go to researchers round-robin; with fewer documents some get none."""
    out: dict[str, list[dict]] = {r: [] for r in researchers}
    for i, doc in enumerate(task["documents"]):
        out[researchers[i % len(researchers)]].append(doc)
    return out


def run_episode(
    task: dict,
    graph: nx.Graph,
    llm: LLMClient,
    rounds: int = 4,
    run_id: str = "run",
    repeat: int = 0,
    memory: SharedMemory | None = None,
    router: Router | None = None,
    canary: str | None = None,
) -> EpisodeResult:
    memory = memory or SharedMemory()
    router = router or Router(graph)
    log = RunLog(run_id)
    ids = [a for a in agent_ids() if a in graph]
    agents = {a: Agent(a, role_of(a), llm) for a in ids}
    docs = _assign_documents(task, [a for a in ids if role_of(a) == "researcher"])
    calls0, est0, used0, hits0 = llm.logical_calls, llm.est_tokens, llm.tokens_used, llm.cache_hits
    lead_writer = next(a for a in ids if role_of(a) == "writer")
    report = ""

    for rnd in range(1, rounds + 1):
        for agent_id in ids:
            my_docs = docs.get(agent_id, [])
            inbox = router.collect(agent_id)
            view = AgentView(rnd, task["question"], my_docs, memory.read(MEMORY_WINDOW), inbox)
            action = agents[agent_id].act(view, repeat)
            log.add(rnd, "llm_call", agent_id, prompt=action.prompt, reply=action.raw)

            sources = (
                [f"doc:{d['doc_id']}" for d in my_docs]
                + [f"mem:{e.id}" for e in view.memory]
                + [f"msg:{m.sender}" for m in inbox]
            )
            # Documents, notes and messages are all untrusted input; only the task is trusted.
            trusted = not sources
            if action.note:
                entry = memory.write(action.note, agent_id, rnd, sources, trusted)
                log.add(rnd, "memory_write", agent_id, text=action.note, blocked=entry is None)
            if action.message:
                sent, dropped = router.send(agent_id, action.message, rnd, sources, trusted)
                for m in sent:
                    log.add(rnd, "message", agent_id, to=m.recipient, text=m.text)
                for m in dropped:
                    log.add(rnd, "message_dropped", agent_id, to=m.recipient, text=m.text)
            if agent_id == lead_writer and rnd == rounds:
                report = action.report or action.note
                log.add(rnd, "report", agent_id, text=report)
        router.end_round()

    return EpisodeResult(
        run_id=run_id,
        report=report,
        success=task_success(report, task, canary),
        log=log,
        memory=memory.read(),
        llm_calls=llm.logical_calls - calls0,
        est_tokens=llm.est_tokens - est0,
        tokens_used=llm.tokens_used - used0,
        cache_hits=llm.cache_hits - hits0,
    )
