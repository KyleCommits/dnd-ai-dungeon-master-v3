# src/spell_system.py
"""
Comprehensive D&D 5e Spell System
Handles spell lists, spell slots, preparation, and casting mechanics
"""

from dataclasses import dataclass
from typing import Dict, List, Optional, Set, Any
from enum import Enum

class SpellSchool(Enum):
    ABJURATION = "Abjuration"
    CONJURATION = "Conjuration"
    DIVINATION = "Divination"
    ENCHANTMENT = "Enchantment"
    EVOCATION = "Evocation"
    ILLUSION = "Illusion"
    NECROMANCY = "Necromancy"
    TRANSMUTATION = "Transmutation"

class CastingTime(Enum):
    ACTION = "1 action"
    BONUS_ACTION = "1 bonus action"
    REACTION = "1 reaction"
    MINUTE = "1 minute"
    TEN_MINUTES = "10 minutes"
    HOUR = "1 hour"
    EIGHT_HOURS = "8 hours"

class SpellRange(Enum):
    SELF = "Self"
    TOUCH = "Touch"
    FEET_5 = "5 feet"
    FEET_10 = "10 feet"
    FEET_30 = "30 feet"
    FEET_60 = "60 feet"
    FEET_90 = "90 feet"
    FEET_120 = "120 feet"
    FEET_150 = "150 feet"
    FEET_300 = "300 feet"
    FEET_500 = "500 feet"
    FEET_1000 = "1000 feet"
    MILE_1 = "1 mile"
    SIGHT = "Sight"
    UNLIMITED = "Unlimited"

@dataclass
class Spell:
    name: str
    level: int
    school: SpellSchool
    casting_time: CastingTime
    range: SpellRange
    components: List[str]  # V, S, M
    duration: str
    description: str
    damage_dice: Optional[str] = None
    damage_type: Optional[str] = None
    save_type: Optional[str] = None
    attack_type: Optional[str] = None  # "ranged", "melee", None
    ritual: bool = False
    concentration: bool = False
    upcast_benefit: Optional[str] = None
    material_component: Optional[str] = None

