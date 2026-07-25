#!/usr/bin/env python3
"""
Offline loader: local rules files -> data/rules.db

Sources (no network):
  - dnd_src_material/rules_and_supplements/*.md  (PHB equipment tables, any MD stat blocks)
  - dnd_src_material/rules_and_supplements/SRD-OGL_V5.1.pdf  (monster stat blocks; MM.md is truncated)
  - Existing in-code monster_catalog + equipment_system catalogs as merge/fallback

Usage:
  python scripts/load_rules_from_md.py
  python scripts/load_rules_from_md.py --db data/rules.db
"""
from __future__ import annotations

import argparse
import logging
import os
import re
import sys
from typing import Optional

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from src.rules_db import RulesDB
from src.equipment_system import ItemType

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("load_rules")

RULES_DIR = os.path.join(ROOT, "dnd_src_material", "rules_and_supplements")


def parse_cost_gp(cost: str) -> Optional[float]:
    if not cost:
        return None
    m = re.search(r"([\d,]+(?:\.\d+)?)\s*(cp|sp|ep|gp|pp)", cost.replace(",", ""), re.I)
    if not m:
        return None
    amt = float(m.group(1))
    unit = m.group(2).lower()
    mult = {"cp": 0.01, "sp": 0.1, "ep": 0.5, "gp": 1.0, "pp": 10.0}
    return amt * mult.get(unit, 1.0)


def parse_phb_equipment_tables(text: str, source: str) -> list:
    items = []
    # Armor table rows: | *Name* | cost | AC formula | Str | Stealth | Weight |
    armor_category = None
    for line in text.splitlines():
        if re.search(r"\|\s*\*Light Armor\*\s*\|", line, re.I):
            armor_category = "light"
            continue
        if re.search(r"\|\s*\*Medium Armor\*\s*\|", line, re.I):
            armor_category = "medium"
            continue
        if re.search(r"\|\s*\*Heavy Armor\*\s*\|", line, re.I):
            armor_category = "heavy"
            continue
        if re.search(r"\|\s*\*Shield\*\s*\|", line) and "gp" not in line.lower():
            armor_category = "shield"
            continue

        m = re.match(
            r"\|\s*\*([^*]+)\*\s*\|\s*([^|]*)\|\s*([^|]*)\|\s*([^|]*)\|\s*([^|]*)\|\s*([^|]*)\|",
            line,
        )
        if not m or not armor_category:
            continue
        name = m.group(1).strip()
        if name.lower() in ("light armor", "medium armor", "heavy armor", "shield") and "gp" not in m.group(2).lower() and "+" not in m.group(3):
            continue
        cost = m.group(2).strip()
        ac_cell = m.group(3).strip()
        strength = m.group(4).strip(" —-\t")
        stealth = m.group(5).strip()
        weight = m.group(6).strip()
        if not ac_cell or ac_cell == "—" or set(ac_cell) <= {"-", "—", " ", "\t"}:
            if armor_category != "shield":
                continue

        base_ac = None
        max_dex = None
        item_type = "armor"
        if armor_category == "shield" or ac_cell.startswith("+"):
            item_type = "shield"
            base_ac = 2
            armor_category_out = "shield"
        else:
            armor_category_out = armor_category
            num = re.search(r"(\d+)", ac_cell)
            if num:
                base_ac = int(num.group(1))
            if "max 2" in ac_cell.lower():
                max_dex = 2
            elif "dex" in ac_cell.lower() and armor_category == "light":
                max_dex = None  # unlimited
            elif armor_category == "heavy":
                max_dex = 0

        items.append(
            {
                "name": name.title() if name.islower() else name,
                "item_type": item_type,
                "cost": cost,
                "weight": weight,
                "base_ac": base_ac,
                "max_dex_bonus": max_dex,
                "armor_category": armor_category_out,
                "stealth_disadvantage": "disadvantage" in stealth.lower(),
                "strength_req": strength if strength and strength not in ("—", "-") else None,
                "source": source,
            }
        )

    # Weapons table
    weapon_section = False
    for line in text.splitlines():
        if "##### Weapons" in line or line.strip() == "## Weapons":
            weapon_section = True
        if weapon_section and line.startswith("## ") and "Weapon" not in line:
            weapon_section = False
        if not weapon_section:
            continue
        if re.search(r"\|\s*\*(Simple|Martial).*\*\s*\|", line):
            continue
        m = re.match(
            r"\|\s*\*([^*]+)\*\s*\|\s*([^|]*)\|\s*([^|]*)\|\s*([^|]*)\|\s*([^|]*)\|",
            line,
        )
        if not m:
            continue
        name = m.group(1).strip()
        cost = m.group(2).strip()
        damage_cell = m.group(3).strip()
        weight = m.group(4).strip()
        props = m.group(5).strip()
        if not damage_cell or "damage" in damage_cell.lower():
            continue
        dm = re.match(r"([\dd+\s]+)\s+(\w+)", damage_cell)
        if not dm:
            continue
        items.append(
            {
                "name": name.title() if "," in name else name[0].upper() + name[1:] if name else name,
                "item_type": "weapon",
                "cost": cost,
                "weight": weight,
                "damage": dm.group(1).replace(" ", ""),
                "damage_type": dm.group(2),
                "properties": props if props not in ("—", "-") else "",
                "source": source,
            }
        )
    return items


