from swarmshield.attacks.infection import plan_infection
from swarmshield.attacks.plan import AttackPlan
from swarmshield.attacks.poisoning import plan_poisoning


def plan_attack(attack: str, task: dict, payload: dict, canary: str, **kwargs) -> AttackPlan:
    if attack == "prompt_infection":
        return plan_infection(task, payload, canary, **kwargs)
    if attack == "memory_poisoning":
        return plan_poisoning(task, payload, canary, **kwargs)
    raise ValueError(f"unknown attack {attack!r}")


__all__ = ["AttackPlan", "plan_attack", "plan_infection", "plan_poisoning"]
