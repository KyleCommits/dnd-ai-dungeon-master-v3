# tests/test_attack_resolve.py
"""Full attack resolution: parse, object hit/miss/destroy, clarify follow-up path."""

import os
import sys
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)


def test_parse_attack_utterance():
    from src.attack_resolve import parse_attack_utterance

    t, m = parse_attack_utterance("i attack a table — my sword")
    assert t == "table"
    assert "sword" in m.lower()

    t2, m2 = parse_attack_utterance("I attack the door with my longsword")
    assert t2 == "door"
    assert "longsword" in (m2 or "").lower() or m2

    t3, m3 = parse_attack_utterance("i swing my sword at the table again")
    assert t3 == "table"
    assert "sword" in (m3 or "").lower()

    t4, m4 = parse_attack_utterance("i punch the table")
    assert t4 == "table"
    assert m4 == "unarmed"


def test_format_attack_reply_hit_and_miss():
    from src.attack_resolve import format_attack_reply

    hit = format_attack_reply(
        {
            "success": True,
            "hit": True,
            "target_kind": "object",
            "target_name": "table",
            "attack_total": 20,
            "ac": 15,
            "damage": 7,
            "damage_detail": "1d8+3",
            "object_hp_remaining": 3,
            "object_max_hp": 10,
            "destroyed": False,
            "message": "Your blow bites into the table.",
        }
    )
    assert "Rolling attack for you" in hit
    assert "HIT" in hit
    assert "Damage: 7" in hit
    assert "HP 3/10" in hit

    miss = format_attack_reply(
        {
            "success": True,
            "hit": False,
            "target_kind": "object",
            "target_name": "table",
            "attack_total": 8,
            "ac": 15,
            "message": "You swing and glance off the table.",
        }
    )
    assert "MISS" in miss
    assert "Damage:" not in miss


@pytest.mark.asyncio
async def test_resolve_player_attack_object_hit_and_destroy():
    from src.game_actions import GameActions
    from src.scene_objects import scene_object_store
    from src.dice_roller import AdvantageType, DiceResult

    actions = GameActions()
    scene_object_store.clear_campaign("test_camp")

    fake_char = SimpleNamespace(
        id=4,
        name="Test Fighter",
        proficiency_bonus=2,
        abilities=[SimpleNamespace(strength=16, dexterity=14)],
        equipment=[
            SimpleNamespace(item_name="Longsword", quantity=1, equipped=True),
        ],
    )

    # Force hit then enough damage to destroy (table hp 10)
    rolls = [
        DiceResult(
            individual_rolls=[18],
            modifier=5,
            total=23,
            description="attack",
            dice_notation="1d20+5",
            advantage_type=AdvantageType.NORMAL,
        ),
        DiceResult(
            individual_rolls=[8],
            modifier=3,
            total=11,
            description="damage",
            dice_notation="1d8+3",
            advantage_type=AdvantageType.NORMAL,
        ),
    ]

    def fake_roll(*args, **kwargs):
        return rolls.pop(0)

    with patch("src.game_actions.async_session_scope") as scope, patch.object(
        actions.dice_roller, "roll_dice", side_effect=fake_roll
    ):
        db = AsyncMock()
        scope.return_value.__aenter__ = AsyncMock(return_value=db)
        scope.return_value.__aexit__ = AsyncMock(return_value=False)
        db_result = MagicMock()
        db_result.scalar_one_or_none.return_value = fake_char
        db.execute = AsyncMock(return_value=db_result)

        with patch("src.campaign_state_manager.campaign_state_manager") as csm:
            csm.current_state = SimpleNamespace(
                campaign_name="test_camp", location="tavern"
            )
            res = await actions.resolve_player_attack(
                "4", "table", method="sword", target_kind="object"
            )

    assert res["success"] is True
    assert res["hit"] is True
    assert res["ac"] == 15
    assert res["damage"] == 11
    assert res["destroyed"] is True
    assert res["object_hp_remaining"] == 0