def parse_md_stat_blocks(text: str, source: str) -> list:
    """Best-effort: Armor Class N / Hit Points N blocks in markdown."""
    monsters = []
    pattern = re.compile(
        r"(?P<header>^#{1,3}\s+(?P<name>[A-Z][^\n]{1,60}))\s*\n"
        r"(?P<body>(?:.*\n){0,40}?)"
        r"Armor Class\s+(?P<ac>\d+)"
        r"(?P<body2>(?:.*\n){0,30}?)"
        r"Hit Points\s+(?P<hp>\d+)",
        re.MULTILINE | re.IGNORECASE,
    )
    for m in pattern.finditer(text):
        name = m.group("name").strip()
        body = (m.group("body") or "") + (m.group("body2") or "")
        cr_m = re.search(r"Challenge\s+([\d/]+)", body, re.I)
        atk_m = re.search(
            r"(?:Melee|Ranged)\s+Weapon\s+Attack:\s*\+(\d+)\s+to hit.*?Hit:\s*\d+\s*\(([^)]+)\)",
            body,
            re.I | re.S,
        )
        dex_m = re.search(r"DEX\s*\n?\s*(\d+)", body, re.I)
        dex_mod = 0
        if dex_m:
            dex_mod = (int(dex_m.group(1)) - 10) // 2
        attack_bonus = int(atk_m.group(1)) if atk_m else 0
        damage = atk_m.group(2).replace(" ", "") if atk_m else "1d4"
        monsters.append(
            {
                "name": name,
                "ac": int(m.group("ac")),
                "hp": int(m.group("hp")),
                "cr": cr_m.group(1) if cr_m else None,
                "dexterity_modifier": dex_mod,
                "attack_bonus": attack_bonus,
                "damage": damage,
                "actions": [],
                "source": source,
            }
        )
    return monsters


def normalize_pdf_text(text: str) -> str:
    text = text.replace("\xa0", " ").replace("\u00a0", " ")
    text = text.replace("\u2212", "-")  # unicode minus
    text = re.sub(r"[\t\r]+", " ", text)
    text = re.sub(r" +", " ", text)
    return text


def extract_pdf_text(pdf_path: str) -> str:
    from PyPDF2 import PdfReader

    reader = PdfReader(pdf_path)
    parts = []
    for page in reader.pages:
        try:
            parts.append(normalize_pdf_text(page.extract_text() or ""))
        except Exception:
            continue
    return "\n".join(parts)


def parse_srd_monsters(text: str, source: str) -> list:
    """
    Parse flattened SRD PDF text using a resilient header match, then scan a
    forward window for DEX, Challenge, and attacks.
    """
    monsters = []
    header = re.compile(
        r"(?P<name>[A-Z][A-Za-z0-9' \-]{1,40}?)\s+"
        r"(?P<size>Tiny|Small|Medium|Large|Huge|Gargantuan)\s+"
        r"(?P<ctype>[a-z][a-z \-]{1,40}?),\s*"
        r"(?P<align>[^A]{0,40}?)"
        r"Armor Class\s+(?P<ac>\d+)"
        r".{0,80}?"
        r"Hit Points\s+(?P<hp>\d+)",
        re.S,
    )

    skip_names = {
        "actions", "reactions", "traits", "legendary actions", "skills",
        "senses", "languages", "saving throws", "damage resistances",
        "damage immunities", "condition immunities", "damage vulnerabilities",
        "giants", "humanoids",
    }

    for m in header.finditer(text):
        name = m.group("name").strip()
        parts = name.split()
        while parts and parts[0].lower() in skip_names:
            parts = parts[1:]
        if not parts:
            continue
        if len(parts) > 4:
            parts = parts[-3:]
        name = " ".join(parts).strip()
        if name.lower() in skip_names or len(name) < 2:
            continue

        window = text[m.start() : m.end() + 900]
        speed_m = re.search(r"Speed\s+(.+?)\s+STR\s+DEX", window, re.S)
        dex_m = re.search(
            r"STR\s+DEX\s+CON\s+INT\s+WIS\s+CHA\s+"
            r"\d+\s*\([+\-]?\d+\)\s+"
            r"\d+\s*\(([+\-]?\d+)\)",
            window,
            re.S,
        )
        cr_m = re.search(r"Challenge\s+([\d/]+)\s*\(", window)
        actions = []
        for am in re.finditer(
            r"([A-Z][A-Za-z' \-/]{1,28})\.\s*"
            r"(Melee|Ranged|Melee or Ranged)\s+Weapon\s+Attack:\s*\+(\d+)\s+to hit,"
            r".*?Hit:\s*(?:\d+\s*)?\(([^)]+)\)\s*(\w+)?",
            window,
            re.S,
        ):
            actions.append(
                {
                    "name": am.group(1).strip(),
                    "kind": am.group(2).lower(),
                    "attack_bonus": int(am.group(3)),
                    "damage": am.group(4).replace(" ", ""),
                    "damage_type": (am.group(5) or "").lower(),
                }
            )

        attack_bonus = actions[0]["attack_bonus"] if actions else 0
        damage = actions[0]["damage"] if actions else "1d4"
        dex_mod = int(dex_m.group(1)) if dex_m else 0

        monsters.append(
            {
                "name": name,
                "ac": int(m.group("ac")),
                "hp": int(m.group("hp")),
                "cr": cr_m.group(1) if cr_m else None,
                "speed": speed_m.group(1).strip() if speed_m else None,
                "size": m.group("size"),
                "creature_type": m.group("ctype").strip(),
                "dexterity_modifier": dex_mod,
                "attack_bonus": attack_bonus,
                "damage": damage,
                "actions": actions,
                "source": source,
            }
        )
    return monsters


