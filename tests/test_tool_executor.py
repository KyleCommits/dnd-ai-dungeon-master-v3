# tests/test_tool_executor.py
"""Smoke tests for TOOL_CALL parse/execute (no live local LLM required).

Tests that pin intent with a generate_intent_json mock must also set
INTENT_BACKEND=llm, or the mock is inert and the real embedding classifier runs.
"""

import os
import sys
from unittest.mock import AsyncMock

import pytest

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)


SAMPLE = """
The goblin lunges!

TOOL_CALL
{"name": "roll_dice_for_character", "arguments": {"dice_string": "1d20+3", "description": "attack"}}
END_TOOL_CALL

TOOL_CALL
{"name": "modify_hp", "arguments": {"character_id": "1", "change": -2, "reason": "test"}}
END_TOOL_CALL

Blood sprays.
"""


def test_extract_multiple_tool_calls():
    from src.tool_executor import extract_tool_calls

    calls = extract_tool_calls(SAMPLE)
    assert len(calls) == 2
    assert calls[0]["name"] == "roll_dice_for_character"
    assert calls[0]["arguments"]["dice_string"] == "1d20+3"
    assert calls[1]["name"] == "modify_hp"


def test_strip_tool_calls_removes_blocks():
    from src.tool_executor import strip_tool_calls

    cleaned = strip_tool_calls(SAMPLE)
    assert "TOOL_CALL" not in cleaned
    assert "END_TOOL_CALL" not in cleaned
    assert "goblin" in cleaned.lower() or "Blood" in cleaned


@pytest.mark.asyncio
async def test_reject_unknown_tool():
    from src.tool_executor import execute_tool_calls

    results = await execute_tool_calls(
        [{"name": "summon_cthulhu", "arguments": {}}],
        allowed_names={"modify_hp", "roll_dice_for_character"},
    )
    assert len(results) == 1
    assert "error" in results[0]
    assert "disallowed" in results[0]["error"] or "unknown" in results[0]["error"]


@pytest.mark.asyncio
async def test_execute_roll_dice():
    from src.tool_executor import execute_tool_calls

    results = await execute_tool_calls(
        [{
            "name": "roll_dice_for_character",
            "arguments": {"dice_string": "1d20+2", "description": "test"},
        }],
        allowed_names={"roll_dice_for_character"},
    )
    assert results[0].get("result", {}).get("success") is True
    assert "total" in results[0]["result"]


@pytest.mark.asyncio
async def test_execute_modify_hp_if_character():
    from src.tool_executor import execute_tool_calls, strip_tool_calls
    from src.database import async_session_scope
    from src.character_models import Character
    from sqlalchemy import select

    character_id = None
    try:
        async with async_session_scope() as db:
            result = await db.execute(select(Character).limit(1))
            character = result.scalar_one_or_none()
            if character:
                character_id = str(character.id)
    except Exception as e:
        pytest.skip(f"Database unavailable: {e}")

    if not character_id:
        pytest.skip("No characters in database")

    results = await execute_tool_calls(
        [{
            "name": "modify_hp",
            "arguments": {"character_id": character_id, "change": -1, "reason": "tool test"},
        }],
        allowed_names={"modify_hp"},
    )
    result = results[0].get("result") or {}
    if result.get("success") is not True:
        err = result.get("error") or results[0].get("error") or result
        if "another operation is in progress" in str(err) or "InterfaceError" in str(err):
            pytest.skip(f"Database busy / connection conflict: {err}")
        pytest.fail(f"modify_hp failed: {err}")

    fake_reply = (
        f'TOOL_CALL\n{{"name": "modify_hp", "arguments": {{"character_id": "{character_id}", "change": -1}}}}\n'
        f"END_TOOL_CALL\nYou take a scratch."
    )
    cleaned = strip_tool_calls(fake_reply)
    assert "TOOL_CALL" not in cleaned
    assert "scratch" in cleaned


