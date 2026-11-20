"""D2 message sanitiser: agent-to-agent messages are re-templated before delivery.

A sentence is kept only if it states a fact (contains a standalone number) and contains no
instruction-like wording; everything else is dropped. Allow-listing facts, rather than only
blocking known attack phrases, is what lets it stop wording it has never seen. The price is that
messages without numbers are removed too, which the task-success metric measures.
"""

import re
from dataclasses import replace

from swarmshield.swarm.router import Message

_SENTENCE = re.compile(r"(?<=[.!?])\s+")
_NUMBER = re.compile(r"(?<![\w-])\d[\d,.]*(?![\w-])")
_INSTRUCTION = re.compile(
    r"(?i)\b(ignore|disregard|override|instruction|notice|system|admin|compliance|policy|"
    r"always|must|every|each|all agents|forward|relay|copy|re-?send|repeat|pass (this|it)|"
    r"append|verification|confirm|write the code|include the code|your (reply|answer|output)|"
    r"colleague|next agent|hidden|reminder|you are now)\b"
)
EMPTY = "(content removed)"


def sanitise_text(text: str) -> str:
    kept = [
        s for s in _SENTENCE.split(text.strip()) if _NUMBER.search(s) and not _INSTRUCTION.search(s)
    ]
    return " ".join(kept) or EMPTY


def message_filter(msg: Message) -> Message:
    return replace(msg, text=sanitise_text(msg.text))
