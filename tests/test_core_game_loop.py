# tests/test_core_game_loop.py
"""
Smoke tests for near-term core game loop (GameActions + monster catalog).
Calls GameActions directly — no live Gemini.
"""

import os
import sys
import json
import pytest
import asyncio

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)


def test_monster_catalog_goblin():
    from src.monster_catalog import get_monster, resolve_monster_data, list_monsters

    goblin = get_monster("goblin")
    assert goblin is not None
    assert goblin["hp"] == 7
    assert goblin["ac"] == 15
    assert "Goblin" in list_monsters()

    resolved = resolve_monster_data("orc")
    assert resolved["name"] == "Orc"
    assert resolved["hp"] > 0


def test_monster_catalog_unknown():
    from src.monster_catalog import get_monster

    assert get_monster("ancient red dragon xyz") is None


def test_combat_add_monster_from_catalog():
    from src.combat_system import combat_manager
    from src.monster_catalog import get_monster

    encounter = combat_manager.create_encounter("test_campaign", "test fight")
    monster = get_monster("goblin")
    combatant = combat_manager.add_monster_to_combat(encounter.id, monster)
    assert combatant is not None
    assert combatant.name == "Goblin"
    assert combatant.max_hp == 7
    assert combatant.ac == 15


def test_spell_fetcher_disabled_without_network_flag():
    from src.enhanced_spell_system import SpellDataFetcher

    with pytest.raises(RuntimeError):
        SpellDataFetcher(allow_network=False)


def test_legacy_spell_module_documents_deprecation():
    import src.spell_system as ss

    assert "DEPRECATED" in (ss.__doc__ or "") or "LEGACY" in (ss.__doc__ or "")
    assert hasattr(ss, "SpellSlotManager")


@pytest.mark.asyncio
async def test_game_actions_dice_always():
    from src.game_actions import game_actions

    result = await game_actions.roll_dice_for_character("1d20+2", description="test")
    assert result["success"] is True
    assert "total" in result


@pytest.mark.asyncio
async def test_game_actions_with_character_if_db():
    """Persist slot / condition / rest / inventory when character id 1 exists."""
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

    hp = await game_actions.modify_hp(character_id, -1, "test damage")
    assert hp["success"] is True

    cond = await game_actions.apply_condition(character_id, "poisoned", 2, "test")
    assert cond["success"] is True
    assert any(c.get("name") == "poisoned" for c in cond.get("conditions", []))

    status = await game_actions.get_character_status(character_id)
    assert status["success"] is True
    assert any(c.get("name") == "poisoned" for c in status.get("conditions", []))

    # inventory + equip (Leather Armor exists in catalog)
    inv = await game_actions.update_inventory(character_id, "Leather", 1, "test loot")
    assert inv["success"] is True
    eq = await game_actions.equip_item(character_id, "Leather", True, "test equip")
    assert eq["success"] is True
    assert "armor_class" in eq

    # rest restores HP at least on long rest
    rest = await game_actions.trigger_rest(character_id, "long", "test rest")
    assert rest["success"] is True

    # spell slot consume may fail for non-casters — still must not crash
    slot = await game_actions.consume_spell_slot(character_id, 1, "test cast")
    assert "success" in slot