class SpellDatabase:
    """Database of all D&D 5e spells"""

    SPELLS = {
        # Cantrips (Level 0)
        "Acid Splash": Spell(
            name="Acid Splash",
            level=0,
            school=SpellSchool.CONJURATION,
            casting_time=CastingTime.ACTION,
            range=SpellRange.FEET_60,
            components=["V", "S"],
            duration="Instantaneous",
            description="Choose one or two creatures within 5 feet of each other within range. Target must make Dex save or take 1d6 acid damage.",
            damage_dice="1d6",
            damage_type="acid",
            save_type="Dexterity"
        ),

        "Eldritch Blast": Spell(
            name="Eldritch Blast",
            level=0,
            school=SpellSchool.EVOCATION,
            casting_time=CastingTime.ACTION,
            range=SpellRange.FEET_120,
            components=["V", "S"],
            duration="Instantaneous",
            description="Make ranged spell attack. On hit, target takes 1d10 force damage.",
            damage_dice="1d10",
            damage_type="force",
            attack_type="ranged"
        ),

        "Fire Bolt": Spell(
            name="Fire Bolt",
            level=0,
            school=SpellSchool.EVOCATION,
            casting_time=CastingTime.ACTION,
            range=SpellRange.FEET_120,
            components=["V", "S"],
            duration="Instantaneous",
            description="Make ranged spell attack. On hit, target takes 1d10 fire damage.",
            damage_dice="1d10",
            damage_type="fire",
            attack_type="ranged"
        ),

        "Mage Hand": Spell(
            name="Mage Hand",
            level=0,
            school=SpellSchool.CONJURATION,
            casting_time=CastingTime.ACTION,
            range=SpellRange.FEET_30,
            components=["V", "S"],
            duration="1 minute",
            description="Create spectral hand that can manipulate objects, open doors, etc. within 30 feet."
        ),

        "Minor Illusion": Spell(
            name="Minor Illusion",
            level=0,
            school=SpellSchool.ILLUSION,
            casting_time=CastingTime.ACTION,
            range=SpellRange.FEET_30,
            components=["S", "M"],
            duration="1 minute",
            description="Create sound or image for 1 minute.",
            material_component="A bit of fleece"
        ),

        "Prestidigitation": Spell(
            name="Prestidigitation",
            level=0,
            school=SpellSchool.TRANSMUTATION,
            casting_time=CastingTime.ACTION,
            range=SpellRange.FEET_10,
            components=["V", "S"],
            duration="Up to 1 hour",
            description="Simple magical effects: light candle, clean object, chill/warm food, etc."
        ),

        # 1st Level Spells
        "Magic Missile": Spell(
            name="Magic Missile",
            level=1,
            school=SpellSchool.EVOCATION,
            casting_time=CastingTime.ACTION,
            range=SpellRange.FEET_120,
            components=["V", "S"],
            duration="Instantaneous",
            description="Create 3 darts that automatically hit targets for 1d4+1 force damage each.",
            damage_dice="3*(1d4+1)",
            damage_type="force",
            upcast_benefit="+1 dart per spell level"
        ),

        "Cure Wounds": Spell(
            name="Cure Wounds",
            level=1,
            school=SpellSchool.EVOCATION,
            casting_time=CastingTime.ACTION,
            range=SpellRange.TOUCH,
            components=["V", "S"],
            duration="Instantaneous",
            description="Touch creature to heal 1d8 + spellcasting modifier hit points.",
            damage_dice="1d8",
            upcast_benefit="+1d8 per spell level"
        ),

        "Shield": Spell(
            name="Shield",
            level=1,
            school=SpellSchool.ABJURATION,
            casting_time=CastingTime.REACTION,
            range=SpellRange.SELF,
            components=["V", "S"],
            duration="1 round",
            description="Reaction when hit by attack. Gain +5 AC until start of next turn."
        ),

        "Healing Word": Spell(
            name="Healing Word",
            level=1,
            school=SpellSchool.EVOCATION,
            casting_time=CastingTime.BONUS_ACTION,
            range=SpellRange.FEET_60,
            components=["V"],
            duration="Instantaneous",
            description="Bonus action to heal creature for 1d4 + spellcasting modifier hit points.",
            damage_dice="1d4",
            upcast_benefit="+1d4 per spell level"
        ),

        # 2nd Level Spells
        "Misty Step": Spell(
            name="Misty Step",
            level=2,
            school=SpellSchool.CONJURATION,
            casting_time=CastingTime.BONUS_ACTION,
            range=SpellRange.SELF,
            components=["V"],
            duration="Instantaneous",
            description="Teleport up to 30 feet to unoccupied space you can see."
        ),

        "Scorching Ray": Spell(
            name="Scorching Ray",
            level=2,
            school=SpellSchool.EVOCATION,
            casting_time=CastingTime.ACTION,
            range=SpellRange.FEET_120,
            components=["V", "S"],
            duration="Instantaneous",
            description="Make 3 ranged spell attacks. Each ray deals 2d6 fire damage on hit.",
            damage_dice="3*2d6",
            damage_type="fire",
            attack_type="ranged",
            upcast_benefit="+1 ray per spell level"
        ),

        # 3rd Level Spells
        "Fireball": Spell(
            name="Fireball",
            level=3,
            school=SpellSchool.EVOCATION,
            casting_time=CastingTime.ACTION,
            range=SpellRange.FEET_150,
            components=["V", "S", "M"],
            duration="Instantaneous",
            description="20-foot radius sphere. Creatures make Dex save or take 8d6 fire damage (half on success).",
            damage_dice="8d6",
            damage_type="fire",
            save_type="Dexterity",
            upcast_benefit="+1d6 per spell level",
            material_component="A tiny ball of bat guano and sulfur"
        ),

        "Lightning Bolt": Spell(
            name="Lightning Bolt",
            level=3,
            school=SpellSchool.EVOCATION,
            casting_time=CastingTime.ACTION,
            range=SpellRange.SELF,
            components=["V", "S", "M"],
            duration="Instantaneous",
            description="100-foot line, 5 feet wide. Creatures make Dex save or take 8d6 lightning damage (half on success).",
            damage_dice="8d6",
            damage_type="lightning",
            save_type="Dexterity",
            upcast_benefit="+1d6 per spell level",
            material_component="A bit of fur and a rod of amber, crystal, or glass"
        ),

        "Counterspell": Spell(
            name="Counterspell",
            level=3,
            school=SpellSchool.ABJURATION,
            casting_time=CastingTime.REACTION,
            range=SpellRange.FEET_60,
            components=["S"],
            duration="Instantaneous",
            description="Reaction to stop spell being cast. Auto-succeeds on 3rd level or lower, ability check for higher."
        )
    }

