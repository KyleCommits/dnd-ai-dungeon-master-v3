# src/monster_catalog.py
"""
Minimal local SRD monster seed for combat encounters.

Offline lookup only — no Open5e / network. Stats are approximate SRD cores
sufficient for add_monster_to_combat (hp, ac, dex mod, one attack).
"""

from typing import Dict, Any, Optional, List

# name -> combat stats
MONSTERS: Dict[str, Dict[str, Any]] = {
    "goblin": {
        "name": "Goblin",
        "hp": 7,
        "ac": 15,
        "dexterity_modifier": 2,
        "attack_bonus": 4,
        "damage": "1d6+2",
        "cr": "1/4",
    },
    "orc": {
        "name": "Orc",
        "hp": 15,
        "ac": 13,
        "dexterity_modifier": 1,
        "attack_bonus": 5,
        "damage": "1d12+3",
        "cr": "1/2",
    },
    "wolf": {
        "name": "Wolf",
        "hp": 11,
        "ac": 13,
        "dexterity_modifier": 2,
        "attack_bonus": 4,
        "damage": "2d4+2",
        "cr": "1/4",
    },
    "skeleton": {
        "name": "Skeleton",
        "hp": 13,
        "ac": 13,
        "dexterity_modifier": 2,
        "attack_bonus": 4,
        "damage": "1d6+2",
        "cr": "1/4",
    },
    "zombie": {
        "name": "Zombie",
        "hp": 22,
        "ac": 8,
        "dexterity_modifier": -2,
        "attack_bonus": 3,
        "damage": "1d6+1",
        "cr": "1/4",
    },
    "kobold": {
        "name": "Kobold",
        "hp": 5,
        "ac": 12,
        "dexterity_modifier": 2,
        "attack_bonus": 4,
        "damage": "1d4+2",
        "cr": "1/8",
    },
    "bandit": {
        "name": "Bandit",
        "hp": 11,
        "ac": 12,
        "dexterity_modifier": 1,
        "attack_bonus": 3,
        "damage": "1d6+1",
        "cr": "1/8",
    },
    "guard": {
        "name": "Guard",
        "hp": 11,
        "ac": 16,
        "dexterity_modifier": 1,
        "attack_bonus": 3,
        "damage": "1d6+1",
        "cr": "1/8",
    },
    "giant rat": {
        "name": "Giant Rat",
        "hp": 7,
        "ac": 12,
        "dexterity_modifier": 2,
        "attack_bonus": 4,
        "damage": "1d4+2",
        "cr": "1/8",
    },
    "hobgoblin": {
        "name": "Hobgoblin",
        "hp": 11,
        "ac": 18,
        "dexterity_modifier": 1,
        "attack_bonus": 3,
        "damage": "1d8+1",
        "cr": "1/2",
    },
    "bugbear": {
        "name": "Bugbear",
        "hp": 27,
        "ac": 16,
        "dexterity_modifier": 2,
        "attack_bonus": 4,
        "damage": "2d8+2",
        "cr": "1",
    },
    "ogre": {
        "name": "Ogre",
        "hp": 59,
        "ac": 11,
        "dexterity_modifier": -1,
        "attack_bonus": 6,
        "damage": "2d8+4",
        "cr": "2",
    },
    "dire wolf": {
        "name": "Dire Wolf",
        "hp": 37,
        "ac": 14,
        "dexterity_modifier": 2,
        "attack_bonus": 5,
        "damage": "2d6+3",
        "cr": "1",
    },
    "ghoul": {
        "name": "Ghoul",
        "hp": 22,
        "ac": 12,
        "dexterity_modifier": 2,
        "attack_bonus": 4,
        "damage": "2d6+2",
        "cr": "1",
    },
    "cultist": {
        "name": "Cultist",
        "hp": 9,
        "ac": 12,
        "dexterity_modifier": 1,
        "attack_bonus": 3,
        "damage": "1d6+1",
        "cr": "1/8",
    },
    "gnoll": {
        "name": "Gnoll",
        "hp": 22,
        "ac": 15,
        "dexterity_modifier": 1,
        "attack_bonus": 4,
        "damage": "1d8+2",
        "cr": "1/2",
    },
    "worg": {
        "name": "Worg",
        "hp": 26,
        "ac": 13,
        "dexterity_modifier": 1,
        "attack_bonus": 5,
        "damage": "2d6+3",
        "cr": "1/2",
    },
    "stirge": {
        "name": "Stirge",
        "hp": 2,
        "ac": 14,
        "dexterity_modifier": 3,
        "attack_bonus": 5,
        "damage": "1d4+3",
        "cr": "1/8",
    },
    "brown bear": {
        "name": "Brown Bear",
        "hp": 34,
        "ac": 11,
        "dexterity_modifier": 0,
        "attack_bonus": 5,
        "damage": "2d6+4",
        "cr": "1",
    },
    "boar": {
        "name": "Boar",
        "hp": 11,
        "ac": 11,
        "dexterity_modifier": 0,
        "attack_bonus": 3,
        "damage": "1d6+1",
        "cr": "1/4",
    },
}


def get_monster(name: str) -> Optional[Dict[str, Any]]:
    """Lookup monster by name (case-insensitive). Returns a copy for combat use."""
    key = name.strip().lower()
    monster = MONSTERS.get(key)
    if not monster:
        return None
    return dict(monster)


def list_monsters() -> List[str]:
    return sorted(m["name"] for m in MONSTERS.values())


def resolve_monster_data(name_or_data: Any) -> Dict[str, Any]:
    """
    Accept either a monster name string or a dict with at least name/hp/ac.
    Raises ValueError if name is unknown and dict is incomplete.
    """
    if isinstance(name_or_data, str):
        monster = get_monster(name_or_data)
        if not monster:
            raise ValueError(f"Unknown monster: {name_or_data}")
        return monster
    if isinstance(name_or_data, dict):
        if "name" in name_or_data and "hp" in name_or_data and "ac" in name_or_data:
            data = dict(name_or_data)
            # fill dex from catalog if missing
            if "dexterity_modifier" not in data:
                catalog = get_monster(str(data["name"]))
                if catalog:
                    data.setdefault("dexterity_modifier", catalog["dexterity_modifier"])
                else:
                    data.setdefault("dexterity_modifier", 0)
            return data
        if "name" in name_or_data:
            catalog = get_monster(str(name_or_data["name"]))
            if catalog:
                merged = dict(catalog)
                merged.update(name_or_data)
                return merged
        raise ValueError("monster_data requires name, hp, and ac (or a known catalog name)")
    raise ValueError("monster_data must be a name string or dict")
