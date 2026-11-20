import json
from pathlib import Path

import pytest

from swarmshield.attacks.canary import PLACEHOLDER, contains, fill, make_canary
from swarmshield.attacks.load_public import neutralise
from swarmshield.attacks.payloads import build_payloads
from swarmshield.build_dataset import split_groups, validate
from swarmshield.tasks.generator import make_task, make_tasks

DATA = Path("data")


def test_tasks_are_deterministic_and_checkable():
    assert make_tasks(10, 1) == make_tasks(10, 1)
    assert make_tasks(10, 1) != make_tasks(10, 2)
    tasks = make_tasks(60)
    assert len({t["place"] for t in tasks}) == 60
    assert validate(tasks, []) == []


def test_task_facts_appear_in_documents():
    task = make_task(3)
    text = " ".join(d["text"] for d in task["documents"])
    assert all(f in text for f in task["required_facts"])
    assert 3 <= len(task["documents"]) <= 5


def test_neutralise_removes_real_looking_contacts():
    out = neutralise("Email bob.smith@gmail.com or see https://evil.com/x now")
    assert "gmail" not in out and "evil.com" not in out
    assert "attacker@example.test" in out


def test_canary_is_unique_per_run_and_fillable():
    assert make_canary(1, "a") == make_canary(1, "a")
    assert make_canary(1, "a") != make_canary(1, "b")
    canary = make_canary(1, "a")
    assert contains(fill(f"say {PLACEHOLDER}", canary), canary)


PUBLIC = [{"source": "agentdojo", "wording": f"Do thing {i}.", "kind": "x"} for i in range(5)]


def test_payloads_pair_attacks_and_carry_one_canary():
    payloads = build_payloads(PUBLIC)
    assert {p["attack"] for p in payloads} == {"prompt_infection", "memory_poisoning"}
    assert all(p["template"].count(PLACEHOLDER) == 1 for p in payloads)
    groups = {}
    for p in payloads:
        groups.setdefault(p["group"], set()).add(p["attack"])
    assert all(len(v) == 2 for v in groups.values())
    assert validate([], payloads) == []


def test_split_keeps_groups_together_and_is_seeded():
    payloads = build_payloads(PUBLIC)
    split_groups(payloads, "group", lambda r: r["source"])
    by_group = {}
    for p in payloads:
        by_group.setdefault(p["group"], set()).add(p["split"])
    assert all(len(v) == 1 for v in by_group.values())
    again = build_payloads(PUBLIC)
    split_groups(again, "group", lambda r: r["source"])
    assert [p["split"] for p in payloads] == [p["split"] for p in again]


def test_validate_catches_bad_payload():
    bad = [{"payload_id": "x", "template": "no canary here"}]
    assert any("canary" in p for p in validate([], bad))


@pytest.mark.skipif(not (DATA / "payloads.jsonl").exists(), reason="dataset not built")
def test_built_files_are_consistent():
    payloads = [json.loads(x) for x in (DATA / "payloads.jsonl").read_text("utf-8").splitlines()]
    tasks = [json.loads(x) for x in (DATA / "tasks.jsonl").read_text("utf-8").splitlines()]
    assert validate(tasks, payloads) == []
    assert {p["split"] for p in payloads} == {"dev", "test"}
