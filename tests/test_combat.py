# tests/test_combat.py
"""
Phase 2 combat smoke tests — engine + GameActions, no Gemini.
"""

import os
import sys

import pytest

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)


def test_encounter_lifecycle():
    from src.combat_system import combat_manager

    encounter = combat_manager.create_encounter("test_camp", "ambush")
    assert encounter.is_active is False

    pc = combat_manager.add_character_to_combat(
        encounter.id,
        {
            "id": 99,
            "name": "Hero",
            "max_hp": 20,
            "current_hp": 20,
            "armor_class": 15,
            "dexterity_modifier": 2,
            "strength_modifier": 3,
            "proficiency_bonus": 2,
        },
    )
    assert pc is not None
    assert pc.character_id == 99
    assert pc.attack_bonus == 5  # max(3,2)+2

    goblin = combat_manager.add_monster_to_combat(encounter.id, {"name": "goblin"})
    assert goblin is not None
    assert goblin.attack_bonus == 4
    assert goblin.damage_dice == "1d6+2"

    begin = combat_manager.begin_combat(encounter.id)
    assert begin["success"] is True
    assert encounter.is_active is True
    assert len(encounter.initiative_order) == 2

    encounter.next_turn()
    status = combat_manager.get_combat_status(encounter.id)
    assert status["is_active"] is True
    assert len(status["combatants"]) == 2

    end = combat_manager.end_and_remove_encounter(encounter.id)
    assert end["success"] is True
    assert combat_manager.get_encounter(encounter.id) is None


def test_resolve_attack_structure():
    from src.combat_system import combat_manager

    encounter = combat_manager.create_encounter("test_camp", "skirmish")
    pc = combat_manager.add_character_to_combat(
        encounter.id,
        {
            "id": 7,
            "name": "Bob",
            "max_hp": 30,
            "current_hp": 30,
            "armor_class": 10,  # easy to hit
            "dexterity_modifier": 0,
            "strength_modifier": 2,
            "proficiency_bonus": 2,
        },
    )
    goblin = combat_manager.add_monster_to_combat(encounter.id, "goblin")
    combat_manager.begin_combat(encounter.id)

    # Force high attack bonus so hits are likely; still assert structure
    goblin.attack_bonus = 50
    before = pc.current_hp
    result = combat_manager.resolve_attack(encounter.id, goblin.id, pc.id)
    assert result["success"] is True
    assert result["hit"] is True
    assert result["damage"] > 0
    assert pc.current_hp < before
    assert result["character_id"] == 7

    # Miss path: AC impossibly high
    pc.ac = 99
    miss = combat_manager.resolve_attack(encounter.id, goblin.id, pc.id)
    assert miss["success"] is True
    assert miss["hit"] is False
    assert miss["damage"] == 0

    combat_manager.end_and_remove_encounter(encounter.id)


@pytest.mark.asyncio
async def test_game_actions_mini_fight():
    from src.game_actions import game_actions

    start = await game_actions.start_combat_encounter("camp1", "rats")
    assert start["success"] is True
    eid = start["encounter_id"]

    monster = await game_actions.add_monster_to_encounter(eid, "giant rat")
    assert monster["success"] is True

    # Character add may fail without DB — use engine PC instead via monster-only begin if needed
    from src.combat_system import combat_manager

    pc = combat_manager.add_character_to_combat(
        eid,
        {
            "id": 55,
            "name": "Tester",
            "max_hp": 15,
            "current_hp": 15,
            "armor_class": 12,
            "dexterity_modifier": 1,
            "strength_modifier": 1,
            "proficiency_bonus": 2,
        },
    )
    begin = await game_actions.begin_combat(eid)
    assert begin["success"] is True

    status = await game_actions.get_combat_status(eid)
    assert status["success"] is True

    attack = await game_actions.resolve_attack(eid, monster["combatant_id"], pc.id)
    assert attack["success"] is True
    assert "hit" in attack

    nxt = await game_actions.next_combat_turn(eid)
    assert nxt["success"] is True

    end = await game_actions.end_combat(eid)
    assert end["success"] is True


@pytest.mark.asyncio
async def test_pc_hp_sync_if_db():
    """Sync combat HP to character DB when a character exists."""
    from src.game_actions import game_actions
    from src.database import get_db_session
    from src.character_models import Character
    from sqlalchemy import select

    character_id = None
    try:
        async for db in get_db_session():
            result = await db.execute(select(Character).limit(1))
            character = result.scalar_one_or_none()
            if character:
                character_id = str(character.id)
            break
    except Exception as e:
        pytest.skip(f"Database unavailable: {e}")

    if not character_id:
        pytest.skip("No characters in database")

    sync = await game_actions.sync_character_hp_from_combat(character_id, 5, reason="test sync")
    assert sync["success"] is True
    assert sync["new_hp"] == 5

    status = await game_actions.get_character_status(character_id)
    assert status["success"] is True
    assert status["hp"]["current"] == 5
