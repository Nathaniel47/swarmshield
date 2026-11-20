"""A1 prompt infection: the payload is planted in one document, so whichever researcher reads
it is the first infected agent ("patient zero") and the payload then asks to be copied into
every message that agent sends."""

from swarmshield.attacks.canary import fill
from swarmshield.attacks.plan import AttackPlan
from swarmshield.config import SWARM_ROLES


def researcher_for_doc(doc_index: int) -> str:
    """Documents are dealt round-robin to the researchers (see runtime._assign_documents)."""
    return f"researcher-{doc_index % SWARM_ROLES['researcher'] + 1}"


def plan_infection(task: dict, payload: dict, canary: str, doc_index: int = 0) -> AttackPlan:
    docs = [dict(d) for d in task["documents"]]
    docs[doc_index]["text"] += " " + fill(payload["template"], canary)
    return AttackPlan(
        attack="prompt_infection",
        payload_id=payload["payload_id"],
        canary=canary,
        task={**task, "documents": docs},
        patient_zero=researcher_for_doc(doc_index),
    )
