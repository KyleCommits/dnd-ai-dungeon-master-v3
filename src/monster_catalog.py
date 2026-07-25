# src/monster_catalog.py
"""
Monster lookup for combat encounters.

Order: data/rules.db (offline MD/PDF seed) -> in-code MONSTERS fallback.
No network.
"""

from typing import Any, Dict, List, Optional
import logging

logger = logging.getLogger(__name__)

# Minimal offline fallback if rules.db missing / empty
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
    "ogre": {
        "name": "Ogre",
        "hp": 59,
        "ac": 11,
        "dexterity_modifier": -1,
        "attack_bonus": 6,
        "damage": "2d8+4",
        "cr": "2",
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
}


def _from_rules_db(name: str) -> Optional[Dict[str, Any]]:
    try:
        from .rules_db import rules_db

        row = rules_db.get_monster(name)
        if not row:
            return None
        # Normalize combat fields; prefer primary action if present
        actions = row.get("actions") or []
        attack_bonus = int(row.get("attack_bonus") or 0)
        damage = str(row.get("damage") or "1d4")
        if actions:
            primary = actions[0]
            attack_bonus = int(primary.get("attack_bonus", attack_bonus) or attack_bonus)
            damage = str(primary.get("damage") or damage)
        return {
            "name": row["name"],
            "hp": int(row["hp"]),
            "ac": int(row["ac"]),
            "dexterity_modifier": int(row.get("dexterity_modifier") or 0),
            "attack_bonus": attack_bonus,
            "damage": damage,
            "cr": row.get("cr"),
            "size": row.get("size"),
            "creature_type": row.get("creature_type"),
            "speed": row.get("speed"),
            "actions": actions,
            "source": row.get("source"),
        }
    except Exception as e:
        logger.warning("rules.db monster lookup failed: %s", e)
        return None


def get_monster(name: str) -> Optional[Dict[str, Any]]:
    """Lookup monster by name (case-insensitive). Returns a copy for combat use."""
    row = _from_rules_db(name)
    if row:
        return dict(row)

    key = name.strip().lower()
    monster = MONSTERS.get(key)
    if not monster:
        # fuzzy key
        for k, v in MONSTERS.items():
            if key in k or key in v["name"].lower():
                logger.warning("Using in-code monster fallback for %s", v["name"])
                return dict(v)
        return None
    logger.warning("Using in-code monster fallback for %s (not in rules.db)", monster["name"])
    return dict(monster)


def search_monsters(query: str = "", cr: Optional[str] = None, limit: int = 40) -> List[Dict[str, Any]]:
    try:
        from .rules_db import rules_db

        rows = rules_db.search_monsters(query=query, cr=cr, limit=limit)
        if rows:
            return rows
    except Exception as e:
        logger.warning("rules.db monster search failed: %s", e)

    q = (query or "").lower()
    out = []
    for m in MONSTERS.values():
        if q and q not in m["name"].lower():
            continue
        if cr is not None and str(m.get("cr")) != str(cr):
            continue
        out.append(dict(m))
        if len(out) >= limit:
            break
    return out


def list_monsters() -> List[str]:
    try:
        from .rules_db import rules_db

        rows = rules_db.search_monsters(limit=500)
        if rows:
            return sorted(r["name"] for r in rows)
    except Exception:
        pass
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
            if "dexterity_modifier" not in data:
                catalog = get_monster(str(data["name"]))
                if catalog:
                    data.setdefault("dexterity_modifier", catalog["dexterity_modifier"])
                    data.setdefault("attack_bonus", catalog.get("attack_bonus", 0))
                    data.setdefault("damage", catalog.get("damage", "1d4"))
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