def seed_from_python_catalogs(db: RulesDB) -> tuple:
    from src.monster_catalog import MONSTERS
    from src.equipment_system import WeaponDatabase, ArmorDatabase

    m_count = 0
    for key, data in MONSTERS.items():
        row = dict(data)
        row.setdefault("source", "monster_catalog_seed")
        row.setdefault("actions", [])
        db.upsert_monster(row)
        m_count += 1

    e_count = 0
    for name, weapon in WeaponDatabase.WEAPONS.items():
        db.upsert_equipment(
            {
                "name": name,
                "item_type": "weapon",
                "cost": f"{weapon.cost_gp} gp",
                "weight": f"{weapon.weight_lb} lb.",
                "damage": weapon.damage.dice if weapon.damage else None,
                "damage_type": weapon.damage.damage_type if weapon.damage else None,
                "properties": ", ".join(weapon.properties or []),
                "source": "equipment_system_seed",
            }
        )
        e_count += 1
    for name, armor in ArmorDatabase.ARMOR.items():
        is_shield = getattr(armor, "item_type", None) == ItemType.SHIELD or name.lower() == "shield"
        db.upsert_equipment(
            {
                "name": name,
                "item_type": "shield" if is_shield else "armor",
                "cost": f"{armor.cost_gp} gp",
                "weight": f"{armor.weight_lb} lb.",
                "base_ac": 2 if is_shield else armor.base_ac,
                "max_dex_bonus": None if is_shield else armor.max_dex_bonus,
                "armor_category": "shield" if is_shield else (
                    armor.armor_type.value if hasattr(armor, "armor_type") else None
                ),
                "stealth_disadvantage": getattr(armor, "stealth_disadvantage", False),
                "strength_req": (
                    f"Str {armor.strength_requirement}"
                    if getattr(armor, "strength_requirement", None)
                    else None
                ),
                "source": "equipment_system_seed",
            }
        )
        e_count += 1
    return m_count, e_count


def main():
    parser = argparse.ArgumentParser(description="Load local rules MD/PDF into data/rules.db")
    parser.add_argument("--db", default=os.path.join(ROOT, "data", "rules.db"))
    parser.add_argument("--fresh", action="store_true", help="Clear tables before load")
    args = parser.parse_args()

    if not os.path.isdir(RULES_DIR):
        logger.error("Rules directory missing: %s", RULES_DIR)
        sys.exit(1)

    db = RulesDB(args.db)
    db.initialize_schema()
    if args.fresh:
        db.clear_tables()

    m_seed, e_seed = seed_from_python_catalogs(db)
    logger.info("Seeded %s monsters and %s equipment from Python catalogs", m_seed, e_seed)

    md_monsters = 0
    md_equipment = 0
    for fname in sorted(os.listdir(RULES_DIR)):
        if not fname.lower().endswith(".md"):
            continue
        path = os.path.join(RULES_DIR, fname)
        logger.info("Parsing MD: %s", fname)
        text = open(path, encoding="utf-8", errors="ignore").read()
        for item in parse_phb_equipment_tables(text, source=fname):
            db.upsert_equipment(item)
            md_equipment += 1
        for mon in parse_md_stat_blocks(text, source=fname):
            db.upsert_monster(mon)
            md_monsters += 1

    logger.info("From MD tables/blocks: %s equipment rows upserted, %s monster blocks", md_equipment, md_monsters)

    pdf_path = os.path.join(RULES_DIR, "SRD-OGL_V5.1.pdf")
    pdf_count = 0
    if os.path.isfile(pdf_path):
        logger.info("Extracting monsters from local SRD PDF (offline)...")
        pdf_text = extract_pdf_text(pdf_path)
        for mon in parse_srd_monsters(pdf_text, source="SRD-OGL_V5.1.pdf"):
            db.upsert_monster(mon)
            pdf_count += 1
        logger.info("Upserted %s monsters from SRD PDF", pdf_count)
    else:
        logger.warning("SRD PDF not found at %s — monster set limited to seeds/MD", pdf_path)

    counts = db.counts()
    logger.info("DONE. data/rules.db -> %s", counts)
    if counts["monsters"] == 0 or counts["equipment"] == 0:
        logger.error("Load produced empty tables")
        sys.exit(2)


if __name__ == "__main__":
    main()
