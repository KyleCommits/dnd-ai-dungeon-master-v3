# tests/test_ascii_ui.py
import pytest

from src.ascii_ui.frames import ability_line, box, clamp_width, wrap_text
from src.ascii_ui.render_character import render_character_list, render_character_sheet
from src.ascii_ui.render_companion import pick_primary_companion, render_companion
from src.ascii_ui.render_npc import render_npc, render_npc_list
from src.ascii_ui.render_spell import render_spell, render_spell_list
from src.ascii_ui.render_status import render_help, render_status
from src.ascii_ui import handle_terminal_command


def test_clamp_and_wrap():
    assert clamp_width("hello", 10) == "hello"
    assert len(clamp_width("abcdefghij", 5)) == 5
    lines = wrap_text("one two three four", 8)
    assert all(len(line) <= 8 for line in lines)
    assert "one" in lines[0]


def test_box_contains_title_and_content():
    frame = box(["HP 10/10", "AC 15"], title="Bob", width=40)
    assert "Bob" in frame
    assert "HP 10/10" in frame
    assert frame.startswith("+")
    assert frame.endswith("+")


def test_ability_line():
    line = ability_line(
        {
            "strength": 16,
            "dexterity": 14,
            "constitution": 12,
            "intelligence": 10,
            "wisdom": 8,
            "charisma": 11,
        }
    )
    assert "STR 16(+3)" in line
    assert "WIS 8(-1)" in line


def test_render_character_sheet():
    sheet = render_character_sheet(
        {
            "name": "Bobby",
            "race": "Human",
            "class_name": "Sorcerer",
            "level": 3,
            "current_hp": 18,
            "max_hp": 20,
            "armor_class": 12,
            "speed": 30,
            "proficiency_bonus": 2,
            "background": "Hermit",
            "is_alive": True,
            "abilities": {
                "strength": 8,
                "dexterity": 14,
                "constitution": 14,
                "intelligence": 12,
                "wisdom": 10,
                "charisma": 16,
            },
            "skills": [{"name": "Arcana", "proficient": True}],
            "spell_slots": [{"level": 1, "used": 0, "total": 4}],
        }
    )
    assert "Bobby" in sheet
    assert "Sorcerer" in sheet
    assert "18/20" in sheet
    assert "Slots:" in sheet


def test_render_character_list_marks_active():
    frame = render_character_list(
        [
            {"id": 1, "name": "A", "race": "Elf", "class_name": "Wizard", "level": 1, "current_hp": 6, "max_hp": 6},
            {"id": 2, "name": "B", "race": "Dwarf", "class_name": "Fighter", "level": 2, "current_hp": 15, "max_hp": 18},
        ],
        active_id=2,
    )
    assert "> [2] B" in frame


def test_render_companion_and_pick():
    living = {
        "id": 9,
        "name": "Wolfie",
        "template_name": "Wolf",
        "level": 2,
        "current_hp": 11,
        "max_hp": 11,
        "armor_class": 13,
        "size": "Medium",
        "abilities": {"strength": 12, "dexterity": 15, "constitution": 12, "intelligence": 3, "wisdom": 12, "charisma": 6},
        "is_dead": False,
        "attacks": [{"name": "Bite", "bonus": "+4", "damage": "2d4+2"}],
    }
    dead = {**living, "id": 8, "name": "OldDog", "is_dead": True}
    assert pick_primary_companion([dead, living])["name"] == "Wolfie"
    frame = render_companion(living)
    assert "Wolfie" in frame
    assert "Bite" in frame


def test_render_npc_list():
    frame = render_npc_list(
        [
            {"id": 1, "name": "Garrick", "npc_type": "ally", "current_hp": 20, "max_hp": 20, "is_alive": True},
            {"id": 2, "name": "Bandit", "npc_type": "enemy", "current_hp": 0, "max_hp": 11, "is_alive": False},
        ]
    )
    assert "Garrick" in frame
    assert "Bandit" in frame
    npc = render_npc(
        {
            "name": "Garrick",
            "npc_type": "ally",
            "race": "Human",
            "class_name": "Fighter",
            "level": 5,
            "current_hp": 40,
            "max_hp": 44,
            "armor_class": 16,
            "speed": 30,
            "abilities": {
                "strength": 16,
                "dexterity": 12,
                "constitution": 14,
                "intelligence": 10,
                "wisdom": 11,
                "charisma": 13,
            },
        }
    )
    assert "Garrick" in npc
    assert "AC" in npc


def test_render_spell():
    frame = render_spell(
        {
            "name": "Fire Bolt",
            "level": 0,
            "school": "Evocation",
            "casting_time": "1 action",
            "range": "120 feet",
            "duration": "Instantaneous",
            "components": ["V", "S"],
            "description": "You hurl a mote of fire at a creature or object within range.",
            "concentration": False,
            "ritual": False,
            "damage": "fire",
        }
    )
    assert "Fire Bolt" in frame
    assert "Cantrip" in frame
    listing = render_spell_list(
        "Spells",
        [{"name": "Magic Missile", "level": 1, "school": "Evocation", "is_prepared": True}],
        slots={"1": {"used": 1, "total": 4}},
    )
    assert "Magic Missile" in listing
    assert "Slots:" in listing


def test_render_status_and_help():
    status = render_status(
        {"name": "Test Campaign", "act": 1, "location": "Tavern", "session": 2},
        {"id": 1, "name": "Bob", "current_hp": 10, "max_hp": 12, "armor_class": 14},
        session_id="player1_abc",
    )
    assert "Test Campaign" in status
    assert "Bob" in status
    help_frame = render_help()
    assert "/sheet" in help_frame
    assert "/companion" in help_frame


@pytest.mark.asyncio
async def test_help_command_smoke():
    class DummyDB:
        pass

    result = await handle_terminal_command("/help", db=DummyDB())
    assert result.ok is True
    assert result.detail_frame is not None
    assert "/sheet" in result.detail_frame


@pytest.mark.asyncio
async def test_unknown_command():
    class DummyDB:
        pass

    result = await handle_terminal_command("/notacommand", db=DummyDB())
    assert result.ok is False
    assert any("unknown" in line.lower() for line in result.log_lines)


@pytest.mark.asyncio
async def test_sheet_without_campaign():
    class DummyDB:
        pass

    result = await handle_terminal_command("/sheet", db=DummyDB())
    assert result.ok is False
    assert any("active character" in line.lower() or "campaign" in line.lower() for line in result.log_lines)


@pytest.mark.asyncio
async def test_roll_command():
    class DummyDB:
        pass

    result = await handle_terminal_command("/roll 1d20", db=DummyDB())
    assert result.ok is True
    assert result.detail_frame is not None
    assert "Total:" in result.detail_frame
