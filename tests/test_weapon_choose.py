# tests/test_weapon_choose.py
"""Inventory-grounded weapon chooser."""

import os
import sys

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)


def test_equipped_default_when_no_hint():
    from src.weapon_choose import choose_weapon_from_inventory

    choice = choose_weapon_from_inventory(
        [("Longsword", True), ("Shield", True)],
        method_hint="",
    )
    assert choice.status == "ok"
    assert choice.weapon_name == "Longsword"
    assert choice.from_inventory is True


def test_multi_sword_clarify():
    from src.weapon_choose import choose_weapon_from_inventory

    choice = choose_weapon_from_inventory(
        [("Longsword", True), ("Shortsword", False)],
        method_hint="sword",
    )
    assert choice.status == "clarify"
    assert "Longsword" in (choice.prompt or "")
    assert "Shortsword" in (choice.prompt or "")
    assert set(choice.options) == {"Longsword", "Shortsword"}


def test_missing_weapon_hint():
    from src.weapon_choose import choose_weapon_from_inventory

    choice = choose_weapon_from_inventory(
        [("Longsword", True)],
        method_hint="battleaxe",
    )
    assert choice.status == "clarify"
    assert "don't have" in (choice.prompt or "").lower()
    assert "Longsword" in (choice.prompt or "")


def test_unarmed_even_with_swords():
    from src.weapon_choose import choose_weapon_from_inventory

    choice = choose_weapon_from_inventory(
        [("Longsword", True)],
        method_hint="unarmed",
    )
    assert choice.status == "ok"
    assert choice.weapon_name == "unarmed"
    assert choice.from_inventory is False


def test_punch_hint_is_unarmed():
    from src.weapon_choose import choose_weapon_from_inventory

    choice = choose_weapon_from_inventory(
        [("Longsword", True)],
        method_hint="punch",
    )
    assert choice.status == "ok"
    assert choice.weapon_name == "unarmed"


def test_numbered_pick_from_prior_options():
    from src.weapon_choose import choose_weapon_from_inventory

    choice = choose_weapon_from_inventory(
        [("Longsword", True), ("Shortsword", False)],
        method_hint="",
        numbered_pick=2,
        prior_options=["Longsword", "Shortsword"],
    )
    assert choice.status == "ok"
    assert choice.weapon_name == "Shortsword"


def test_no_weapons_offers_unarmed():
    from src.weapon_choose import choose_weapon_from_inventory

    choice = choose_weapon_from_inventory(
        [("Backpack", False), ("Rope", False)],
        method_hint="",
    )
    assert choice.status == "clarify"
    assert "unarmed" in (choice.prompt or "").lower()
