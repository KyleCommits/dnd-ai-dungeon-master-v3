# src/rules_db.py — offline SQLite lookups for monsters + equipment (data/rules.db)
from __future__ import annotations

import json
import logging
import os
import sqlite3
from typing import Any, Dict, List, Optional

DEFAULT_DB_PATH = "data/rules.db"

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS monsters (
    name TEXT PRIMARY KEY COLLATE NOCASE,
    cr TEXT,
    size TEXT,
    creature_type TEXT,
    ac INTEGER NOT NULL,
    hp INTEGER NOT NULL,
    speed TEXT,
    dexterity_modifier INTEGER DEFAULT 0,
    attack_bonus INTEGER DEFAULT 0,
    damage TEXT DEFAULT '1d4',
    actions_json TEXT DEFAULT '[]',
    source TEXT,
    raw_stats_json TEXT DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS equipment (
    name TEXT PRIMARY KEY COLLATE NOCASE,
    item_type TEXT NOT NULL,
    cost TEXT,
    weight TEXT,
    damage TEXT,
    damage_type TEXT,
    properties TEXT,
    base_ac INTEGER,
    max_dex_bonus INTEGER,
    armor_category TEXT,
    stealth_disadvantage INTEGER DEFAULT 0,
    strength_req TEXT,
    source TEXT,
    raw_json TEXT DEFAULT '{}'
);

CREATE INDEX IF NOT EXISTS idx_monsters_cr ON monsters(cr);
CREATE INDEX IF NOT EXISTS idx_equipment_type ON equipment(item_type);
"""


class RulesDB:
    def __init__(self, db_path: str = DEFAULT_DB_PATH):
        self.db_path = db_path
        self._ensure_parent()

    def _ensure_parent(self) -> None:
        parent = os.path.dirname(self.db_path)
        if parent:
            os.makedirs(parent, exist_ok=True)

    def connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def initialize_schema(self) -> None:
        with self.connect() as conn:
            conn.executescript(SCHEMA_SQL)
            conn.commit()

    def clear_tables(self) -> None:
        with self.connect() as conn:
            conn.execute("DELETE FROM monsters")
            conn.execute("DELETE FROM equipment")
            conn.commit()

    def upsert_monster(self, data: Dict[str, Any]) -> None:
        name = (data.get("name") or "").strip()
        if not name:
            return
        actions = data.get("actions") or []
        raw = {k: v for k, v in data.items() if k not in ("actions",)}
        with self.connect() as conn:
            conn.execute(
                """
                INSERT INTO monsters (
                    name, cr, size, creature_type, ac, hp, speed,
                    dexterity_modifier, attack_bonus, damage, actions_json, source, raw_stats_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(name) DO UPDATE SET
                    cr=excluded.cr,
                    size=excluded.size,
                    creature_type=excluded.creature_type,
                    ac=excluded.ac,
                    hp=excluded.hp,
                    speed=excluded.speed,
                    dexterity_modifier=excluded.dexterity_modifier,
                    attack_bonus=excluded.attack_bonus,
                    damage=excluded.damage,
                    actions_json=excluded.actions_json,
                    source=excluded.source,
                    raw_stats_json=excluded.raw_stats_json
                """,
                (
                    name,
                    data.get("cr"),
                    data.get("size"),
                    data.get("creature_type"),
                    int(data.get("ac", 10)),
                    int(data.get("hp", 1)),
                    data.get("speed"),
                    int(data.get("dexterity_modifier", 0)),
                    int(data.get("attack_bonus", 0)),
                    str(data.get("damage", "1d4")),
                    json.dumps(actions),
                    data.get("source"),
                    json.dumps(raw),
                ),
            )
            conn.commit()

    def upsert_equipment(self, data: Dict[str, Any]) -> None:
        name = (data.get("name") or "").strip()
        if not name:
            return
        with self.connect() as conn:
            conn.execute(
                """
                INSERT INTO equipment (
                    name, item_type, cost, weight, damage, damage_type, properties,
                    base_ac, max_dex_bonus, armor_category, stealth_disadvantage,
                    strength_req, source, raw_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(name) DO UPDATE SET
                    item_type=excluded.item_type,
                    cost=excluded.cost,
                    weight=excluded.weight,
                    damage=excluded.damage,
                    damage_type=excluded.damage_type,
                    properties=excluded.properties,
                    base_ac=excluded.base_ac,
                    max_dex_bonus=excluded.max_dex_bonus,
                    armor_category=excluded.armor_category,
                    stealth_disadvantage=excluded.stealth_disadvantage,
                    strength_req=excluded.strength_req,
                    source=excluded.source,
                    raw_json=excluded.raw_json
                """,
                (
                    name,
                    data.get("item_type", "gear"),
                    data.get("cost"),
                    data.get("weight"),
                    data.get("damage"),
                    data.get("damage_type"),
                    data.get("properties"),
                    data.get("base_ac"),
                    data.get("max_dex_bonus"),
                    data.get("armor_category"),
                    1 if data.get("stealth_disadvantage") else 0,
                    data.get("strength_req"),
                    data.get("source"),
                    json.dumps(data),
                ),
            )
            conn.commit()

    def get_monster(self, name: str) -> Optional[Dict[str, Any]]:
        if not os.path.isfile(self.db_path):
            return None
        with self.connect() as conn:
            row = conn.execute(
                "SELECT * FROM monsters WHERE name = ? COLLATE NOCASE",
                (name.strip(),),
            ).fetchone()
            if not row:
                # fuzzy contains
                row = conn.execute(
                    "SELECT * FROM monsters WHERE name LIKE ? COLLATE NOCASE ORDER BY LENGTH(name) LIMIT 1",
                    (f"%{name.strip()}%",),
                ).fetchone()
            if not row:
                return None
            return self._monster_row(row)

    def search_monsters(self, query: str = "", cr: Optional[str] = None, limit: int = 40) -> List[Dict[str, Any]]:
        if not os.path.isfile(self.db_path):
            return []
        clauses = ["1=1"]
        params: List[Any] = []
        if query:
            clauses.append("name LIKE ? COLLATE NOCASE")
            params.append(f"%{query}%")
        if cr is not None:
            clauses.append("cr = ?")
            params.append(str(cr))
        sql = f"SELECT * FROM monsters WHERE {' AND '.join(clauses)} ORDER BY name LIMIT ?"
        params.append(limit)
        with self.connect() as conn:
            rows = conn.execute(sql, params).fetchall()
            return [self._monster_row(r) for r in rows]

    def get_item(self, name: str) -> Optional[Dict[str, Any]]:
        if not os.path.isfile(self.db_path):
            return None
        with self.connect() as conn:
            row = conn.execute(
                "SELECT * FROM equipment WHERE name = ? COLLATE NOCASE",
                (name.strip(),),
            ).fetchone()
            if not row:
                row = conn.execute(
                    "SELECT * FROM equipment WHERE name LIKE ? COLLATE NOCASE ORDER BY LENGTH(name) LIMIT 1",
                    (f"%{name.strip()}%",),
                ).fetchone()
            if not row:
                return None
            return self._equipment_row(row)

    def search_items(self, query: str = "", item_type: Optional[str] = None, limit: int = 40) -> List[Dict[str, Any]]:
        if not os.path.isfile(self.db_path):
            return []
        clauses = ["1=1"]
        params: List[Any] = []
        if query:
            clauses.append("name LIKE ? COLLATE NOCASE")
            params.append(f"%{query}%")
        if item_type:
            clauses.append("item_type = ? COLLATE NOCASE")
            params.append(item_type)
        sql = f"SELECT * FROM equipment WHERE {' AND '.join(clauses)} ORDER BY name LIMIT ?"
        params.append(limit)
        with self.connect() as conn:
            rows = conn.execute(sql, params).fetchall()
            return [self._equipment_row(r) for r in rows]

    def counts(self) -> Dict[str, int]:
        if not os.path.isfile(self.db_path):
            return {"monsters": 0, "equipment": 0}
        with self.connect() as conn:
            m = conn.execute("SELECT COUNT(*) FROM monsters").fetchone()[0]
            e = conn.execute("SELECT COUNT(*) FROM equipment").fetchone()[0]
            return {"monsters": m, "equipment": e}

    @staticmethod
    def _monster_row(row: sqlite3.Row) -> Dict[str, Any]:
        actions = []
        try:
            actions = json.loads(row["actions_json"] or "[]")
        except Exception:
            actions = []
        return {
            "name": row["name"],
            "cr": row["cr"],
            "size": row["size"],
            "creature_type": row["creature_type"],
            "ac": row["ac"],
            "hp": row["hp"],
            "speed": row["speed"],
            "dexterity_modifier": row["dexterity_modifier"],
            "attack_bonus": row["attack_bonus"],
            "damage": row["damage"],
            "actions": actions,
            "source": row["source"],
        }

    @staticmethod
    def _equipment_row(row: sqlite3.Row) -> Dict[str, Any]:
        return {
            "name": row["name"],
            "item_type": row["item_type"],
            "cost": row["cost"],
            "weight": row["weight"],
            "damage": row["damage"],
            "damage_type": row["damage_type"],
            "properties": row["properties"],
            "base_ac": row["base_ac"],
            "max_dex_bonus": row["max_dex_bonus"],
            "armor_category": row["armor_category"],
            "stealth_disadvantage": bool(row["stealth_disadvantage"]),
            "strength_req": row["strength_req"],
            "source": row["source"],
        }


rules_db = RulesDB()