@pytest.mark.asyncio
async def test_run_tool_loop_with_mock_generate(monkeypatch):
    from src.tool_executor import run_tool_loop

    # Avoid empty/speak short-circuit; this test covers TOOL_CALL → narrate loop
    monkeypatch.setenv("INTENT_BACKEND", "llm")
    monkeypatch.setattr(
        "src.intent_llm.intent_llm.generate_intent_json",
        AsyncMock(return_value='{"action":"move","confidence":0.9}'),
    )

    calls = {"n": 0}

    async def mock_generate(prompt, max_new_tokens=250, available_functions=None):
        calls["n"] += 1
        if calls["n"] == 1:
            return (
                'TOOL_CALL\n'
                '{"name": "roll_dice_for_character", "arguments": {"dice_string": "1d6", "description": "dmg"}}\n'
                'END_TOOL_CALL\n'
                'A hit lands.'
            )
        # second pass: narration only
        assert "Mechanics:" in prompt or "REAL results" in prompt
        return "The blade connects for real damage."

    funcs = [{
        "name": "roll_dice_for_character",
        "description": "roll",
        "parameters": {"required": ["dice_string"]},
    }]

    out = await run_tool_loop(
        "Player swings a sword.",
        funcs,
        mock_generate,
        max_rounds=2,
        player_message="I walk toward the door",
    )
    assert "TOOL_CALL" not in out
    assert "blade" in out.lower() or "Mechanics" in out
    assert calls["n"] == 2


def test_llm_manager_local_only_no_gemini_primary():
    from src.llm_manager import llm_manager, TOOL_CALL_PROTOCOL

    assert llm_manager.gemini_client is None
    assert "TOOL_CALL" in TOOL_CALL_PROTOCOL
    assert "Never narrate damage" in TOOL_CALL_PROTOCOL
    assert "lookup_spell" in TOOL_CALL_PROTOCOL
    assert "Illegal cast" in TOOL_CALL_PROTOCOL
    built = llm_manager.build_prompt_with_tools(
        "hello",
        [{"name": "modify_hp", "description": "hp", "parameters": {"required": ["character_id"]}}],
    )
    assert "AVAILABLE FUNCTIONS" in built
    assert "modify_hp" in built


def test_extract_trailing_comma_and_fenced_json():
    from src.tool_executor import extract_tool_calls

    trailing = """
TOOL_CALL
{"name": "roll_dice_for_character", "arguments": {"dice_string": "1d20", "description": "x",},}
END_TOOL_CALL
"""
    calls = extract_tool_calls(trailing)
    assert len(calls) == 1
    assert calls[0]["name"] == "roll_dice_for_character"

    fenced = """
TOOL_CALL

```json
{"name": "lookup_spell", "arguments": {"spell_name": "Fireball"}}
```

END_TOOL_CALL
"""
    calls2 = extract_tool_calls(fenced)
    assert len(calls2) == 1
    assert calls2[0]["arguments"]["spell_name"] == "Fireball"


def test_extract_broken_block_returns_empty_and_is_not_silent():
    from src.tool_executor import extract_tool_calls, count_tool_call_markers

    broken = """
TOOL_CALL
{not valid json at all
END_TOOL_CALL
"""
    assert count_tool_call_markers(broken) == 1
    assert extract_tool_calls(broken) == []


def test_prose_claims_mechanics_table():
    from src.mechanics_claims import (
        extract_cast_spell_name,
        player_requests_mechanics,
        prose_claims_mechanics,
    )

    positives = [
        "The goblin takes 8 damage.",
        "You heal 12 hit points.",
        "She rolls a 17 on the check.",
        "Natural 20!",
        "Bob casts Fireball at the pack.",
        "You spend a spell slot.",
        "A burst of magical energy fills the room.",
        "Your swing misses the table yet again.",
    ]
    negatives = [
        "The tavern smells of ale and salt.",
        "Mira smiles and offers you a seat.",
        "You ask the mayor about the docks.",
        "Mira casts a glance your way and smiles.",
        "She casts her eyes toward the door.",
    ]
    for s in positives:
        assert prose_claims_mechanics(s) is True, s
    for s in negatives:
        assert prose_claims_mechanics(s) is False, s

    assert player_requests_mechanics("i cast fireball") is True
    assert player_requests_mechanics("I look around the inn") is False
    assert player_requests_mechanics("i attack a table") is True  # target → chooser path
    assert extract_cast_spell_name("i cast fireball") == "Fireball"
    assert extract_cast_spell_name("i cast fireball instead") == "Fireball"
    assert extract_cast_spell_name("i cast cure wounds again") == "Cure Wounds"