class SpellSlotManager:
    """Manages spell slots for different caster types"""

    # Spell slot progression tables
    FULL_CASTER_SLOTS = {
        1: [2, 0, 0, 0, 0, 0, 0, 0, 0],
        2: [3, 0, 0, 0, 0, 0, 0, 0, 0],
        3: [4, 2, 0, 0, 0, 0, 0, 0, 0],
        4: [4, 3, 0, 0, 0, 0, 0, 0, 0],
        5: [4, 3, 2, 0, 0, 0, 0, 0, 0],
        6: [4, 3, 3, 0, 0, 0, 0, 0, 0],
        7: [4, 3, 3, 1, 0, 0, 0, 0, 0],
        8: [4, 3, 3, 2, 0, 0, 0, 0, 0],
        9: [4, 3, 3, 3, 1, 0, 0, 0, 0],
        10: [4, 3, 3, 3, 2, 0, 0, 0, 0],
        11: [4, 3, 3, 3, 2, 1, 0, 0, 0],
        12: [4, 3, 3, 3, 2, 1, 0, 0, 0],
        13: [4, 3, 3, 3, 2, 1, 1, 0, 0],
        14: [4, 3, 3, 3, 2, 1, 1, 0, 0],
        15: [4, 3, 3, 3, 2, 1, 1, 1, 0],
        16: [4, 3, 3, 3, 2, 1, 1, 1, 0],
        17: [4, 3, 3, 3, 2, 1, 1, 1, 1],
        18: [4, 3, 3, 3, 3, 1, 1, 1, 1],
        19: [4, 3, 3, 3, 3, 2, 1, 1, 1],
        20: [4, 3, 3, 3, 3, 2, 2, 1, 1]
    }

    HALF_CASTER_SLOTS = {
        1: [0, 0, 0, 0, 0],
        2: [2, 0, 0, 0, 0],
        3: [3, 0, 0, 0, 0],
        4: [3, 0, 0, 0, 0],
        5: [4, 2, 0, 0, 0],
        6: [4, 2, 0, 0, 0],
        7: [4, 3, 0, 0, 0],
        8: [4, 3, 0, 0, 0],
        9: [4, 3, 2, 0, 0],
        10: [4, 3, 2, 0, 0],
        11: [4, 3, 3, 0, 0],
        12: [4, 3, 3, 0, 0],
        13: [4, 3, 3, 1, 0],
        14: [4, 3, 3, 1, 0],
        15: [4, 3, 3, 2, 0],
        16: [4, 3, 3, 2, 0],
        17: [4, 3, 3, 3, 1],
        18: [4, 3, 3, 3, 1],
        19: [4, 3, 3, 3, 2],
        20: [4, 3, 3, 3, 2]
    }

    THIRD_CASTER_SLOTS = {
        1: [0, 0, 0, 0],
        2: [0, 0, 0, 0],
        3: [2, 0, 0, 0],
        4: [3, 0, 0, 0],
        5: [3, 0, 0, 0],
        6: [3, 0, 0, 0],
        7: [4, 2, 0, 0],
        8: [4, 2, 0, 0],
        9: [4, 2, 0, 0],
        10: [4, 3, 0, 0],
        11: [4, 3, 0, 0],
        12: [4, 3, 0, 0],
        13: [4, 3, 2, 0],
        14: [4, 3, 2, 0],
        15: [4, 3, 2, 0],
        16: [4, 3, 3, 0],
        17: [4, 3, 3, 0],
        18: [4, 3, 3, 0],
        19: [4, 3, 3, 1],
        20: [4, 3, 3, 1]
    }

    WARLOCK_SLOTS = {
        1: [1, 0, 0, 0, 0],
        2: [2, 0, 0, 0, 0],
        3: [0, 2, 0, 0, 0],
        4: [0, 2, 0, 0, 0],
        5: [0, 0, 2, 0, 0],
        6: [0, 0, 2, 0, 0],
        7: [0, 0, 0, 2, 0],
        8: [0, 0, 0, 2, 0],
        9: [0, 0, 0, 0, 2],
        10: [0, 0, 0, 0, 2],
        11: [0, 0, 0, 0, 3],
        12: [0, 0, 0, 0, 3],
        13: [0, 0, 0, 0, 3],
        14: [0, 0, 0, 0, 3],
        15: [0, 0, 0, 0, 3],
        16: [0, 0, 0, 0, 3],
        17: [0, 0, 0, 0, 4],
        18: [0, 0, 0, 0, 4],
        19: [0, 0, 0, 0, 4],
        20: [0, 0, 0, 0, 4]
    }

    def get_spell_slots(self, caster_type: str, level: int) -> List[int]:
        """Get spell slots for a caster type and level"""
        if caster_type == "full":
            return self.FULL_CASTER_SLOTS.get(level, [0] * 9)
        elif caster_type == "half":
            return self.HALF_CASTER_SLOTS.get(level, [0] * 5)
        elif caster_type == "third":
            return self.THIRD_CASTER_SLOTS.get(level, [0] * 4)
        elif caster_type == "warlock":
            return self.WARLOCK_SLOTS.get(level, [0] * 5)
        else:
            return [0] * 9

