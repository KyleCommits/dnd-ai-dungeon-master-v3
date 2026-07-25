# tests/test_player_intent.py
"""Small IntentLLM primary path + engine resolve (mocked model; no live download)."""

import os
import sys
from unittest.mock import AsyncMock

import pytest

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)


def test_parse_intent_json_punch():
    from src.player_intent import parse_intent_json

    blob = (
        '{"action":"attack","target":"table","method":"unarmed","confidence":0.9}'
    )
    intent = parse_intent_json(blob, "i punch the table")
    assert intent is not None
    assert intent.method == "unarmed"
    assert intent.target == "table"
    assert intent.needs_clarify is False
    assert intent.source == "intent_llm"


def test_parse_intent_json_unknown_clarifies():
    from src.player_intent import parse_intent_json

    blob = (
        '{"action":"attack","target":"table","method":"unknown","confidence":0.7}'
    )
    intent = parse_intent_json(blob, "i go for the table")
    assert intent is not None
    assert intent.method == "unknown"
    assert intent.needs_clarify is True


def test_parse_intent_json_intent_alias():
    from src.player_intent import parse_intent_json

    blob = '{"intent":"attack","target":"door","method":"weapon","weapon_hint":"axe"}'
    intent = parse_intent_json(blob, "axe the door")
    assert intent is not None
    assert intent.action == "attack"
    assert intent.weapon_hint == "axe"


def test_parse_intent_json_fail_closed():
    from src.player_intent import parse_intent_json

    assert parse_intent_json("not json at all", "x") is None


def test_intent_from_rules_helper_still_works():
    """Debug/pending helper — not the live primary path."""
    from src.player_intent import intent_from_rules

    intent = intent_from_rules("i punch the table")
    assert intent.action == "attack"
    assert intent.method == "unarmed"


@pytest.mark.asyncio
async def test_parse_uses_intent_llm_not_rules(monkeypatch):
    from src.player_intent import parse_player_intent

    async def fake_gen(text, weapon_names=None):
        assert "punch" in text.lower()
        return (
            '{"action":"attack","target":"table","method":"unarmed","confidence":0.95}'
        )

    monkeypatch.setattr(
        "src.intent_llm.intent_llm.generate_intent_json",
        AsyncMock(side_effect=fake_gen),
    )
    monkeypatch.setenv("INTENT_RULES_FALLBACK", "0")

    intent = await parse_player_intent("i punch the table")
    assert intent.source == "intent_llm"
    assert intent.method == "unarmed"
    assert intent.target == "table"


@pytest.mark.asyncio
async def test_parse_bad_json_fail_closed(monkeypatch):
    from src.player_intent import parse_player_intent

    monkeypatch.setattr(
        "src.intent_llm.intent_llm.generate_intent_json",
        AsyncMock(return_value="sorry I cannot help"),
    )

    intent = await parse_player_intent("i smash things")
    assert intent.needs_clarify is True
    assert intent.action == "unclear"


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
