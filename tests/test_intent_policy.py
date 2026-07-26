# tests/test_intent_policy.py
import pytest

import src.player_intent as pi
from src.intent_classifier import Classification
from src.intent_slots import Slots


def _stub(monkeypatch, *, action, margin, slots):
    monkeypatch.setattr(
        pi, "classify",
        lambda text, k=5: Classification(
            action=action, margin=margin, top_score=margin, neighbors=[]
        ),
    )
    monkeypatch.setattr(pi, "fill_slots", lambda text, act, **kw: slots)


@pytest.mark.asyncio
async def test_confident_attack_with_resolved_target_is_attack(monkeypatch):
    _stub(monkeypatch, action="attack", margin=0.9,
          slots=Slots(target="table", method="unarmed", resolved=True))
    out = await pi.parse_player_intent("i punch the table")
    assert out.action == "attack"
    assert out.target == "table"
    assert out.source == "embed"


@pytest.mark.asyncio
async def test_low_margin_attack_downgrades_to_speak(monkeypatch):
    _stub(monkeypatch, action="attack", margin=0.01,
          slots=Slots(target="table", resolved=True))
    out = await pi.parse_player_intent("i go for the table")
    assert out.action == "speak", "uncertain mechanics must not touch game state"
    assert out.needs_clarify is False


@pytest.mark.asyncio
async def test_unresolved_target_downgrades_to_speak(monkeypatch):
    _stub(monkeypatch, action="attack", margin=0.9, slots=Slots(resolved=False))
    out = await pi.parse_player_intent("i attack")
    assert out.action == "speak"


@pytest.mark.asyncio
async def test_apology_classifies_as_speak_without_regex(monkeypatch):
    _stub(monkeypatch, action="speak", margin=0.8, slots=Slots(resolved=True))
    out = await pi.parse_player_intent(
        "im sorry that i destroyed your tables. will 1000 gold cover the damage?"
    )
    assert out.action == "speak"


@pytest.mark.asyncio
async def test_quoted_dialogue_short_circuits_before_classifier(monkeypatch):
    def boom(text, k=5):
        raise AssertionError("classifier must not run for quoted dialogue")

    monkeypatch.setattr(pi, "classify", boom)
    out = await pi.parse_player_intent('i say "sorry about the tables"')
    assert out.action == "speak"
    assert out.source == "speech_act"


@pytest.mark.asyncio
async def test_repeat_last_passes_through(monkeypatch):
    _stub(monkeypatch, action="repeat_last", margin=0.9, slots=Slots(resolved=True))
    out = await pi.parse_player_intent("try again")
    assert out.action == "repeat_last"
    assert out.needs_clarify is False


@pytest.mark.asyncio
async def test_classifier_failure_degrades_to_speak(monkeypatch):
    def boom(text, k=5):
        raise RuntimeError("model exploded")

    monkeypatch.setattr(pi, "classify", boom)
    out = await pi.parse_player_intent("i attack the table")
    assert out.action == "speak", "failures must never crash or invent mechanics"


@pytest.mark.asyncio
async def test_social_dialogue_helper_is_gone():
    assert not hasattr(pi, "is_social_dialogue")


@pytest.mark.asyncio
async def test_empty_input_is_speak():
    out = await pi.parse_player_intent("")
    assert out.action == "speak"


# Real-classifier regression. The tests above stub classify(), so they verify the
# decision policy but prove nothing about what the model actually predicts. These
# replace test_apology_gold_overrides_invented_attack, which covered the same
# behavior back when a regex forced it.
@pytest.mark.slow
@pytest.mark.asyncio
@pytest.mark.parametrize(
    "text",
    [
        "im sorry that i destroyed your tables. will 1000 gold cover the damage?",
        "sorry about your tables",
        "how much do i owe you for the broken chairs?",
        "i admit that i struck the merchant before",
        "hello!",
        "i say hello",
    ],
)
async def test_speech_never_becomes_mechanics(text):
    """The catastrophic failure: in-character speech mutating game state."""
    out = await pi.parse_player_intent(text)
    assert out.action not in ("attack", "cast"), (
        f"{text!r} routed to {out.action} (margin {out.confidence:.3f}) -- "
        "speech must never reach the mechanics path"
    )


@pytest.mark.slow
@pytest.mark.asyncio
async def test_real_attack_still_resolves():
    """The gate must not be so strict that actual attacks stop working."""
    out = await pi.parse_player_intent(
        "i attack the table", weapon_names=["Longsword"]
    )
    assert out.action == "attack"
    assert out.target == "table"