def test_classify_player_intent_tiers():
    from src.mechanics_claims import IntentTier, classify_player_intent

    cases = [
        ("i cast fireball", IntentTier.AUTO, "cast"),
        ("i cast fireball instead", IntentTier.AUTO, "cast"),
        ("I take a long rest", IntentTier.AUTO, "rest"),
        ("roll 1d20", IntentTier.AUTO, "roll"),
        ("i attack a table", IntentTier.AUTO, "attack_clear"),
        ("I attack", IntentTier.CLARIFY, "attack"),
        ("i dash", IntentTier.CLARIFY, "dash"),
        ("i sneak past the guard", IntentTier.CLARIFY, "sneak"),
        ("I look around the inn", IntentTier.NARRATIVE, "roleplay"),
        ("hello Mira", IntentTier.NARRATIVE, "roleplay"),
        ("I attack with my longsword", IntentTier.AUTO, "attack_clear"),
        ("i swing my sword at the table again", IntentTier.AUTO, "attack_clear"),
    ]
    for text, tier, subtype in cases:
        got_tier, got_sub = classify_player_intent(text)
        assert got_tier == tier, f"{text}: expected {tier}, got {got_tier}"
        assert got_sub == subtype, f"{text}: expected subtype {subtype}, got {got_sub}"


@pytest.mark.asyncio
async def test_attack_table_inventory_clarify(monkeypatch):
    """Ambiguous inventory match asks which weapon — DM LLM not used."""
    from src.pending_clarify import clear_pending_clarify, get_pending_clarify
    from src.tool_executor import run_tool_loop, NONBINDING_NOTE

    clear_pending_clarify("player1")
    monkeypatch.setenv("INTENT_BACKEND", "llm")
    monkeypatch.setattr(
        "src.intent_llm.intent_llm.generate_intent_json",
        AsyncMock(
            return_value=(
                '{"action":"attack","target":"table","method":"weapon",'
                '"weapon_hint":"sword","confidence":0.9}'
            )
        ),
    )

    async def mock_generate(prompt, max_new_tokens=250, available_functions=None):
        raise AssertionError("DM LLM should not run")

    async def fake_resolve(**kwargs):
        return {
            "success": False,
            "needs_clarify": True,
            "message": "Which sword — 1) Longsword; 2) Shortsword?",
            "options": ["Longsword", "Shortsword"],
            "target_name": "table",
        }

    monkeypatch.setattr(
        "src.game_actions.game_actions.resolve_player_attack",
        AsyncMock(side_effect=fake_resolve),
    )

    out = await run_tool_loop(
        "ctx",
        [{"name": "resolve_player_attack", "description": "x", "parameters": {}}],
        mock_generate,
        player_message="i attack a table — my sword",
        user_id="player1",
        character_id="4",
    )
    assert "Longsword" in out and "Shortsword" in out
    assert NONBINDING_NOTE not in out
    pending = get_pending_clarify("player1")
    assert pending is not None
    assert pending.options == ["Longsword", "Shortsword"]


@pytest.mark.asyncio
async def test_clarify_followup_sword_resolves_attack(monkeypatch):
    """After clarify, 'i use my sword' must not become tavern banter."""
    from src.pending_clarify import clear_pending_clarify, set_pending_clarify
    from src.tool_executor import run_tool_loop, NONBINDING_NOTE

    clear_pending_clarify("player1")
    set_pending_clarify("player1", "attack", "i attack the table")

    async def mock_generate(prompt, max_new_tokens=250, available_functions=None):
        return "Innkeeper Mira eyes you warily from the bar."

    async def fake_resolve(**kwargs):
        assert "table" in kwargs["target_name"].lower()
        assert "sword" in kwargs["method"].lower()
        return {
            "success": True,
            "hit": True,
            "target_kind": "object",
            "target_name": "table",
            "attack_total": 18,
            "ac": 15,
            "damage": 6,
            "damage_detail": "1d8+3",
            "object_hp_remaining": 4,
            "object_max_hp": 10,
            "destroyed": False,
            "message": "Your blow bites into the table.",
        }

    monkeypatch.setattr(
        "src.game_actions.game_actions.resolve_player_attack",
        AsyncMock(side_effect=fake_resolve),
    )

    out = await run_tool_loop(
        "ctx",
        [{"name": "resolve_player_attack", "description": "x", "parameters": {}}],
        mock_generate,
        max_rounds=2,
        player_message="i use my sword",
        user_id="player1",
        character_id="4",
    )
    assert "Rolling attack for you" in out
    assert "HIT" in out
    assert "Damage: 6" in out
    assert "boarding up the windows" not in out.lower()
    assert NONBINDING_NOTE not in out


