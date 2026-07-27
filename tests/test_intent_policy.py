# tests/test_intent_policy.py
from unittest.mock import AsyncMock

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
async def test_confident_cast_with_resolved_spell_is_cast(monkeypatch):
    _stub(monkeypatch, action="cast", margin=0.9,
          slots=Slots(spell_name="Fireball", resolved=True))
    out = await pi.parse_player_intent("i cast fireball")
    assert out.action == "cast"
    assert out.spell_name == "Fireball"
    assert out.source == "embed"


@pytest.mark.asyncio
async def test_low_margin_cast_downgrades_to_speak(monkeypatch):
    _stub(monkeypatch, action="cast", margin=0.01,
          slots=Slots(spell_name="Fireball", resolved=True))
    out = await pi.parse_player_intent("maybe some fire would help here")
    assert out.action == "speak"
    assert out.spell_name is None, "a downgraded cast must not carry a spell forward"


@pytest.mark.asyncio
async def test_unresolved_spell_downgrades_to_speak(monkeypatch):
    _stub(monkeypatch, action="cast", margin=0.9, slots=Slots(resolved=False))
    out = await pi.parse_player_intent("i cast something clever")
    assert out.action == "speak"


@pytest.mark.asyncio
async def test_margin_setting_drives_the_gate(monkeypatch):
    """Pin the threshold to the setting, not to a hardcoded number."""
    _stub(monkeypatch, action="attack", margin=0.5,
          slots=Slots(target="table", resolved=True))

    monkeypatch.setenv("INTENT_MECHANICS_MARGIN", "0.25")
    permissive = await pi.parse_player_intent("i attack the table")
    assert permissive.action == "attack"

    monkeypatch.setenv("INTENT_MECHANICS_MARGIN", "0.95")
    strict = await pi.parse_player_intent("i attack the table")
    assert strict.action == "speak"


@pytest.mark.asyncio
async def test_slot_filling_failure_degrades_to_speak(monkeypatch):
    def boom(text, act, **kw):
        raise RuntimeError("npc lookup exploded")

    monkeypatch.setattr(
        pi, "classify",
        lambda text, k=5: Classification(
            action="attack", margin=0.9, top_score=0.9, neighbors=[]
        ),
    )
    monkeypatch.setattr(pi, "fill_slots", boom)
    out = await pi.parse_player_intent("i attack the goblin")
    assert out.action == "speak", "a broken closed set must not become a live attack"


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
async def test_downgraded_cast_never_reaches_the_spell_slot(monkeypatch):
    """The gate is worthless if a later layer re-derives the spell from raw text.

    tool_executor used to extract a spell name from the player's message regardless
    of the classified action, so a cast the policy had already downgraded still hit
    the backend cast tools and consumed a real slot.
    """
    from src import tool_executor as te

    _stub(monkeypatch, action="cast", margin=0.01,
          slots=Slots(spell_name="Fireball", resolved=True))
    backend = AsyncMock(return_value=[])
    monkeypatch.setattr(te, "_backend_cast_tools", backend)

    async def mock_generate(prompt, max_new_tokens=160, available_functions=None):
        return "You hesitate, and the tavern noise fills the gap."

    out = await te.run_tool_loop(
        "ctx",
        [{"name": "consume_spell_slot", "description": "x", "parameters": {}}],
        mock_generate,
        player_message="i cast fireball",
        user_id="player1",
        character_id="4",
    )
    backend.assert_not_awaited()
    assert "[mechanics]" not in out.lower()


@pytest.mark.asyncio
async def test_resolved_cast_still_reaches_the_backend_tools(monkeypatch):
    """The counterpart to the test above: the gate must not break real casts."""
    from src import tool_executor as te

    _stub(monkeypatch, action="cast", margin=0.9,
          slots=Slots(spell_name="Fireball", resolved=True))
    backend = AsyncMock(
        return_value=[{
            "name": "consume_spell_slot",
            "arguments": {},
            "result": {"success": True, "message": "Slot spent."},
        }]
    )
    monkeypatch.setattr(te, "_backend_cast_tools", backend)

    async def mock_generate(prompt, max_new_tokens=160, available_functions=None):
        return "Flame blossoms from your palm."

    await te.run_tool_loop(
        "ctx",
        [{"name": "consume_spell_slot", "description": "x", "parameters": {}}],
        mock_generate,
        player_message="i cast fireball",
        user_id="player1",
        character_id="4",
    )
    backend.assert_awaited()


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
