import json

from swarmshield.config import Config
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
