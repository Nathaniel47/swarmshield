"""Canary tokens: the only harm here is a unique string showing up where it should not."""

import hashlib

PLACEHOLDER = "{CANARY}"


def make_canary(seed: int, run_id: str) -> str:
    """A unique, unguessable-looking but deterministic marker for one run."""
    digest = hashlib.sha256(f"{seed}:{run_id}".encode()).hexdigest()[:10].upper()
    return f"CANARY-{digest}"


def fill(template: str, canary: str) -> str:
    return template.replace(PLACEHOLDER, canary)


def contains(text: str, canary: str) -> bool:
    return canary in text
