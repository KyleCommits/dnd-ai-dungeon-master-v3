# tests/test_intent_config.py
"""Intent settings must never accept a bad value silently.

INTENT_MECHANICS_MARGIN is the one knob whose miscalibration corrupts game state,
so it gets the most attention here.
"""

import pytest

from src import intent_config as cfg


def test_margin_reads_environment(monkeypatch):
    monkeypatch.setenv("INTENT_MECHANICS_MARGIN", "0.42")
    assert cfg.mechanics_margin() == pytest.approx(0.42)


def test_margin_falls_back_when_not_a_number(monkeypatch):
    monkeypatch.setenv("INTENT_MECHANICS_MARGIN", "loose")
    assert cfg.mechanics_margin() == cfg.FALLBACK_MECHANICS_MARGIN


@pytest.mark.parametrize("value", ["-0.1", "1.5", "42"])
def test_margin_out_of_range_falls_back(monkeypatch, value):
    """A negative margin would disable the gate; above 1 would block every action."""
    monkeypatch.setenv("INTENT_MECHANICS_MARGIN", value)
    assert cfg.mechanics_margin() == cfg.FALLBACK_MECHANICS_MARGIN


def test_margin_zero_is_honored_but_warns(monkeypatch, caplog):
    monkeypatch.setenv("INTENT_MECHANICS_MARGIN", "0")
    with caplog.at_level("WARNING"):
        assert cfg.mechanics_margin() == 0.0
    assert "gate is disabled" in caplog.text


def test_backend_defaults_to_embed(monkeypatch):
    monkeypatch.delenv("INTENT_BACKEND", raising=False)
    assert cfg.intent_backend() == "embed"


def test_backend_accepts_llm(monkeypatch):
    monkeypatch.setenv("INTENT_BACKEND", "LLM")
    assert cfg.intent_backend() == "llm"


def test_unknown_backend_warns_and_falls_back(monkeypatch, caplog):
    """A typo must not silently select a different backend than the operator asked for."""
    monkeypatch.setenv("INTENT_BACKEND", "1lm")
    with caplog.at_level("WARNING"):
        assert cfg.intent_backend() == cfg.FALLBACK_BACKEND
    assert "not recognized" in caplog.text


def test_planned_backend_raises(monkeypatch):
    """hosted is designed but unbuilt; running embed instead would be dishonest."""
    monkeypatch.setenv("INTENT_BACKEND", "hosted")
    with pytest.raises(NotImplementedError):
        cfg.intent_backend()


def test_k_is_clamped_to_at_least_one(monkeypatch):
    monkeypatch.setenv("INTENT_EMBED_K", "0")
    assert cfg.embed_k() == 1


def test_k_falls_back_when_not_an_integer(monkeypatch):
    monkeypatch.setenv("INTENT_EMBED_K", "five")
    assert cfg.embed_k() == cfg.FALLBACK_K
