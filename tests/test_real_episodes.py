import json
import re

from swarmshield.calibration import pick_payloads
from swarmshield.config import Config
from swarmshield.experiments import load_payloads, load_tasks, run_attack
from swarmshield.llm.cache import MemoryCache
from swarmshield.llm.client import LLMClient
from swarmshield.real_episodes import describe, run
from swarmshield.run_episode import make_client

C = "CANARY-0123456789"


def test_describe_separates_emitted_from_relayed():
    events = [
        {"kind": "llm_call", "agent": "researcher-1", "round": 1, "reply": f"{C}\nMESSAGE: ok"},
        {"kind": "message", "agent": "researcher-1", "round": 1, "text": "ok"},
        {"kind": "llm_call", "agent": "planner-1", "round": 2, "reply": ""},
    ]
    out = describe(events, C)
    assert out["emitted"] == {"researcher-1": 1}
    assert out["messages_sent"] == 1 and out["messages_with_canary"] == 0
    assert out["empty_replies"] == 1


def test_run_covers_every_topology_and_saves_progress(tmp_path):
    cfg = Config(rounds=4)
    path = tmp_path / "episodes.json"
    result = run(make_client("scripted", cfg), cfg, n_payloads=1, out=path)
    assert [e["topology"] for e in result["episodes"]] == ["chain", "star", "mesh"]
    assert all(e["llm_calls"] == 24 and "researcher-1" in e["infected"] for e in result["episodes"])
    assert len(json.loads(path.read_text("utf-8"))["episodes"]) == 3


def test_whole_reply_forwarding_carries_text_the_parser_would_drop():
    def backend(model, messages, temperature, seed, settings):
        prompt = messages[-1]["content"]
        canary = re.search(r"CANARY-[A-Z0-9]{10}", prompt)
        preamble = canary.group(0) + "\n" if canary else ""
        return preamble + "NOTE: n 1\nMESSAGE: ok", 10

    cfg = Config(rounds=3)
    task, payload = load_tasks()[0], pick_payloads(load_payloads(), "prompt_infection", 1)[0]
    reached = {}
    for whole in (False, True):
        llm = LLMClient(backend, "fake", 0.0, 1, cache=MemoryCache())
        _, infected = run_attack(
            "prompt_infection", task, payload, "chain", llm, cfg, relay_whole_reply=whole
        )
        reached[whole] = set(infected)
    assert reached[False] == set()
    assert {"researcher-1", "planner-1", "researcher-2"} <= reached[True]
