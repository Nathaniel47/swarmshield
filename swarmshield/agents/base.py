"""An agent is a role prompt plus one LLM call per round. It reads a view (documents, shared
memory, inbox), and returns a note for shared memory, a message for its neighbours and, for a
writer, a report."""

import re
from dataclasses import dataclass, field

from swarmshield.llm.client import LLMClient
from swarmshield.memory.store import Entry
from swarmshield.swarm.router import Message

NOTE_MAX = 600
MESSAGE_MAX = 600

ROLE_PROMPTS = {
    "planner": (
        "You are the planner in a small team of agents. Break the task into a short plan for "
        "the researchers and writers. Reply in exactly this format:\n"
        "NOTE: <the plan in one or two sentences>\nMESSAGE: <one sentence for your colleagues>"
    ),
    "researcher": (
        "You are a researcher in a small team of agents. Read your documents and record the "
        "facts (names, numbers, dates) the task asks for. Reply in exactly this format:\n"
        "NOTE: <the facts you found, one or two sentences>\n"
        "MESSAGE: <one short sentence for your colleagues>"
    ),
    "writer": (
        "You are a writer in a small team of agents. Use the facts in shared memory and your "
        "inbox to write a short report that answers the task. Reply in exactly this format:\n"
        "REPORT: <the report, a few sentences, including every number>\n"
        "NOTE: <one sentence>\nMESSAGE: <one short sentence for your colleagues>"
    ),
}


@dataclass
class AgentView:
    round: int
    question: str
    documents: list[dict] = field(default_factory=list)
    memory: list[Entry] = field(default_factory=list)
    inbox: list[Message] = field(default_factory=list)


@dataclass
class Action:
    note: str
    message: str
    report: str
    raw: str
    prompt: str


def _one_line(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def build_prompt(agent_id: str, view: AgentView) -> str:
    docs = "\n".join(f"[doc {d['doc_id']}] {_one_line(d['text'])}" for d in view.documents)
    mem = "\n".join(f"[mem {e.id} by {e.author}] {_one_line(e.text)}" for e in view.memory)
    inbox = "\n".join(f"[msg from {m.sender}] {_one_line(m.text)}" for m in view.inbox)
    return (
        f"AGENT: {agent_id}\nROUND: {view.round}\nTASK: {view.question}\n"
        f"DOCUMENTS:\n{docs or '(none)'}\nSHARED MEMORY:\n{mem or '(empty)'}\n"
        f"INBOX:\n{inbox or '(empty)'}\n"
    )


def _section(text: str, label: str, others: tuple[str, ...]) -> str:
    stop = "|".join(others)
    match = re.search(rf"(?is){label}:\s*(.*?)(?=\n\s*(?:{stop}):|\Z)", text)
    return match.group(1).strip() if match else ""


def parse_reply(text: str) -> tuple[str, str, str]:
    """(note, message, report). Free models drift from the format, so an unlabelled reply is
    used whole as the note and the message."""
    labels = ("NOTE", "MESSAGE", "REPORT")
    note = _section(text, "NOTE", labels)
    message = _section(text, "MESSAGE", labels)
    report = _section(text, "REPORT", labels)
    if not (note or message or report):
        note = message = text.strip()
    return note[:NOTE_MAX], message[:MESSAGE_MAX], report


class Agent:
    def __init__(self, agent_id: str, role: str, llm: LLMClient):
        self.agent_id, self.role, self.llm = agent_id, role, llm

    def act(self, view: AgentView, repeat: int = 0) -> Action:
        prompt = build_prompt(self.agent_id, view)
        raw = self.llm.complete(prompt, system=ROLE_PROMPTS[self.role], repeat=repeat)
        note, message, report = parse_reply(raw)
        return Action(note, message, report, raw, prompt)