@pytest.mark.asyncio
async def test_try_again_uses_last_attack(monkeypatch):
    from src.last_attack import clear_last_attack, set_last_attack
    from src.pending_clarify import clear_pending_clarify
    from src.tool_executor import run_tool_loop

    clear_pending_clarify("player1")
    clear_last_attack("player1")
    set_last_attack("player1", target="table", weapon="Longsword", raw="i attack the table")
    monkeypatch.setenv("INTENT_BACKEND", "llm")
    monkeypatch.setattr(
        "src.intent_llm.intent_llm.generate_intent_json",
        AsyncMock(return_value='{"action":"repeat_last","confidence":0.95}'),
    )

    called = AsyncMock(
        return_value={
            "success": True,
            "hit": False,
            "target_kind": "object",
            "target_name": "table",
            "weapon": "Longsword",
            "attack_total": 10,
            "ac": 15,
            "message": "miss",
        }
    )
    monkeypatch.setattr(
        "src.game_actions.game_actions.resolve_player_attack",
        called,
    )

    async def mock_generate(prompt, max_new_tokens=160, available_functions=None):
        return "SHOULD NOT NARRATE A MISS"

    out = await run_tool_loop(
        "ctx",
        [{"name": "resolve_player_attack", "description": "x", "parameters": {}}],
        mock_generate,
        player_message="i try again",
        user_id="player1",
        character_id="4",
    )
    called.assert_awaited()
    kwargs = called.await_args.kwargs
    assert "table" in kwargs["target_name"].lower()
    assert "longsword" in kwargs["method"].lower()
    assert "Rolling attack" in out
    assert "SHOULD NOT" not in out


def test_and_again_rewrites_from_last_attack():
    from src.last_attack import clear_last_attack, rewrite_from_last_attack, set_last_attack

    clear_last_attack("player1")
    set_last_attack("player1", target="next table", weapon="Longsword")
    for line in ("and again", "once more", "i go again"):
        out = rewrite_from_last_attack("player1", line)
        assert out is not None, line
        assert "next table" in out.lower()
        assert "longsword" in out.lower()


@pytest.mark.asyncio
async def test_and_again_resolves_attack(monkeypatch):
    from src.last_attack import clear_last_attack, set_last_attack
    from src.pending_clarify import clear_pending_clarify
    from src.tool_executor import run_tool_loop

    clear_pending_clarify("player1")
    clear_last_attack("player1")
    set_last_attack("player1", target="next table", weapon="Longsword")
    monkeypatch.setenv("INTENT_BACKEND", "llm")
    monkeypatch.setattr(
        "src.intent_llm.intent_llm.generate_intent_json",
        AsyncMock(return_value='{"action":"repeat_last","confidence":0.95}'),
    )

    called = AsyncMock(
        return_value={
            "success": True,
            "hit": True,
            "target_kind": "object",
            "target_name": "next table",
            "weapon": "Longsword",
            "attack_total": 16,
            "ac": 13,
            "damage": 5,
            "damage_detail": "1d8+3",
            "object_hp_remaining": 3,
            "object_max_hp": 8,
            "destroyed": False,
            "message": "hit",
        }
    )
    monkeypatch.setattr(
        "src.game_actions.game_actions.resolve_player_attack",
        called,
    )

    async def mock_generate(prompt, max_new_tokens=160, available_functions=None):
        return "Mira glares."

    out = await run_tool_loop(
        "ctx",
        [{"name": "resolve_player_attack", "description": "x", "parameters": {}}],
        mock_generate,
        player_message="and again",
        user_id="player1",
        character_id="4",
    )
    called.assert_awaited()
    assert "next table" in called.await_args.kwargs["target_name"].lower()
    assert "Rolling attack" in out


