from swarmshield.llm.cache import ResponseCache
from swarmshield.llm.client import LLMClient
from swarmshield.llm.meta import update_run_meta


def make_client(tmp_path, calls):
    def backend(model, messages, temperature, seed, settings):
        calls.append(messages)
        return "answer", 10

    return LLMClient(backend, "m", 0.0, 1, cache=ResponseCache(tmp_path))


def test_second_identical_call_hits_cache(tmp_path):
    calls = []
    client = make_client(tmp_path, calls)
    assert client.complete("hi") == "answer"
    assert client.complete("hi") == "answer"
    assert len(calls) == 1
    assert client.cache_hits == 1
    assert client.tokens_used == 10


def test_repeat_index_bypasses_cache(tmp_path):
    calls = []
    client = make_client(tmp_path, calls)
    client.complete("hi", repeat=0)
    client.complete("hi", repeat=1)
    assert len(calls) == 2


def test_run_meta_records_commit(tmp_path):
    meta = update_run_meta(tmp_path / "run_meta.json", model="m", seed=1)
    assert meta["model"] == "m"
    assert "git_commit" in meta
