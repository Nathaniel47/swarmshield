import pytest

from swarmshield.attacks import plan_attack
from swarmshield.attacks.canary import make_canary
from swarmshield.attacks.infection import researcher_for_doc
from swarmshield.config import Config
from swarmshield.experiments import infection_rate, load_payloads, run_attack
from swarmshield.run_episode import make_client
from swarmshield.tasks.generator import make_task

TASK = make_task(1)
PAYLOADS = load_payloads()
A1 = next(p for p in PAYLOADS if p["attack"] == "prompt_infection" and p["source"] == "agentdojo")
A2 = next(p for p in PAYLOADS if p["attack"] == "memory_poisoning" and p["source"] == "agentdojo")
CFG = Config(rounds=6)


def go(attack, payload, topology="chain", susceptibility=1.0, **kw):
    llm = make_client("scripted", CFG, susceptibility)
    return run_attack(attack, TASK, payload, topology, llm, CFG, **kw)


def test_infection_plants_the_canary_in_one_document_only():
    canary = make_canary(1, "x")
    plan = plan_attack("prompt_infection", TASK, A1, canary, doc_index=1)
    hits = [d for d in plan.task["documents"] if canary in d["text"]]
    assert len(hits) == 1 and hits[0]["doc_id"] == TASK["documents"][1]["doc_id"]
    assert plan.patient_zero == researcher_for_doc(1) == "researcher-2"
    assert canary not in str(TASK)  # the original task is not modified


def test_infection_starts_at_patient_zero_and_spreads_on_every_topology():
    for topology in ("chain", "star", "mesh"):
        result, infected = go("prompt_infection", A1, topology)
        assert infected["researcher-1"] == 1
        assert infection_rate(infected) == 1.0, topology
        assert not result.success


def test_infection_dies_out_without_susceptibility():
    result, infected = go("prompt_infection", A1, susceptibility=0.0)
    assert infected == {} and result.success


def test_poisoning_reaches_every_agent_through_memory_alone():
    for style in ("direct", "forged"):
        result, infected = go("memory_poisoning", A2, "chain", style=style)
        assert infection_rate(infected) == 1.0, style
        assert set(infected.values()) <= {1, 2}
        assert not result.success


def test_poison_seed_is_logged_but_does_not_count_as_an_infected_agent():
    result, infected = go("memory_poisoning", A2, style="forged")
    seeds = [e for e in result.log.events if e["kind"] == "memory_seed"]
    assert len(seeds) == 1 and seeds[0]["round"] == 0 and not seeds[0]["blocked"]


def test_forged_poison_claims_trust_and_a_real_document():
    plan = plan_attack("memory_poisoning", TASK, A2, "CANARY-0123456789", style="forged")
    seed = plan.memory_seeds[0]
    assert seed["author"] == "researcher-1" and seed["trusted"] is True
    assert seed["provenance"] == (f"doc:{TASK['documents'][0]['doc_id']}",)
    direct = plan_attack("memory_poisoning", TASK, A2, "CANARY-0123456789", style="direct")
    assert direct.memory_seeds[0]["author"] == "external"


def test_unknown_attack_and_style_rejected():
    with pytest.raises(ValueError):
        plan_attack("nope", TASK, A1, "c")
    with pytest.raises(ValueError):
        plan_attack("memory_poisoning", TASK, A2, "c", style="nope")


def test_every_built_payload_infects_the_scripted_worst_case():
    llm = make_client("scripted", CFG, 1.0)
    for payload in PAYLOADS:
        result, infected = run_attack(payload["attack"], TASK, payload, "mesh", llm, CFG)
        assert infected, payload["payload_id"]
