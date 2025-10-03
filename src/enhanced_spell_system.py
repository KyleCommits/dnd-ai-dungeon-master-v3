# src/enhanced_spell_system.py
"""
enhanced d&d 5e spell system
handles all 319+ spells from the dnd api with detailed data
"""

import json
import requests
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Any, Union
from enum import Enum
import sqlite3
import os

class SpellSchool(Enum):
    ABJURATION = "abjuration"
    CONJURATION = "conjuration"
    DIVINATION = "divination"
    ENCHANTMENT = "enchantment"
    EVOCATION = "evocation"
    ILLUSION = "illusion"
    NECROMANCY = "necromancy"
    TRANSMUTATION = "transmutation"

@dataclass
class SpellDamage:
    damage_type: Optional[str] = None
    damage_at_slot_level: Dict[int, str] = field(default_factory=dict)

@dataclass
class SpellSavingThrow:
    ability: Optional[str] = None
    success_type: Optional[str] = None  # "half", "none", etc.

@dataclass
class SpellAreaOfEffect:
    type: Optional[str] = None  # "sphere", "cone", "line", etc.
    size: Optional[int] = None

@dataclass
class SpellClass:
    index: str
    name: str

@dataclass
class EnhancedSpell:
    """enhanced spell data that matches the dnd api format"""
    index: str
    name: str
    level: int
    school: str
    casting_time: str
    range: str
    components: List[str]
    duration: str
    description: List[str]

    # optional fields
    higher_level: List[str] = field(default_factory=list)
    material: Optional[str] = None
    ritual: bool = False
    concentration: bool = False
    damage: Optional[SpellDamage] = None
    saving_throw: Optional[SpellSavingThrow] = None
    area_of_effect: Optional[SpellAreaOfEffect] = None
    classes: List[SpellClass] = field(default_factory=list)
    subclasses: List[Dict] = field(default_factory=list)
    attack_type: Optional[str] = None  # "ranged", "melee"
    heal_at_slot_level: Dict[int, str] = field(default_factory=dict)

class SpellDataFetcher:
    """grabs spell data from the dnd api"""

    BASE_URL = "https://www.dnd5eapi.co/api"

    def __init__(self):
        self.session = requests.Session()
        self.rate_limit_delay = 0.1  # 100ms between requests

    def fetch_all_spells_list(self) -> List[Dict]:
        """get the list of all spells available"""
        try:
            response = self.session.get(f"{self.BASE_URL}/spells")
            response.raise_for_status()
            data = response.json()
            return data.get('results', [])
        except Exception as e:
            print(f"ERROR: Failed to fetch spell list: {e}")
            return []

    def fetch_spell_details(self, spell_url: str) -> Optional[Dict]:
        """get detailed info for a specific spell"""
        try:
            time.sleep(self.rate_limit_delay)
            # remove /api if already there
            if spell_url.startswith('/api'):
                full_url = f"https://www.dnd5eapi.co{spell_url}"
            else:
                full_url = f"{self.BASE_URL}{spell_url}"
            response = self.session.get(full_url)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"ERROR: Failed to fetch spell details from {spell_url}: {e}")
            return None

    def fetch_all_spell_details(self) -> List[Dict]:
        """get all the spell details from the api"""
        spell_list = self.fetch_all_spells_list()
        detailed_spells = []

        print(f"Fetching details for {len(spell_list)} spells...")

        for i, spell_summary in enumerate(spell_list):
            print(f"[{i+1}/{len(spell_list)}] Fetching {spell_summary['name']}...")

            details = self.fetch_spell_details(spell_summary['url'])
            if details:
                detailed_spells.append(details)

            # show progress every 50
            if (i + 1) % 50 == 0:
                print(f"Progress: {i+1}/{len(spell_list)} spells fetched")

        print(f"Successfully fetched {len(detailed_spells)} spell details")
        return detailed_spells

