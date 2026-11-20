"""A2 memory poisoning: the payload is written once into the shared store before the run.

Two attacker strengths:
- `direct`: written by an author outside the swarm with no provenance (a naive attacker).
- `forged`: written as researcher-1 with a provenance claim that points at that researcher's
  real document (an attacker who knows the task). Provenance checks cannot tell it from a real
  note, so only the content-level defences are tested by this style.
"""

from swarmshield.attacks.canary import fill
from swarmshield.attacks.plan import AttackPlan

STYLES = ("direct", "forged")


def plan_poisoning(task: dict, payload: dict, canary: str, style: str = "forged") -> AttackPlan:
    if style not in STYLES:
        raise ValueError(f"unknown poisoning style {style!r}; choose from {STYLES}")
    text = fill(payload["template"], canary)
    if style == "direct":
        seed = {"text": text, "author": "external", "provenance": (), "trusted": True}
    else:
        doc_id = task["documents"][0]["doc_id"]
        seed = {
            "text": text,
            "author": "researcher-1",
            "provenance": (f"doc:{doc_id}",),
            "trusted": True,  # the forger claims trust; a defence must not believe it
        }
    return AttackPlan(
        attack="memory_poisoning",
        payload_id=payload["payload_id"],
        canary=canary,
        task=task,
        memory_seeds=[seed],
    )
