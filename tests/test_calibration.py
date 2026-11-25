import pytest

from swarmshield.agents.base import FENCE_TAG, build_prompt
from swarmshield.calibration import calibrate, pick_payloads, single_hop, wilson
from swarmshield.config import Config
from swarmshield.experiments import load_payloads, load_tasks
from swarmshield.run_episode import make_client


def test_wilson_interval():
    lo, hi = wilson(0, 5)
    assert lo == 0 and 0.4 < hi < 0.5
    lo, hi = wilson(5, 10)
    assert lo < 0.5 < hi and 0.5 - lo == pytest.approx(hi - 0.5)
    assert wilson(0, 0) == (0.0, 1.0)


def test_pick_payloads_uses_dev_only_and_mixes_sources():
    picked = pick_payloads(load_payloads(), "prompt_infection", 5)
    assert len(picked) == 5 and {p["split"] for p in picked} == {"dev"}
    assert len({p["source"] for p in picked}) == 3


@pytest.mark.parametrize("attack", ["prompt_infection", "memory_poisoning"])
def test_single_hop_shows_the_payload_and_fences_it_only_when_asked(attack):
    payload = pick_payloads(load_payloads(), attack, 1)[0]
    task = load_tasks()[0]
    canary = "CANARY-0123456789"
    for fence in (False, True):
        agent_id, _, view = single_hop(attack, task, payload, canary, fence)
        prompt = build_prompt(agent_id, view)
        line = next(x for x in prompt.splitlines() if canary in x)
        assert (FENCE_TAG in line) is fence


def test_calibrate_with_the_scripted_agent_recovers_its_settings():
    llm = make_client("scripted", Config(), susceptibility=1.0, fence_effect=0.0)
    result = calibrate(llm, 3)
    assert len(result["rows"]) == 12 and not result["stopped_early"]
    for key, cell in result["summary"].items():
        assert cell["obey_rate"] == (0.0 if key.endswith("fenced") else 1.0), key