@pytest.mark.asyncio
async def test_use_sword_with_last_target(monkeypatch):
    from src.last_attack import clear_last_attack, set_last_attack
    from src.pending_clarify import clear_pending_clarify
    from src.tool_executor import run_tool_loop

    clear_pending_clarify("player1")
    clear_last_attack("player1")
    set_last_attack("player1", target="table", weapon="unarmed", raw="i attack the table")
    monkeypatch.setenv("INTENT_BACKEND", "llm")
    monkeypatch.setattr(
        "src.intent_llm.intent_llm.generate_intent_json",
        AsyncMock(
            return_value=(
                '{"action":"attack","target":null,"method":"weapon",'
                '"weapon_hint":"sword","confidence":0.9}'
            )
        ),
    )

    called = AsyncMock(
        return_value={
            "success": True,
            "hit": True,
            "target_kind": "object",
            "target_name": "table",
            "weapon": "Longsword",
            "attack_total": 18,
            "ac": 15,
            "damage": 5,
            "damage_detail": "1d8+3",
            "object_hp_remaining": 5,
            "object_max_hp": 10,
            "destroyed": False,
            "message": "hit",
        }
    )
    monkeypatch.setattr(
        "src.game_actions.game_actions.resolve_player_attack",
        called,
    )

    async def mock_generate(prompt, max_new_tokens=160, available_functions=None):
        return "I'm using my longsword."

    out = await run_tool_loop(
        "ctx",
        [{"name": "resolve_player_attack", "description": "x", "parameters": {}}],
        mock_generate,
        player_message="this time i use my sword!",
        user_id="player1",
        character_id="4",
    )
    called.assert_awaited()
    assert "sword" in called.await_args.kwargs["method"].lower()
    assert "Rolling attack" in out
    assert "I'm using my longsword" not in out


@pytest.mark.asyncio
async def test_speak_rejects_invented_mechanics(monkeypatch):
    from src.last_attack import clear_last_attack, set_last_attack
    from src.tool_executor import run_tool_loop

    clear_last_attack("player1")
    set_last_attack("player1", target="table", weapon="Longsword")

    monkeypatch.setenv("INTENT_BACKEND", "llm")
    monkeypatch.setattr(
        "src.intent_llm.intent_llm.generate_intent_json",
        AsyncMock(return_value='{"action":"speak","confidence":0.9}'),
    )

    async def mock_generate(prompt, max_new_tokens=160, available_functions=None):
        return "Your swing misses the table yet again. That's not even close."

    out = await run_tool_loop(
        "ctx",
        [],
        mock_generate,
        player_message="hmm interesting",
        user_id="player1",
    )
    assert "try again" in out.lower() or "longsword" in out.lower()
    assert "not even close" not in out.lower()


@pytest.mark.asyncio
async def test_speak_skips_tool_schema(monkeypatch):
    """Soft RP must not prefill the full TOOL_CALL schema (latency)."""
    from src.tool_executor import run_tool_loop

    monkeypatch.setenv("INTENT_BACKEND", "llm")
    monkeypatch.setattr(
        "src.intent_llm.intent_llm.generate_intent_json",
        AsyncMock(return_value='{"action":"speak","confidence":0.95}'),
    )

    seen = {}

    async def mock_generate(prompt, max_new_tokens=160, available_functions=None):
        seen["funcs"] = available_functions
        seen["prompt"] = prompt
        return "The tavern hums around you."

    out = await run_tool_loop(
        "CONTEXT\n\nFUNCTION CALLING INSTRUCTIONS:\n- emit TOOL_CALL forever\n",
        [{"name": "modify_hp", "description": "hp", "parameters": {"required": []}}],
        mock_generate,
        player_message="hello there",
    )
    assert seen["funcs"] == []
    assert "FUNCTION CALLING INSTRUCTIONS" not in seen["prompt"]
    assert "tavern" in out.lower()


