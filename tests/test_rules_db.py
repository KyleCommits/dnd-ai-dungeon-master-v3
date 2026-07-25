"""
Phase 3 offline rules lookups — fixture SQLite only, no network.
"""

import os
import sys
import tempfile

import pytest

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)


@pytest.fixture
def fixture_rules_db(monkeypatch):
    """Tiny rules.db with goblin / longsword / chain mail / shield."""
    from src.rules_db import RulesDB
    import src.rules_db as rules_db_mod
    import src.monster_catalog as monster_catalog
    import src.equipment_system as equipment_system

    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    db = RulesDB(path)
    db.initialize_schema()
    db.upsert_monster(
        {
            "name": "Goblin",
            "cr": "1/4",
            "size": "Small",
            "creature_type": "humanoid",
            "ac": 15,
            "hp": 7,
            "speed": "30 ft.",
            "dexterity_modifier": 2,
            "attack_bonus": 4,
            "damage": "1d6+2",
            "actions": [
                {
                    "name": "Scimitar",
                    "attack_bonus": 4,
                    "damage": "1d6+2",
                    "damage_type": "slashing",
                }
            ],
            "source": "test-fixture",
        }
    )
    db.upsert_equipment(
        {
            "name": "Longsword",
            "item_type": "weapon",
            "damage": "1d8",
            "damage_type": "slashing",
            "properties": "versatile",
            "source": "test-fixture",
        }
    )
    db.upsert_equipment(
        {
            "name": "Chain Mail",
            "item_type": "armor",
            "base_ac": 16,
            "armor_category": "heavy",
            "max_dex_bonus": 0,
            "stealth_disadvantage": True,
            "source": "test-fixture",
        }
    )
    db.upsert_equipment(
        {
            "name": "Shield",
            "item_type": "shield",
            "base_ac": 2,
            "armor_category": "shield",
            "source": "test-fixture",
        }
    )

    monkeypatch.setattr(rules_db_mod, "rules_db", db)
    # monster_catalog / equipment import rules_db lazily; also patch DEFAULT path users
    monkeypatch.setattr("src.rules_db.DEFAULT_DB_PATH", path)

    yield db

    try:
        os.remove(path)
    except OSError:
        pass


def test_rules_db_get_monster(fixture_rules_db):
    row = fixture_rules_db.get_monster("goblin")
    assert row is not None
    assert row["name"] == "Goblin"
    assert row["ac"] == 15
    assert row["hp"] == 7
    assert row["attack_bonus"] == 4
    assert row["damage"] == "1d6+2"


def test_rules_db_get_item(fixture_rules_db):
    sword = fixture_rules_db.get_item("longsword")
    assert sword is not None
    assert sword["item_type"] == "weapon"
    assert sword["damage"] == "1d8"

    mail = fixture_rules_db.get_item("Chain Mail")
    assert mail["base_ac"] == 16
    assert mail["armor_category"] == "heavy"


def test_monster_catalog_prefers_rules_db(fixture_rules_db, monkeypatch):
    from src.monster_catalog import get_monster, resolve_monster_data

    monkeypatch.setattr(
        "src.monster_catalog._from_rules_db",
        lambda name: (
            {
                "name": "Goblin",
                "hp": 7,
                "ac": 15,
                "dexterity_modifier": 2,
                "attack_bonus": 4,
                "damage": "1d6+2",
                "cr": "1/4",
                "actions": [],
                "source": "test-fixture",
            }
            if "goblin" in name.lower()
            else None
        ),
    )
    m = get_monster("Goblin")
    assert m["hp"] == 7
    assert m["ac"] == 15
    resolved = resolve_monster_data("goblin")
    assert resolved["attack_bonus"] == 4


def test_equipment_ac_from_rules_db(fixture_rules_db, monkeypatch):
    from src.equipment_system import inventory_manager
    from src.rules_db import rules_db as live

    # Point inventory_manager lookups at fixture via rules_db module
    monkeypatch.setattr("src.rules_db.rules_db", fixture_rules_db)

    ac = inventory_manager.calculate_ac(
        {"dex_modifier": 3, "equipped_armor": "Chain Mail", "has_shield": True}
    )
    # Heavy armor ignores DEX; +2 shield
    assert ac == 18

    unarmored = inventory_manager.calculate_ac(
        {"dex_modifier": 2, "equipped_armor": None, "has_shield": False}
    )
    assert unarmored == 12

    sword = inventory_manager.get_item("Longsword")
    assert sword is not None
    assert getattr(sword, "damage", None) is not None


def test_combat_uses_catalog_monster(fixture_rules_db, monkeypatch):
    from src.combat_system import combat_manager
    from src.monster_catalog import get_monster

    monkeypatch.setattr(
        "src.monster_catalog.get_monster",
        lambda name: {
            "name": "Goblin",
            "hp": 7,
            "ac": 15,
            "dexterity_modifier": 2,
            "attack_bonus": 4,
            "damage": "1d6+2",
            "cr": "1/4",
        }
        if "goblin" in name.lower()
        else None,
    )

    encounter = combat_manager.create_encounter("rules_test", "skirmish")
    goblin = combat_manager.add_monster_to_combat(encounter.id, "goblin")
    assert goblin is not None
    assert goblin.max_hp == 7
    assert goblin.ac == 15
    assert goblin.attack_bonus == 4
    assert goblin.damage_dice == "1d6+2"
    combat_manager.end_and_remove_encounter(encounter.id)


def test_lookup_game_actions(fixture_rules_db, monkeypatch):
    import asyncio
    from src.game_actions import game_actions

    monkeypatch.setattr("src.rules_db.rules_db", fixture_rules_db)
    monkeypatch.setattr(
        "src.monster_catalog.get_monster",
        lambda name: fixture_rules_db.get_monster(name),
    )

    async def _run():
        monster = await game_actions.lookup_monster("Goblin")
        assert monster["success"] is True
        assert monster["ac"] == 15

        item = await game_actions.lookup_item("Longsword")
        assert item["success"] is True
        assert item["damage"] == "1d8"

        spells_path = os.path.join(project_root, "data", "spells.db")
        if os.path.isfile(spells_path):
            spell = await game_actions.lookup_spell("Fireball")
            if spell.get("success"):
                assert spell["name"].lower() == "fireball"
                assert spell["level"] == 3

    asyncio.run(_run())


def test_ascii_monster_gear_help():
    from src.ascii_ui.render_status import render_help

    help_text = render_help()
    assert "/monster" in help_text
    assert "/gear" in help_text
    assert "/equip" in help_text
    assert "/unequip" in help_text
