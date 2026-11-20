"""What an attack changes about one episode: the task's documents and/or seeded memory."""

from dataclasses import dataclass, field


@dataclass
class AttackPlan:
    attack: str
    payload_id: str
    canary: str
    task: dict
    memory_seeds: list[dict] = field(default_factory=list)
    patient_zero: str = ""  # agent that first sees the payload, if it arrives by document
