#!/usr/bin/env python3
"""Ensure a known combat monster set exists in data/rules.db."""
from __future__ import annotations

import argparse
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

PLAYTEST_MONSTERS = [
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
            {"name": "Scimitar", "attack_bonus": 4, "damage": "1d6+2", "damage_type": "slashing"}
        ],
        "source": "playtest-seed",
    },
    {
        "name": "Wolf",
        "cr": "1/4",
        "size": "Medium",
        "creature_type": "beast",
        "ac": 13,
        "hp": 11,
        "speed": "40 ft.",
        "dexterity_modifier": 2,
        "attack_bonus": 4,
        "damage": "2d4+2",
        "actions": [
            {"name": "Bite", "attack_bonus": 4, "damage": "2d4+2", "damage_type": "piercing"}
        ],
        "source": "playtest-seed",
    },
    {
        "name": "Orc",
        "cr": "1/2",
        "size": "Medium",
        "creature_type": "humanoid",
        "ac": 13,
        "hp": 15,
        "speed": "30 ft.",
        "dexterity_modifier": 1,
        "attack_bonus": 5,
        "damage": "1d12+3",
        "actions": [
            {"name": "Greataxe", "attack_bonus": 5, "damage": "1d12+3", "damage_type": "slashing"}
        ],
        "source": "playtest-seed",
    },
    {
        "name": "Skeleton",
        "cr": "1/4",
        "size": "Medium",
        "creature_type": "undead",
        "ac": 13,
        "hp": 13,
        "speed": "30 ft.",
        "dexterity_modifier": 2,
        "attack_bonus": 4,
        "damage": "1d6+2",
        "actions": [
            {"name": "Shortsword", "attack_bonus": 4, "damage": "1d6+2", "damage_type": "piercing"}
        ],
        "source": "playtest-seed",
    },
]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", default="data/rules.db")
    parser.add_argument(
        "--full-load",
        action="store_true",
        help="Also run load_rules_from_md.py (needs local MD/PDF)",
    )
    args = parser.parse_args()

    if args.full_load:
        import subprocess

        r = subprocess.run([sys.executable, os.path.join("scripts", "load_rules_from_md.py")], cwd=ROOT)
        if r.returncode != 0:
            print("WARNING: full load failed; continuing with playtest upserts")

    from src.rules_db import RulesDB

    db = RulesDB(args.db)
    db.initialize_schema()
    for m in PLAYTEST_MONSTERS:
        db.upsert_monster(m)
        print(f"SUCCESS: upserted monster {m['name']}")

    from src.monster_catalog import get_monster

    for m in PLAYTEST_MONSTERS:
        got = get_monster(m["name"])
        if not got:
            print(f"ERROR: lookup failed for {m['name']}")
            return 1
    print("SUCCESS: playtest monsters ready (/monster goblin, wolf, orc, skeleton)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
