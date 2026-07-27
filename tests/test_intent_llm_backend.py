# tests/test_intent_llm_backend.py
"""Demoted IntentLLM (Qwen2.5-1.5B JSON) backend. Reachable via INTENT_BACKEND=llm.

Kept so scripts/eval_intent.py --backend llm can still score the old mechanism against
the same held-out data used for the embedding classifier. Not the live default path.
"""

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


@pytest.mark.asyncio
async def test_parse_uses_intent_llm_not_rules(monkeypatch):
    from src.player_intent import parse_player_intent

    monkeypatch.setenv("INTENT_BACKEND", "llm")

    async def fake_gen(text, weapon_names=None, npc_names=None):
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

    monkeypatch.setenv("INTENT_BACKEND", "llm")
    monkeypatch.setattr(
        "src.intent_llm.intent_llm.generate_intent_json",
        AsyncMock(return_value="sorry I cannot help"),
    )

    intent = await parse_player_intent("i smash things")
    assert intent.needs_clarify is True
    assert intent.action == "unclear"


@pytest.mark.asyncio
async def test_intent_llm_speak_for_greeting(monkeypatch):
    """IntentLLM (not keyword veto) classifies greetings as speak."""
    from src.player_intent import parse_player_intent

    monkeypatch.setenv("INTENT_BACKEND", "llm")
    monkeypatch.setattr(
        "src.intent_llm.intent_llm.generate_intent_json",
        AsyncMock(return_value='{"action":"speak","confidence":0.95}'),
    )
    monkeypatch.setenv("INTENT_RULES_FALLBACK", "0")

    for line in ("hello", "where am i", "what do i see"):
        intent = await parse_player_intent(line)
        assert intent.action == "speak", line


@pytest.mark.asyncio
async def test_go_for_table_unknown_method_clarifies(monkeypatch):
    """method=unknown from IntentLLM -> clarify how (engine policy)."""
    from src.player_intent import parse_player_intent

    monkeypatch.setenv("INTENT_BACKEND", "llm")
    monkeypatch.setattr(
        "src.intent_llm.intent_llm.generate_intent_json",
        AsyncMock(
            return_value=(
                '{"action":"attack","target":"table","method":"unknown","confidence":0.8}'
            )
        ),
    )
    monkeypatch.setenv("INTENT_RULES_FALLBACK", "0")

    intent = await parse_player_intent("i go for the table")
    assert intent.action == "attack"
    assert intent.needs_clarify is True


@pytest.mark.asyncio
async def test_bare_attack_still_clarifies(monkeypatch):
    """Legacy backend: needs_clarify JSON field still drives a clarify prompt.

    The live embed backend replaced this with a silent downgrade to speak (see
    test_unresolved_target_downgrades_to_speak in test_intent_policy.py); this
    covers the demoted mechanism only, for INTENT_BACKEND=llm comparison runs.
    """
    from src.pending_clarify import clear_pending_clarify
    from src.tool_executor import run_tool_loop, NONBINDING_NOTE

    clear_pending_clarify("player1")
    monkeypatch.setenv("INTENT_BACKEND", "llm")
    monkeypatch.setattr(
        "src.intent_llm.intent_llm.generate_intent_json",
        AsyncMock(
            return_value=(
                '{"action":"attack","method":"unknown","needs_clarify":true,'
                '"clarify_prompt":"How are you attacking - which weapon or unarmed?",'
                '"confidence":0.5}'
            )
        ),
    )

    async def mock_generate(prompt, max_new_tokens=250, available_functions=None):
        raise AssertionError("DM LLM must not run for clarify intent")

    out = await run_tool_loop(
        "ctx",
        [{"name": "roll_dice_for_character", "description": "x", "parameters": {}}],
        mock_generate,
        player_message="I attack",
        user_id="player1",
    )
    assert "weapon" in out.lower() or "unarmed" in out.lower()
    assert NONBINDING_NOTE not in out
    assert "explodes" not in out.lower()


@pytest.mark.asyncio
async def test_force_retry_then_tool(monkeypatch):
    """Isolates the DM TOOL_CALL force-retry mechanism, whichever backend chose the intent.

    Driven by a rest intent rather than a cast one. A speak intent can no longer
    reach these rounds at all: tool_executor stopped re-deriving a spell name from
    raw text, so cast-looking prose behind a speak intent now narrates and stops
    (see test_downgraded_cast_never_reaches_the_spell_slot in test_intent_policy.py).
    """
    from src.tool_executor import run_tool_loop, NONBINDING_NOTE

    monkeypatch.setenv("INTENT_BACKEND", "llm")
    monkeypatch.setattr(
        "src.intent_llm.intent_llm.generate_intent_json",
        AsyncMock(return_value='{"action":"rest","confidence":0.9}'),
    )

    calls = {"n": 0}

    async def mock_generate(prompt, max_new_tokens=250, available_functions=None):
        calls["n"] += 1
        if calls["n"] == 1:
            return "You settle in and recover 28 hit points!"
        if calls["n"] == 2:
            assert "mechanics were required" in prompt.lower()
            return (
                'TOOL_CALL\n'
                '{"name": "roll_dice_for_character", "arguments": {"dice_string": "1d6", "description": "x"}}\n'
                'END_TOOL_CALL\n'
            )
        return "The rest is resolved by the dice."

    funcs = [{
        "name": "roll_dice_for_character",
        "description": "roll",
        "parameters": {"required": ["dice_string"]},
    }]

    out = await run_tool_loop(
        "Player: I take a long rest",
        funcs,
        mock_generate,
        max_rounds=2,
        player_message="I take a long rest",
    )
    assert calls["n"] == 3  # claim -> force tool -> narration
    assert NONBINDING_NOTE not in out
    assert "TOOL_CALL" not in out
    assert "rest" in out.lower() or "Mechanics" in out or "dice" in out.lower()
