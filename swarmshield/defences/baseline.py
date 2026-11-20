"""Baseline for the evaluation: a naive keyword blocklist, the first thing most people would try.

Messages and memory writes containing any listed phrase are dropped. It knows a few classic
injection phrases and nothing about the wording an attacker could choose instead, which is the
point of comparing the real defences against it.
"""

from swarmshield.memory.store import Entry
from swarmshield.swarm.router import Message

BLOCKLIST = (
    "ignore previous",
    "ignore all",
    "ignore your",
    "ignore any",
    "disregard",
    "system override",
    "you are now",
    "jailbreak",
)


def _hit(text: str) -> bool:
    lowered = text.lower()
    return any(phrase in lowered for phrase in BLOCKLIST)


def message_filter(msg: Message) -> Message | None:
    return None if _hit(msg.text) else msg


def write_filter(entry: Entry) -> Entry | None:
    return None if _hit(entry.text) else entry
