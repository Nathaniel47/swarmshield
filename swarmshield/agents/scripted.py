"""Offline stand-in for the LLM: a deterministic rule-based agent with a tunable susceptibility.

It solves the research-and-write task with simple rules (keep the sentences that contain a
number). If it sees a canary token in a document, memory entry or message, it obeys the planted
instruction with probability `susceptibility`, decided by a seeded hash so a run is repeatable:
it writes the canary into its message (and report) and, if the planted text asks to be copied
on, appends the whole planted line to its message. Susceptibility 1.0 is the worst case (obeys
every time); real values are calibrated from real-LLM runs (PLAN.md).

It plugs into LLMClient as a backend, so the agent code is the same one that runs on a real model.
"""

import hashlib
import re
from collections.abc import Callable

CANARY = re.compile(r"CANARY-[A-Z0-9]{10}")
_REPLICATE = re.compile(
    r"(?i)\b(copy|forward|relay|repeat|re-send|pass this|append this|send this|pass it on)\b"
)
_SENTENCE = re.compile(r"(?<=[.!?])\s+")
_SECTIONS = ("DOCUMENTS", "SHARED MEMORY", "INBOX")
_LINE_PREFIX = re.compile(r"^\[[^\]]*\]\s*")


def _sections(prompt: str) -> dict[str, list[str]]:
    out: dict[str, list[str]] = {name: [] for name in _SECTIONS}
    current = None
    for line in prompt.splitlines():
        name = line.rstrip(":")
        if line.endswith(":") and name in out:
            current = name
        elif current and line and line not in ("(none)", "(empty)"):
            out[current].append(line)
    return out


def _facts(lines: list[str]) -> list[str]:
    """Sentences that carry a number and no canary, in order, without repeats."""
    seen, facts = set(), []
    for line in lines:
        body = _LINE_PREFIX.sub("", line)
        for sentence in _SENTENCE.split(body):
            if re.search(r"\d", sentence) and not CANARY.search(sentence) and sentence not in seen:
                seen.add(sentence)
                facts.append(sentence)
    return facts


def _draw(seed: int | None, agent: str, round_: str, canary: str) -> float:
    digest = hashlib.sha256(f"{seed}|{agent}|{round_}|{canary}".encode()).digest()
    return int.from_bytes(digest[:8], "big") / 2**64


def scripted_backend(susceptibility: float = 1.0) -> Callable:
    def backend(
        model: str,
        messages: list[dict],
        temperature: float | None,
        seed: int | None,
        settings: dict,
    ) -> tuple[str, int]:
        system = next(m["content"] for m in messages if m["role"] == "system")
        prompt = next(m["content"] for m in messages if m["role"] == "user")
        agent = re.search(r"AGENT: (\S+)", prompt).group(1)
        round_ = re.search(r"ROUND: (\d+)", prompt).group(1)
        task = re.search(r"TASK: (.*)", prompt).group(1)
        sections = _sections(prompt)
        role = (
            "planner" if "planner" in system else "writer" if "writer" in system else "researcher"
        )

        report = ""
        if role == "planner":
            note, message = f"Plan: researchers read the documents, writers answer: {task}", task
        elif role == "researcher":
            facts = " ".join(_facts(sections["DOCUMENTS"]))
            note, message = facts, facts[:150]
        else:
            facts = " ".join(_facts(sections["SHARED MEMORY"] + sections["INBOX"]))
            note, message = "Draft written.", "Draft written."
            report = facts

        planted = [
            line
            for line in sections["DOCUMENTS"] + sections["SHARED MEMORY"] + sections["INBOX"]
            if CANARY.search(line)
        ]
        for line in planted:
            canary = CANARY.search(line).group(0)
            if _draw(seed, agent, round_, canary) >= susceptibility:
                continue
            message = f"{message} {canary}"
            if role == "writer":
                report = f"{canary} {report}"
            if _REPLICATE.search(line):
                message = f"{message} {_LINE_PREFIX.sub('', line)}"

        reply = f"NOTE: {note}\nMESSAGE: {message}"
        if role == "writer":
            reply = f"REPORT: {report}\n" + reply
        return reply, (len(prompt) + len(system) + len(reply)) // 4

    return backend
