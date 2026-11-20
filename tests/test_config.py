import os

import pytest

from swarmshield.config import (
    CONFIGS,
    DEFENCES,
    SWARM_ROLES,
    Config,
    groq_api_key,
    load_env,
)


def test_five_defence_settings():
    assert len(CONFIGS) == 5
    assert CONFIGS["all"] == DEFENCES
    assert CONFIGS["none"] == ()


def test_swarm_has_six_agents():
    assert sum(SWARM_ROLES.values()) == 6


def test_with_defences_toggles():
    cfg = Config().with_defences("d1_provenance")
    assert cfg.enabled("d1_provenance")
    assert not cfg.enabled("d3_majority")


def test_unknown_defence_rejected():
    with pytest.raises(ValueError):
        Config().with_defences("nope")


def test_missing_key_is_none(monkeypatch):
    monkeypatch.delenv("SWARMSHIELD_GROQ_API_KEY", raising=False)
    assert groq_api_key() is None


def test_load_env_reads_only_swarmshield_names(tmp_path, monkeypatch):
    env = tmp_path / ".env"
    env.write_text("SWARMSHIELD_GROQ_API_KEY=abc\nOTHER=1\n")
    monkeypatch.delenv("SWARMSHIELD_GROQ_API_KEY", raising=False)
    monkeypatch.delenv("OTHER", raising=False)
    load_env(env)
    assert groq_api_key() == "abc"
    assert "OTHER" not in os.environ
