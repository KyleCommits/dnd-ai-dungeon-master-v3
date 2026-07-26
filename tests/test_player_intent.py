# tests/test_player_intent.py
"""Small IntentLLM primary path + engine resolve (mocked model; no live download)."""

import os
import sys
from unittest.mock import AsyncMock

import pytest

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)


def test_intent_from_rules_helper_still_works():
    """Debug/pending helper — not the live primary path."""
    from src.player_intent import intent_from_rules

    intent = intent_from_rules("i punch the table")
    assert intent.action == "attack"
    assert intent.method == "unarmed"


@pytest.mark.asyncio
async def test_bare_attack_keeps_model_method(monkeypatch):
    """IntentLLM owns method; no English cue list rewrites unarmed → None."""
    from src.player_intent import parse_player_intent

    monkeypatch.setattr(
        "src.intent_llm.intent_llm.generate_intent_json",
        AsyncMock(
            return_value=(
                '{"action":"attack","target":"table","method":null,"confidence":0.95}'
            )
        ),
    )
    monkeypatch.setenv("INTENT_RULES_FALLBACK", "0")

    intent = await parse_player_intent("i attack the table again!")
    assert intent.action == "attack"
    assert intent.target == "table"
    assert intent.method is None
    assert intent.needs_clarify is False


def test_unknown_target_not_scene_object():
    from src.target_resolve import resolve_attack_target

    ref = resolve_attack_target("you")
    assert ref.kind == "unknown"
    ref2 = resolve_attack_target("table")
    assert ref2.kind == "object"
    assert ref2.name == "table"


@pytest.mark.asyncio
async def test_pronoun_attack_target_clarifies(monkeypatch):
    """Bad IntentLLM attack@you is stopped by world target resolve, not verb lists."""
    from src.intent_resolver import resolve_intent
    from src.player_intent import PlayerIntent

    outcome = await resolve_intent(
        PlayerIntent(
            action="attack",
            target="you",
            method="weapon",
            weapon_hint="Longsword",
            confidence=0.9,
            raw="night with you",
        ),
        character_id="4",
        allowed={"resolve_player_attack"},
        user_id="player1",
    )
    assert outcome.handled
    assert "who or what" in outcome.reply.lower()


@pytest.mark.asyncio
async def test_repeat_last_action_parsed(monkeypatch):
    from src.player_intent import parse_player_intent

    monkeypatch.setattr(
        "src.intent_llm.intent_llm.generate_intent_json",
        AsyncMock(return_value='{"action":"repeat_last","confidence":0.95}'),
    )
    monkeypatch.setenv("INTENT_RULES_FALLBACK", "0")

    intent = await parse_player_intent("try again")
    assert intent.action == "repeat_last"


@pytest.mark.asyncio
async def test_i_say_is_speech_act_without_intent_llm(monkeypatch):
    from src.player_intent import parse_player_intent

    mocked = AsyncMock(return_value='{"action":"attack","target":"tables","confidence":0.9}')
    monkeypatch.setattr(
        "src.intent_llm.intent_llm.generate_intent_json",
        mocked,
    )
    line = (
        'i say "im sorry that i destroyed your tables. will 1000 gold cover the damage?"'
    )
    intent = await parse_player_intent(line)
    assert intent.action == "speak"
    assert intent.source == "speech_act"
    mocked.assert_not_awaited()


@pytest.mark.asyncio
async def test_hello_speak_mechanics_false_positive_safe_fallback(monkeypatch):
    from src.tool_executor import run_tool_loop

    monkeypatch.setattr(
        "src.intent_llm.intent_llm.generate_intent_json",
        AsyncMock(return_value='{"action":"speak","confidence":0.95}'),
    )

    async def mock_generate(prompt, max_new_tokens=160, available_functions=None):
        return "Mira casts a glance your way and smiles."

    out = await run_tool_loop(
        "ctx",
        [],
        mock_generate,
        player_message="hello!",
        user_id="player1",
    )
    assert "if you are attacking" not in out.lower()
    # Either real narration (cast-glance no longer flagged) or soft fallback
    assert "weapon" not in out.lower() or "longsword" not in out.lower()


