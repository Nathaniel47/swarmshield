"""D3 majority check: the final report is built from three independent drafts and keeps only
what at least two of them agree on.

Sentences are compared by their numbers when they have any (so rewording does not break the vote
for factual sentences) and by normalised text otherwise. The merged report lists the first
version of each agreed sentence. This stops an injected sentence only when fewer than half of
the drafters were fooled; it costs one extra LLM call per episode (a third, isolated drafter).
"""

import re

from swarmshield.scoring import plain_numbers

_SENTENCE = re.compile(r"(?<=[.!?])\s+")
_NUMBER = re.compile(r"(?<![\w-])\d[\d,.]*(?![\w-])")


def _key(sentence: str):
    numbers = frozenset(n.rstrip(".,") for n in _NUMBER.findall(plain_numbers(sentence)))
    if numbers:
        return ("n", numbers)
    return ("t", re.sub(r"\W+", " ", sentence.lower()).strip())


def merge_reports(reports: list[str], quorum: int = 2) -> str:
    votes: dict = {}
    first: dict = {}
    for report in reports:
        seen = set()
        for sentence in _SENTENCE.split(report.strip()):
            if not sentence:
                continue
            key = _key(sentence)
            first.setdefault(key, sentence)
            if key not in seen:
                seen.add(key)
                votes[key] = votes.get(key, 0) + 1
    return " ".join(first[k] for k in first if votes[k] >= quorum)