@pytest.mark.asyncio
async def test_force_retry_still_no_tools_adds_note(monkeypatch):
    from src.tool_executor import run_tool_loop, NONBINDING_NOTE

    monkeypatch.setenv("INTENT_BACKEND", "llm")
    monkeypatch.setattr(
        "src.intent_llm.intent_llm.generate_intent_json",
        AsyncMock(return_value='{"action":"rest","confidence":0.9}'),
    )

    async def mock_generate(prompt, max_new_tokens=250, available_functions=None):
        return "You smash through and deal 40 damage."

    funcs = [{
        "name": "roll_dice_for_character",
        "description": "roll",
        "parameters": {"required": ["dice_string"]},
    }]

    out = await run_tool_loop(
        "Player: rest",
        funcs,
        mock_generate,
        max_rounds=2,
        player_message="I take a long rest",
    )
    assert NONBINDING_NOTE in out


@pytest.mark.asyncio
async def test_player_cast_soft_narration_triggers_backend_tools(monkeypatch):
    """Soft tavern prose + 'i cast fireball' must run backend cast tools."""
    from src.tool_executor import run_tool_loop

    monkeypatch.setenv("INTENT_BACKEND", "llm")
    monkeypatch.setattr(
        "src.intent_llm.intent_llm.generate_intent_json",
        AsyncMock(
            return_value=(
                '{"action":"cast","spell_name":"Fireball","confidence":0.95}'
            )
        ),
    )

    async def mock_generate(prompt, max_new_tokens=250, available_functions=None):
        return "The patrons gasp as magical energy crackles by the fireplace."

    async def fake_backend(player_message, character_id, allowed):
        assert "fireball" in player_message.lower()
        assert character_id == "42"
        return [{
            "name": "consume_spell_slot",
            "arguments": {},
            "result": {
                "success": False,
                "message": "Test Fighter (Fighter) cannot cast Fireball.",
            },
        }]

    monkeypatch.setattr("src.tool_executor._backend_cast_tools", fake_backend)

    funcs = [
        {"name": "lookup_spell", "description": "x", "parameters": {}},
        {"name": "consume_spell_slot", "description": "x", "parameters": {}},
    ]
    out = await run_tool_loop(
        "ctx",
        funcs,
        mock_generate,
        max_rounds=2,
        player_message="i cast fireball",
        character_id="42",
    )
    assert "cannot cast" in out.lower()
    assert "No spell effect" in out or "nothing happens" in out.lower()
    assert "cast blocked" in out.lower() or "[mechanics]" in out.lower()
    assert "explodes" not in out.lower()


@pytest.mark.asyncio
async def test_failed_cast_tools_hard_refuse_ignores_bad_narration(monkeypatch):
    """If tools reject the cast, do not keep LLM fireball chaos from chat history."""
    from src.tool_executor import run_tool_loop

    monkeypatch.setenv("INTENT_BACKEND", "llm")
    monkeypatch.setattr(
        "src.intent_llm.intent_llm.generate_intent_json",
        AsyncMock(
            return_value=(
                '{"action":"cast","spell_name":"Fireball","confidence":0.95}'
            )
        ),
    )

    calls = {"n": 0}

    async def mock_generate(prompt, max_new_tokens=250, available_functions=None):
        calls["n"] += 1
        if available_functions:
            return (
                'TOOL_CALL\n'
                '{"name": "consume_spell_slot", "arguments": '
                '{"character_id": "4", "slot_level": 3, "spell_name": "Fireball"}}\n'
                'END_TOOL_CALL\n'
            )
        return "As the second fireball explodes, the tavern erupts into chaos."

    async def fake_execute(tool_calls, allowed_names=None):
        return [{
            "name": "consume_spell_slot",
            "arguments": tool_calls[0]["arguments"],
            "result": {
                "success": False,
                "message": "Test Fighter (Fighter) cannot cast Fireball.",
            },
        }]

    import src.tool_executor as te
    original = te.execute_tool_calls
    te.execute_tool_calls = fake_execute
    try:
        out = await run_tool_loop(
            "ctx with prior fireball chat",
            [{"name": "consume_spell_slot", "description": "x", "parameters": {}}],
            mock_generate,
            max_rounds=2,
            player_message="i cast fireball",
            character_id="4",
        )
    finally:
        te.execute_tool_calls = original

    assert "cannot cast" in out.lower()
    assert "second fireball" not in out.lower()
    assert "explodes" not in out.lower()