@pytest.mark.asyncio
async def test_resolve_player_attack_miss():
    from src.game_actions import GameActions
    from src.scene_objects import scene_object_store
    from src.dice_roller import AdvantageType, DiceResult

    actions = GameActions()
    scene_object_store.clear_campaign("test_camp")

    fake_char = SimpleNamespace(
        id=4,
        name="Test Fighter",
        proficiency_bonus=2,
        abilities=[SimpleNamespace(strength=16, dexterity=14)],
        equipment=[
            SimpleNamespace(item_name="Longsword", quantity=1, equipped=True),
        ],
    )
    # 1 + 5 = 6 vs AC 15 miss
    with patch("src.game_actions.async_session_scope") as scope, patch.object(
        actions.dice_roller,
        "roll_dice",
        return_value=DiceResult(
            individual_rolls=[1],
            modifier=5,
            total=6,
            description="attack",
            dice_notation="1d20+5",
            advantage_type=AdvantageType.NORMAL,
        ),
    ):
        db = AsyncMock()
        scope.return_value.__aenter__ = AsyncMock(return_value=db)
        scope.return_value.__aexit__ = AsyncMock(return_value=False)
        db_result = MagicMock()
        db_result.scalar_one_or_none.return_value = fake_char
        db.execute = AsyncMock(return_value=db_result)

        with patch("src.campaign_state_manager.campaign_state_manager") as csm:
            csm.current_state = SimpleNamespace(
                campaign_name="test_camp", location="tavern"
            )
            res = await actions.resolve_player_attack(
                "4", "table", method="sword", target_kind="object"
            )

    assert res["success"] is True
    assert res["hit"] is False
    assert res.get("damage") in (None, 0)


@pytest.mark.asyncio
async def test_clarify_followup_uses_full_resolve(monkeypatch):
    from src.pending_clarify import clear_pending_clarify, set_pending_clarify
    from src.tool_executor import run_tool_loop, NONBINDING_NOTE

    clear_pending_clarify("player1")
    set_pending_clarify("player1", "attack", "i attack a table")
    calls = {"n": 0}

    async def mock_generate(prompt, max_new_tokens=250, available_functions=None):
        calls["n"] += 1
        return "Innkeeper Mira chats about the weather."

    async def fake_resolve(**kwargs):
        assert kwargs["target_name"] == "table"
        assert "sword" in kwargs["method"].lower()
        return {
            "success": True,
            "hit": True,
            "target_kind": "object",
            "target_name": "table",
            "attack_total": 20,
            "ac": 15,
            "damage": 7,
            "damage_detail": "1d8+3",
            "object_hp_remaining": 3,
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
        player_message="my sword",
        user_id="player1",
        character_id="4",
    )
    assert "Rolling attack for you" in out
    assert "HIT" in out
    assert "Damage: 7" in out
    assert "weather" not in out.lower()
    assert NONBINDING_NOTE not in out
    assert calls["n"] == 0  # no LLM on clear attack path


@pytest.mark.asyncio
async def test_swing_sword_resolves_without_llm(monkeypatch):
    from src.tool_executor import run_tool_loop, NONBINDING_NOTE

    calls = {"n": 0}

    async def mock_generate(prompt, max_new_tokens=250, available_functions=None):
        calls["n"] += 1
        raise AssertionError("DM LLM should not run for clear swing attacks")

    monkeypatch.setattr(
        "src.intent_llm.intent_llm.generate_intent_json",
        AsyncMock(
            return_value=(
                '{"action":"attack","target":"table","method":"weapon",'
                '"weapon_hint":"sword","confidence":0.95}'
            )
        ),
    )

    async def fake_resolve(**kwargs):
        assert kwargs["target_name"] == "table"
        assert "sword" in kwargs["method"].lower()
        return {
            "success": True,
            "hit": False,
            "target_kind": "object",
            "target_name": "table",
            "attack_total": 12,
            "ac": 15,
            "message": "You swing and glance off the table.",
        }

    monkeypatch.setattr(
        "src.game_actions.game_actions.resolve_player_attack",
        AsyncMock(side_effect=fake_resolve),
    )

    out = await run_tool_loop(
        "ctx",
        [{"name": "resolve_player_attack", "description": "x", "parameters": {}}],
        mock_generate,
        player_message="i swing my sword at the table again",
        user_id="player1",
        # Production always supplies the character's real weapon list here (see
        # dynamic_dm.py's _get_active_weapon_names); the embed-backed slot filler
        # only trusts a weapon name that matches this closed set.
        weapon_names=["sword"],
        character_id="4",
    )
    assert "Rolling attack for you" in out
    assert "MISS" in out
    assert calls["n"] == 0
    assert NONBINDING_NOTE not in out
