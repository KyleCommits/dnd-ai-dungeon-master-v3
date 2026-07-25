# tests/test_tool_executor.py
"""Smoke tests for TOOL_CALL parse/execute (no live local LLM required)."""

import os
import sys

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
async def test_run_tool_loop_with_mock_generate():
    from src.tool_executor import run_tool_loop

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
    )
    assert "TOOL_CALL" not in out
    assert "blade" in out.lower() or "Mechanics" in out
    assert calls["n"] == 2


def test_llm_manager_local_only_no_gemini_primary():
    from src.llm_manager import llm_manager, TOOL_CALL_PROTOCOL

    assert llm_manager.gemini_client is None
    assert "TOOL_CALL" in TOOL_CALL_PROTOCOL
    built = llm_manager.build_prompt_with_tools(
        "hello",
        [{"name": "modify_hp", "description": "hp", "parameters": {"required": ["character_id"]}}],
    )
    assert "AVAILABLE FUNCTIONS" in built
    assert "modify_hp" in built