class SpellListManager:
    """Manages spell lists for different classes"""

    CLASS_SPELL_LISTS = {
        "Bard": [
            # Cantrips
            "Minor Illusion", "Prestidigitation", "Mage Hand",
            # 1st level
            "Cure Wounds", "Healing Word",
            # 2nd level
            "Misty Step",
            # 3rd level
            # Bards get Magical Secrets to learn from any list
        ],

        "Cleric": [
            # Cantrips
            "Guidance", "Sacred Flame", "Thaumaturgy",
            # 1st level
            "Cure Wounds", "Healing Word", "Shield of Faith",
            # 2nd level
            "Spiritual Weapon", "Hold Person",
            # 3rd level
            "Spirit Guardians", "Dispel Magic"
        ],

        "Druid": [
            # Cantrips
            "Druidcraft", "Guidance", "Produce Flame",
            # 1st level
            "Cure Wounds", "Healing Word", "Entangle",
            # 2nd level
            "Heat Metal", "Moonbeam",
            # 3rd level
            "Conjure Animals", "Call Lightning"
        ],

        "Sorcerer": [
            # Cantrips
            "Fire Bolt", "Mage Hand", "Minor Illusion", "Prestidigitation",
            # 1st level
            "Magic Missile", "Shield",
            # 2nd level
            "Misty Step", "Scorching Ray",
            # 3rd level
            "Fireball", "Lightning Bolt", "Counterspell"
        ],

        "Warlock": [
            # Cantrips
            "Eldritch Blast", "Minor Illusion", "Prestidigitation",
            # 1st level
            "Hex", "Armor of Agathys",
            # 2nd level
            "Misty Step", "Hold Person",
            # 3rd level
            "Counterspell", "Hypnotic Pattern"
        ],

        "Wizard": [
            # Cantrips
            "Fire Bolt", "Mage Hand", "Minor Illusion", "Prestidigitation",
            # 1st level
            "Magic Missile", "Shield",
            # 2nd level
            "Misty Step", "Scorching Ray",
            # 3rd level
            "Fireball", "Lightning Bolt", "Counterspell"
        ]
    }

    def get_class_spells(self, class_name: str, level: int) -> List[str]:
        """Get available spells for a class up to a given spell level"""
        all_spells = self.CLASS_SPELL_LISTS.get(class_name, [])
        available_spells = []

        for spell_name in all_spells:
            if spell_name in SpellDatabase.SPELLS:
                spell = SpellDatabase.SPELLS[spell_name]
                if spell.level <= level:
                    available_spells.append(spell_name)

        return available_spells

class SpellManager:
    """Main spell management class"""

    def __init__(self):
        self.database = SpellDatabase()
        self.slot_manager = SpellSlotManager()
        self.list_manager = SpellListManager()

    def get_spell(self, name: str) -> Optional[Spell]:
        """Get spell by name"""
        return self.database.SPELLS.get(name)

    def search_spells(self, **kwargs) -> List[Spell]:
        """Search spells by criteria"""
        results = []

        for spell in self.database.SPELLS.values():
            match = True

            if 'level' in kwargs and spell.level != kwargs['level']:
                match = False
            if 'school' in kwargs and spell.school != kwargs['school']:
                match = False
            if 'class_name' in kwargs:
                class_spells = self.list_manager.get_class_spells(kwargs['class_name'], 9)
                if spell.name not in class_spells:
                    match = False

            if match:
                results.append(spell)

        return results

    def calculate_spell_damage(self, spell: Spell, caster_level: int, spell_slot_level: int,
                             ability_modifier: int) -> Dict[str, Any]:
        """Calculate spell damage including upcasting"""
        if not spell.damage_dice:
            return {"damage": 0, "dice": "", "type": ""}

        # Base damage calculation would go here
        # This is simplified - full implementation would parse dice notation

        return {
            "base_damage": spell.damage_dice,
            "damage_type": spell.damage_type,
            "upcast_bonus": spell.upcast_benefit if spell_slot_level > spell.level else None,
            "save_dc": 8 + ability_modifier + ((caster_level - 1) // 4 + 2)  # Prof bonus
        }

# Global spell manager instance
spell_manager = SpellManager()