@pytest.mark.asyncio
async def test_resolve_intent_punch_unarmed(monkeypatch):
    from src.intent_resolver import resolve_intent
    from src.player_intent import parse_intent_json

    async def fake_resolve(**kwargs):
        assert kwargs["method"] == "unarmed"
        assert kwargs["target_name"] == "table"
        return {
            "success": True,
            "hit": True,
            "target_kind": "object",
            "target_name": "table",
            "weapon": "unarmed",
            "attack_total": 14,
            "ac": 15,
            "damage": 4,
            "damage_detail": "1d4+3",
            "object_hp_remaining": 6,
            "object_max_hp": 10,
            "destroyed": False,
            "message": "Your fist connects.",
        }

    monkeypatch.setattr(
        "src.game_actions.game_actions.resolve_player_attack",
        AsyncMock(side_effect=fake_resolve),
    )

    intent = parse_intent_json(
        '{"action":"attack","target":"table","method":"unarmed","confidence":0.9}',
        "i punch the table",
    )
    out = await resolve_intent(
        intent,
        "4",
        allowed={"resolve_player_attack"},
        user_id="player1",
    )
    assert out.handled
    assert "Rolling attack" in out.reply
    assert "Longsword" not in out.reply


@pytest.mark.asyncio
async def test_resolve_intent_unknown_clarifies(monkeypatch):
    from src.intent_resolver import resolve_intent
    from src.player_intent import parse_intent_json
    from src.pending_clarify import clear_pending_clarify, get_pending_clarify

    clear_pending_clarify("player1")
    intent = parse_intent_json(
        '{"action":"attack","target":"table","method":"unknown","confidence":0.8}',
        "i go for the table",
    )

    called = AsyncMock()
    monkeypatch.setattr(
        "src.game_actions.game_actions.resolve_player_attack",
        called,
    )

    out = await resolve_intent(
        intent, "4", allowed={"resolve_player_attack"}, user_id="player1"
    )
    assert out.handled
    assert "weapon" in out.reply.lower() or "unarmed" in out.reply.lower()
    called.assert_not_called()
    assert get_pending_clarify("player1") is not None


@pytest.mark.asyncio
async def test_resolve_intent_cast_reject(monkeypatch):
    from src.intent_resolver import resolve_intent
    from src.player_intent import parse_intent_json

    async def fake_backend(msg, cid, allowed):
        return [{
            "name": "lookup_spell",
            "arguments": {"spell_name": "Fireball"},
            "result": {"success": True, "level": 3, "name": "Fireball"},
        }, {
            "name": "consume_spell_slot",
            "arguments": {},
            "result": {
                "success": False,
                "message": "Fighter cannot cast Fireball",
            },
        }]

    monkeypatch.setattr(
        "src.tool_executor._backend_cast_tools",
        AsyncMock(side_effect=fake_backend),
    )

    intent = parse_intent_json(
        '{"action":"cast","spell_name":"Fireball","confidence":0.9}',
        "i cast fireball",
    )
    out = await resolve_intent(
        intent,
        "4",
        allowed={"lookup_spell", "consume_spell_slot"},
        user_id="player1",
    )
    assert out.handled
    assert "cast blocked" in out.reply.lower() or "nothing happens" in out.reply.lower()


@pytest.mark.asyncio
async def test_tool_loop_uses_intent_llm(monkeypatch):
    from src.pending_clarify import clear_pending_clarify
    from src.player_intent import parse_intent_json
    from src.tool_executor import run_tool_loop, NONBINDING_NOTE

    clear_pending_clarify("player1")

    async def mock_generate(prompt, max_new_tokens=250, available_functions=None):
        raise AssertionError("DM LLM should not run for punch attack")

    async def fake_parse(text, **kwargs):
        return parse_intent_json(
            '{"action":"attack","target":"table","method":"unarmed","confidence":0.95}',
            text,
        )

    monkeypatch.setattr(
        "src.player_intent.parse_player_intent",
        AsyncMock(side_effect=fake_parse),
    )

    async def fake_resolve(**kwargs):
        assert kwargs["method"] == "unarmed"
        assert kwargs["target_name"] == "table"
        return {
            "success": True,
            "hit": False,
            "target_kind": "object",
            "target_name": "table",
            "weapon": "unarmed",
            "attack_total": 8,
            "ac": 15,
            "message": "You swing your unarmed and glance off the table.",
        }

    monkeypatch.setattr(
        "src.game_actions.game_actions.resolve_player_attack",
        AsyncMock(side_effect=fake_resolve),
    )

    out = await run_tool_loop(
        "ctx",
        [{"name": "resolve_player_attack", "description": "x", "parameters": {}}],
        mock_generate,
        player_message="i punch the table",
        user_id="player1",
        character_id="4",
    )
    assert "Rolling attack for you" in out
    assert "MISS" in out
    assert NONBINDING_NOTE not in out