class SpellDatabase:
    """sqlite database to store and search spells"""

    def __init__(self, db_path: str = "data/spells.db"):
        self.db_path = db_path
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self.init_database()

    def init_database(self):
        """setup the spells database"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS spells (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    spell_index TEXT UNIQUE NOT NULL,
                    name TEXT NOT NULL,
                    level INTEGER NOT NULL,
                    school TEXT NOT NULL,
                    casting_time TEXT NOT NULL,
                    range_text TEXT NOT NULL,
                    components TEXT NOT NULL,
                    duration TEXT NOT NULL,
                    description TEXT NOT NULL,
                    higher_level TEXT,
                    material TEXT,
                    ritual BOOLEAN DEFAULT FALSE,
                    concentration BOOLEAN DEFAULT FALSE,
                    damage_type TEXT,
                    damage_at_slot_level TEXT,
                    saving_throw_ability TEXT,
                    saving_throw_success TEXT,
                    area_type TEXT,
                    area_size INTEGER,
                    classes TEXT,
                    subclasses TEXT,
                    attack_type TEXT,
                    heal_at_slot_level TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # create indexes for speed
            conn.execute("CREATE INDEX IF NOT EXISTS idx_spell_level ON spells(level)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_spell_school ON spells(school)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_spell_name ON spells(name)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_spell_classes ON spells(classes)")

    def insert_spell(self, spell: EnhancedSpell):
        """add or update a spell in the db"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO spells (
                    spell_index, name, level, school, casting_time, range_text, components,
                    duration, description, higher_level, material, ritual, concentration,
                    damage_type, damage_at_slot_level, saving_throw_ability, saving_throw_success,
                    area_type, area_size, classes, subclasses, attack_type, heal_at_slot_level,
                    updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """, (
                spell.index, spell.name, spell.level, spell.school, spell.casting_time,
                spell.range, json.dumps(spell.components), spell.duration,
                json.dumps(spell.description), json.dumps(spell.higher_level),
                spell.material, spell.ritual, spell.concentration,
                spell.damage.damage_type if spell.damage else None,
                json.dumps(spell.damage.damage_at_slot_level) if spell.damage else None,
                spell.saving_throw.ability if spell.saving_throw else None,
                spell.saving_throw.success_type if spell.saving_throw else None,
                spell.area_of_effect.type if spell.area_of_effect else None,
                spell.area_of_effect.size if spell.area_of_effect else None,
                json.dumps([c.name for c in spell.classes]),
                json.dumps(spell.subclasses),
                spell.attack_type,
                json.dumps(spell.heal_at_slot_level)
            ))

    def get_spell_by_name(self, name: str) -> Optional[EnhancedSpell]:
        """find a spell by its name"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("SELECT * FROM spells WHERE name = ?", (name,))
            row = cursor.fetchone()

            if row:
                return self._row_to_spell(row)
            return None

    def get_spells_by_level(self, level: int) -> List[EnhancedSpell]:
        """get all spells for a certain level"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("SELECT * FROM spells WHERE level = ? ORDER BY name", (level,))
            return [self._row_to_spell(row) for row in cursor.fetchall()]

    def get_spells_by_class(self, class_name: str) -> List[EnhancedSpell]:
        """find spells that a class can use"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                "SELECT * FROM spells WHERE classes LIKE ? ORDER BY level, name",
                (f'%{class_name}%',)
            )
            return [self._row_to_spell(row) for row in cursor.fetchall()]

    def search_spells(self, **kwargs) -> List[EnhancedSpell]:
        """search spells using various filters"""
        conditions = []
        params = []

        if 'level' in kwargs:
            conditions.append("level = ?")
            params.append(kwargs['level'])

        if 'school' in kwargs:
            conditions.append("school = ?")
            params.append(kwargs['school'])

        if 'class_name' in kwargs:
            conditions.append("classes LIKE ?")
            params.append(f"%{kwargs['class_name']}%")

        if 'ritual' in kwargs:
            conditions.append("ritual = ?")
            params.append(kwargs['ritual'])

        if 'concentration' in kwargs:
            conditions.append("concentration = ?")
            params.append(kwargs['concentration'])

        if 'name_contains' in kwargs:
            conditions.append("name LIKE ?")
            params.append(f"%{kwargs['name_contains']}%")

        where_clause = " AND ".join(conditions) if conditions else "1=1"

        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                f"SELECT * FROM spells WHERE {where_clause} ORDER BY level, name",
                params
            )
            return [self._row_to_spell(row) for row in cursor.fetchall()]

    def get_spell_count(self) -> int:
        """count how many spells we have in the db"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("SELECT COUNT(*) FROM spells")
            return cursor.fetchone()[0]

    def _row_to_spell(self, row: sqlite3.Row) -> EnhancedSpell:
        """turn database row into spell object"""
        damage = None
        if row['damage_type']:
            damage = SpellDamage(
                damage_type=row['damage_type'],
                damage_at_slot_level=json.loads(row['damage_at_slot_level'] or '{}')
            )

        saving_throw = None
        if row['saving_throw_ability']:
            saving_throw = SpellSavingThrow(
                ability=row['saving_throw_ability'],
                success_type=row['saving_throw_success']
            )

        area_of_effect = None
        if row['area_type']:
            area_of_effect = SpellAreaOfEffect(
                type=row['area_type'],
                size=row['area_size']
            )

        classes = [SpellClass(c, c) for c in json.loads(row['classes'] or '[]')]

        return EnhancedSpell(
            index=row['spell_index'],
            name=row['name'],
            level=row['level'],
            school=row['school'],
            casting_time=row['casting_time'],
            range=row['range_text'],
            components=json.loads(row['components']),
            duration=row['duration'],
            description=json.loads(row['description']),
            higher_level=json.loads(row['higher_level'] or '[]'),
            material=row['material'],
            ritual=bool(row['ritual']),
            concentration=bool(row['concentration']),
            damage=damage,
            saving_throw=saving_throw,
            area_of_effect=area_of_effect,
            classes=classes,
            subclasses=json.loads(row['subclasses'] or '[]'),
            attack_type=row['attack_type'],
            heal_at_slot_level=json.loads(row['heal_at_slot_level'] or '{}')
        )

class SpellDataLoader:
    """loads spell data from api into our database"""

    def __init__(self):
        self.fetcher = SpellDataFetcher()
        self.database = SpellDatabase()

    def load_all_spells(self):
        """grab all spells from api and put them in db"""
        print("Starting spell data import...")

        # check if spells already loaded
        existing_count = self.database.get_spell_count()
        if existing_count > 0:
            print(f"Database already contains {existing_count} spells.")
            response = input("Reload all spells? (y/n): ").lower()
            if response != 'y':
                print("Skipping spell reload.")
                return

        # fetch all spells
        spell_data = self.fetcher.fetch_all_spell_details()

        if not spell_data:
            print("ERROR: No spell data fetched")
            return

        print(f"Processing {len(spell_data)} spells...")

        # process and save spells
        for i, spell_dict in enumerate(spell_data):
            try:
                spell = self._convert_api_spell(spell_dict)
                self.database.insert_spell(spell)

                if (i + 1) % 50 == 0:
                    print(f"Processed {i+1}/{len(spell_data)} spells")

            except Exception as e:
                print(f"ERROR: Failed to process spell {spell_dict.get('name', 'Unknown')}: {e}")

        final_count = self.database.get_spell_count()
        print(f"SUCCESS: Imported {final_count} spells into database")

    def _convert_api_spell(self, api_data: Dict) -> EnhancedSpell:
        """turn api spell data into our spell object"""

        # handle damage data
        damage = None
        if 'damage' in api_data and api_data['damage']:
            damage_type = None
            damage_at_slot_level = {}

            if 'damage_type' in api_data['damage']:
                damage_type = api_data['damage']['damage_type']['name']

            if 'damage_at_slot_level' in api_data['damage']:
                damage_at_slot_level = api_data['damage']['damage_at_slot_level']

            damage = SpellDamage(
                damage_type=damage_type,
                damage_at_slot_level=damage_at_slot_level
            )

        # process saving throws
        saving_throw = None
        if 'dc' in api_data and api_data['dc']:
            saving_throw = SpellSavingThrow(
                ability=api_data['dc']['dc_type']['name'],
                success_type=api_data['dc'].get('dc_success', 'none')
            )

        # handle area effects
        area_of_effect = None
        if 'area_of_effect' in api_data and api_data['area_of_effect']:
            area_of_effect = SpellAreaOfEffect(
                type=api_data['area_of_effect']['type'],
                size=api_data['area_of_effect']['size']
            )

        # determine class availability
        classes = []
        if 'classes' in api_data:
            classes = [SpellClass(c['index'], c['name']) for c in api_data['classes']]

        # process healing spells
        heal_at_slot_level = {}
        if 'heal_at_slot_level' in api_data:
            heal_at_slot_level = api_data['heal_at_slot_level']

        # check if attack spell
        attack_type = None
        if 'attack_type' in api_data:
            attack_type = api_data['attack_type']
        elif damage and any(word in ' '.join(api_data.get('desc', [])).lower()
                           for word in ['ranged spell attack', 'spell attack roll']):
            attack_type = "ranged"

        return EnhancedSpell(
            index=api_data['index'],
            name=api_data['name'],
            level=api_data['level'],
            school=api_data['school']['name'].lower(),
            casting_time=api_data['casting_time'],
            range=api_data['range'],
            components=api_data['components'],
            duration=api_data['duration'],
            description=api_data.get('desc', []),
            higher_level=api_data.get('higher_level', []),
            material=api_data.get('material'),
            ritual=api_data.get('ritual', False),
            concentration=api_data.get('concentration', False),
            damage=damage,
            saving_throw=saving_throw,
            area_of_effect=area_of_effect,
            classes=classes,
            subclasses=api_data.get('subclasses', []),
            attack_type=attack_type,
            heal_at_slot_level=heal_at_slot_level
        )

class EnhancedSpellManager:
    """enhanced spell manager with full database integration"""

    def __init__(self):
        self.database = SpellDatabase()
        self.loader = SpellDataLoader()

    def initialize(self):
        """setup the spell system - run this once"""
        spell_count = self.database.get_spell_count()
        if spell_count == 0:
            print("No spells found in database. Loading from API...")
            self.loader.load_all_spells()
        else:
            print(f"Spell system initialized with {spell_count} spells")

    def get_spell(self, name: str) -> Optional[EnhancedSpell]:
        """find a spell by name"""
        return self.database.get_spell_by_name(name)

    def get_class_spells(self, class_name: str, max_level: int = 9) -> List[EnhancedSpell]:
        """get spells for a class up to a certain level"""
        all_spells = self.database.get_spells_by_class(class_name)
        return [s for s in all_spells if s.level <= max_level]

    def search_spells(self, **kwargs) -> List[EnhancedSpell]:
        """search spells using different filters"""
        return self.database.search_spells(**kwargs)

    def get_cantrips(self, class_name: str = None) -> List[EnhancedSpell]:
        """get cantrips, maybe filtered by class"""
        if class_name:
            return self.search_spells(level=0, class_name=class_name)
        return self.database.get_spells_by_level(0)

    def get_spell_statistics(self) -> Dict[str, Any]:
        """get stats about our spell database"""
        total = self.database.get_spell_count()
        by_level = {}
        by_school = {}

        for level in range(10):  # 0-9
            spells = self.database.get_spells_by_level(level)
            by_level[level] = len(spells)

        for school in SpellSchool:
            spells = self.search_spells(school=school.value)
            by_school[school.value] = len(spells)

        return {
            "total_spells": total,
            "spells_by_level": by_level,
            "spells_by_school": by_school
        }

# main spell manager
enhanced_spell_manager = EnhancedSpellManager()

if __name__ == "__main__":
    # command line loading
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "load":
        print("Loading spell data from D&D 5e API...")
        loader = SpellDataLoader()
        loader.load_all_spells()
    else:
        # test the system
        manager = EnhancedSpellManager()
        manager.initialize()

        # display stats
        stats = manager.get_spell_statistics()
        print(f"Total spells: {stats['total_spells']}")
        print(f"Spells by level: {stats['spells_by_level']}")

        # test spell lookup
        fireball = manager.get_spell("Fireball")
        if fireball:
            print(f"\nFound spell: {fireball.name}")
            print(f"Level: {fireball.level}")
            print(f"School: {fireball.school}")
            print(f"Description: {' '.join(fireball.description)}")