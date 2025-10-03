# src/detailed_character_creator.py
"""
Enhanced D&D 5e Character Creator with comprehensive rule support
Handles all PHB races, classes, subclasses, feats, and variants
"""

import json
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from enum import Enum

@dataclass
class RacialTrait:
    name: str
    description: str
    level_gained: int = 1

@dataclass
class AbilityScoreIncrease:
    ability: str
    amount: int

@dataclass
class RaceVariant:
    name: str
    ability_increases: List[AbilityScoreIncrease]
    traits: List[RacialTrait]
    size: str = "Medium"
    speed: int = 30
    languages: List[str] = None
    proficiencies: List[str] = None
    extra_language: bool = False
    extra_skill: bool = False
    extra_cantrip: bool = False

class CharacterRace:
    """Comprehensive race definitions with all variants and options"""

    RACES = {
        "Human": {
            "base_speed": 30,
            "size": "Medium",
            "languages": ["Common"],
            "variants": {
                "Standard Human": RaceVariant(
                    name="Standard Human",
                    ability_increases=[
                        AbilityScoreIncrease("strength", 1),
                        AbilityScoreIncrease("dexterity", 1),
                        AbilityScoreIncrease("constitution", 1),
                        AbilityScoreIncrease("intelligence", 1),
                        AbilityScoreIncrease("wisdom", 1),
                        AbilityScoreIncrease("charisma", 1)
                    ],
                    traits=[
                        RacialTrait("Versatile", "Humans are adaptable and ambitious")
                    ],
                    extra_language=True,
                    proficiencies=["One skill of choice"]
                ),
                "Variant Human": RaceVariant(
                    name="Variant Human",
                    ability_increases=[
                        # Player chooses two different abilities to increase by 1
                    ],
                    traits=[
                        RacialTrait("Extra Feat", "Choose one feat at 1st level"),
                        RacialTrait("Skills", "Choose one skill proficiency")
                    ],
                    extra_language=True,
                    extra_skill=True
                ),
                "Custom Lineage": RaceVariant(
                    name="Custom Lineage",
                    ability_increases=[
                        # Player chooses one ability to increase by 2 OR two abilities by 1
                    ],
                    traits=[
                        RacialTrait("Variable Size", "Choose Small or Medium"),
                        RacialTrait("Extra Feat", "Choose one feat at 1st level"),
                        RacialTrait("Darkvision", "60 feet darkvision OR extra skill proficiency")
                    ]
                )
            }
        },

        "Elf": {
            "base_speed": 30,
            "size": "Medium",
            "languages": ["Common", "Elvish"],
            "traits": [
                RacialTrait("Darkvision", "60 feet"),
                RacialTrait("Keen Senses", "Proficiency in Perception"),
                RacialTrait("Fey Ancestry", "Advantage on saves vs charmed, immune to sleep"),
                RacialTrait("Trance", "4 hours of trance instead of 8 hours sleep")
            ],
            "variants": {
                "High Elf": RaceVariant(
                    name="High Elf",
                    ability_increases=[
                        AbilityScoreIncrease("dexterity", 2),
                        AbilityScoreIncrease("intelligence", 1)
                    ],
                    traits=[
                        RacialTrait("Cantrip", "Know one wizard cantrip"),
                        RacialTrait("Weapon Training", "Proficiency with longswords, shortbows, longbows, shortswords"),
                        RacialTrait("Extra Language", "One additional language")
                    ]
                ),
                "Wood Elf": RaceVariant(
                    name="Wood Elf",
                    ability_increases=[
                        AbilityScoreIncrease("dexterity", 2),
                        AbilityScoreIncrease("wisdom", 1)
                    ],
                    traits=[
                        RacialTrait("Weapon Training", "Proficiency with longswords, shortbows, longbows, shortswords"),
                        RacialTrait("Fleet of Foot", "Speed increases to 35 feet"),
                        RacialTrait("Mask of the Wild", "Hide when lightly obscured by natural phenomena")
                    ],
                    speed=35
                ),
                "Dark Elf (Drow)": RaceVariant(
                    name="Dark Elf (Drow)",
                    ability_increases=[
                        AbilityScoreIncrease("dexterity", 2),
                        AbilityScoreIncrease("charisma", 1)
                    ],
                    traits=[
                        RacialTrait("Superior Darkvision", "120 feet darkvision"),
                        RacialTrait("Sunlight Sensitivity", "Disadvantage in bright light"),
                        RacialTrait("Drow Magic", "Dancing lights cantrip, faerie fire and darkness spells"),
                        RacialTrait("Weapon Training", "Proficiency with rapiers, shortswords, hand crossbows")
                    ]
                )
            }
        },

        "Dwarf": {
            "base_speed": 25,
            "size": "Medium",
            "languages": ["Common", "Dwarvish"],
            "traits": [
                RacialTrait("Darkvision", "60 feet"),
                RacialTrait("Dwarven Resilience", "Advantage on saves vs poison, resistance to poison damage"),
                RacialTrait("Stonecunning", "Add double proficiency to History checks on stonework"),
                RacialTrait("Dwarven Combat Training", "Proficiency with battleaxes, handaxes, light hammers, warhammers")
            ],
            "variants": {
                "Mountain Dwarf": RaceVariant(
                    name="Mountain Dwarf",
                    ability_increases=[
                        AbilityScoreIncrease("constitution", 2),
                        AbilityScoreIncrease("strength", 1)
                    ],
                    traits=[
                        RacialTrait("Armor Training", "Proficiency with light and medium armor")
                    ]
                ),
                "Hill Dwarf": RaceVariant(
                    name="Hill Dwarf",
                    ability_increases=[
                        AbilityScoreIncrease("constitution", 2),
                        AbilityScoreIncrease("wisdom", 1)
                    ],
                    traits=[
                        RacialTrait("Dwarven Toughness", "Hit point maximum increases by 1, +1 per level")
                    ]
                )
            }
        },

        "Halfling": {
            "base_speed": 25,
            "size": "Small",
            "languages": ["Common", "Halfling"],
            "traits": [
                RacialTrait("Lucky", "Reroll natural 1s on attack rolls, ability checks, and saves"),
                RacialTrait("Brave", "Advantage on saves vs frightened"),
                RacialTrait("Halfling Nimbleness", "Move through space of Medium or larger creatures")
            ],
            "variants": {
                "Lightfoot Halfling": RaceVariant(
                    name="Lightfoot Halfling",
                    ability_increases=[
                        AbilityScoreIncrease("dexterity", 2),
                        AbilityScoreIncrease("charisma", 1)
                    ],
                    traits=[
                        RacialTrait("Naturally Stealthy", "Hide even behind Medium or larger creatures")
                    ]
                ),
                "Stout Halfling": RaceVariant(
                    name="Stout Halfling",
                    ability_increases=[
                        AbilityScoreIncrease("dexterity", 2),
                        AbilityScoreIncrease("constitution", 1)
                    ],
                    traits=[
                        RacialTrait("Stout Resilience", "Advantage on saves vs poison, resistance to poison damage")
                    ]
                )
            }
        },

        "Dragonborn": {
            "base_speed": 30,
            "size": "Medium",
            "languages": ["Common", "Draconic"],
            "traits": [
                RacialTrait("Draconic Ancestry", "Choose a dragon type for breath weapon and resistance"),
                RacialTrait("Breath Weapon", "Use action to exhale destructive energy"),
                RacialTrait("Damage Resistance", "Resistance to damage type associated with draconic ancestry")
            ],
            "variants": {
                "Chromatic Dragonborn": RaceVariant(
                    name="Chromatic Dragonborn",
                    ability_increases=[
                        AbilityScoreIncrease("strength", 2),
                        AbilityScoreIncrease("charisma", 1)
                    ],
                    traits=[
                        RacialTrait("Chromatic Warding", "Starting at 5th level, resistance to chosen damage type")
                    ]
                ),
                "Metallic Dragonborn": RaceVariant(
                    name="Metallic Dragonborn",
                    ability_increases=[
                        AbilityScoreIncrease("strength", 2),
                        AbilityScoreIncrease("charisma", 1)
                    ],
                    traits=[
                        RacialTrait("Metallic Breath Weapon", "Enervating or repulsion breath at 5th level")
                    ]
                ),
                "Gem Dragonborn": RaceVariant(
                    name="Gem Dragonborn",
                    ability_increases=[
                        AbilityScoreIncrease("strength", 2),
                        AbilityScoreIncrease("charisma", 1)
                    ],
                    traits=[
                        RacialTrait("Telepathic", "Telepathic communication"),
                        RacialTrait("Gem Flight", "Temporary flight at 5th level")
                    ]
                )
            }
        },

        "Gnome": {
            "base_speed": 25,
            "size": "Small",
            "languages": ["Common", "Gnomish"],
            "traits": [
                RacialTrait("Darkvision", "60 feet"),
                RacialTrait("Gnome Cunning", "Advantage on Int, Wis, Cha saves vs magic")
            ],
            "variants": {
                "Forest Gnome": RaceVariant(
                    name="Forest Gnome",
                    ability_increases=[
                        AbilityScoreIncrease("intelligence", 2),
                        AbilityScoreIncrease("dexterity", 1)
                    ],
                    traits=[
                        RacialTrait("Natural Illusionist", "Know minor illusion cantrip"),
                        RacialTrait("Speak with Small Beasts", "Communicate simple ideas with Small beasts")
                    ]
                ),
                "Rock Gnome": RaceVariant(
                    name="Rock Gnome",
                    ability_increases=[
                        AbilityScoreIncrease("intelligence", 2),
                        AbilityScoreIncrease("constitution", 1)
                    ],
                    traits=[
                        RacialTrait("Artificer's Lore", "Add double proficiency to History checks about magic items"),
                        RacialTrait("Tinker", "Construct tiny clockwork devices")
                    ]
                )
            }
        },

        "Half-Elf": {
            "base_speed": 30,
            "size": "Medium",
            "languages": ["Common", "Elvish"],
            "traits": [
                RacialTrait("Darkvision", "60 feet"),
                RacialTrait("Fey Ancestry", "Advantage on saves vs charmed, immune to sleep"),
                RacialTrait("Skill Versatility", "Proficiency in two skills of choice")
            ],
            "variants": {
                "Half-Elf": RaceVariant(
                    name="Half-Elf",
                    ability_increases=[
                        AbilityScoreIncrease("charisma", 2)
                        # Player chooses two other abilities to increase by 1
                    ],
                    traits=[],
                    extra_language=True
                )
            }
        },

        "Half-Orc": {
            "base_speed": 30,
            "size": "Medium",
            "languages": ["Common", "Orc"],
            "traits": [
                RacialTrait("Darkvision", "60 feet"),
                RacialTrait("Menacing", "Proficiency in Intimidation"),
                RacialTrait("Relentless Endurance", "Drop to 1 HP instead of 0 once per long rest"),
                RacialTrait("Savage Attacks", "Extra damage die on critical hits with melee weapons")
            ],
            "variants": {
                "Half-Orc": RaceVariant(
                    name="Half-Orc",
                    ability_increases=[
                        AbilityScoreIncrease("strength", 2),
                        AbilityScoreIncrease("constitution", 1)
                    ],
                    traits=[]
                )
            }
        },

        "Tiefling": {
            "base_speed": 30,
            "size": "Medium",
            "languages": ["Common", "Infernal"],
            "traits": [
                RacialTrait("Darkvision", "60 feet"),
                RacialTrait("Hellish Resistance", "Resistance to fire damage"),
                RacialTrait("Infernal Legacy", "Know thaumaturgy cantrip, bonus spells at higher levels")
            ],
            "variants": {
                "Asmodeus Tiefling": RaceVariant(
                    name="Asmodeus Tiefling",
                    ability_increases=[
                        AbilityScoreIncrease("intelligence", 1),
                        AbilityScoreIncrease("charisma", 2)
                    ],
                    traits=[
                        RacialTrait("Infernal Legacy", "Thaumaturgy cantrip, hellish rebuke at 3rd level, darkness at 5th level")
                    ]
                ),
                "Baalzebul Tiefling": RaceVariant(
                    name="Baalzebul Tiefling",
                    ability_increases=[
                        AbilityScoreIncrease("intelligence", 1),
                        AbilityScoreIncrease("charisma", 2)
                    ],
                    traits=[
                        RacialTrait("Legacy of Maladomini", "Thaumaturgy cantrip, ray of sickness at 3rd level, crown of madness at 5th level")
                    ]
                ),
                "Dispater Tiefling": RaceVariant(
                    name="Dispater Tiefling",
                    ability_increases=[
                        AbilityScoreIncrease("dexterity", 1),
                        AbilityScoreIncrease("charisma", 2)
                    ],
                    traits=[
                        RacialTrait("Legacy of Dis", "Thaumaturgy cantrip, disguise self at 3rd level, detect thoughts at 5th level")
                    ]
                ),
                "Fierna Tiefling": RaceVariant(
                    name="Fierna Tiefling",
                    ability_increases=[
                        AbilityScoreIncrease("wisdom", 1),
                        AbilityScoreIncrease("charisma", 2)
                    ],
                    traits=[
                        RacialTrait("Legacy of Phlegethos", "Friends cantrip, charm person at 3rd level, suggestion at 5th level")
                    ]
                ),
                "Glasya Tiefling": RaceVariant(
                    name="Glasya Tiefling",
                    ability_increases=[
                        AbilityScoreIncrease("dexterity", 1),
                        AbilityScoreIncrease("charisma", 2)
                    ],
                    traits=[
                        RacialTrait("Legacy of Malbolge", "Minor illusion cantrip, disguise self at 3rd level, invisibility at 5th level")
                    ]
                ),
                "Levistus Tiefling": RaceVariant(
                    name="Levistus Tiefling",
                    ability_increases=[
                        AbilityScoreIncrease("constitution", 1),
                        AbilityScoreIncrease("charisma", 2)
                    ],
                    traits=[
                        RacialTrait("Legacy of Stygia", "Ray of frost cantrip, armor of Agathys at 3rd level, darkness at 5th level")
                    ]
                ),
                "Mammon Tiefling": RaceVariant(
                    name="Mammon Tiefling",
                    ability_increases=[
                        AbilityScoreIncrease("intelligence", 1),
                        AbilityScoreIncrease("charisma", 2)
                    ],
                    traits=[
                        RacialTrait("Legacy of Minauros", "Mage hand cantrip, Tenser's floating disk at 3rd level, arcane lock at 5th level")
                    ]
                ),
                "Mephistopheles Tiefling": RaceVariant(
                    name="Mephistopheles Tiefling",
                    ability_increases=[
                        AbilityScoreIncrease("intelligence", 1),
                        AbilityScoreIncrease("charisma", 2)
                    ],
                    traits=[
                        RacialTrait("Legacy of Cania", "Mage hand cantrip, burning hands at 3rd level, flame blade at 5th level")
                    ]
                ),
                "Zariel Tiefling": RaceVariant(
                    name="Zariel Tiefling",
                    ability_increases=[
                        AbilityScoreIncrease("strength", 1),
                        AbilityScoreIncrease("charisma", 2)
                    ],
                    traits=[
                        RacialTrait("Legacy of Avernus", "Thaumaturgy cantrip, searing smite at 3rd level, branding smite at 5th level")
                    ]
                )
            }
        },

        # Supplement Races from Volo's Guide
        "Aasimar": {
            "base_speed": 30,
            "size": "Medium",
            "languages": ["Common", "Celestial"],
            "traits": [
                RacialTrait("Darkvision", "60 feet"),
                RacialTrait("Celestial Resistance", "Resistance to necrotic and radiant damage"),
                RacialTrait("Healing Hands", "Heal hit points equal to your level once per long rest"),
                RacialTrait("Light Bearer", "Know the light cantrip")
            ],
            "variants": {
                "Protector Aasimar": RaceVariant(
                    name="Protector Aasimar",
                    ability_increases=[
                        AbilityScoreIncrease("charisma", 2),
                        AbilityScoreIncrease("wisdom", 1)
                    ],
                    traits=[
                        RacialTrait("Radiant Soul", "Transformation: sprout spectral wings, fly 30 feet, extra radiant damage")
                    ]
                ),
                "Scourge Aasimar": RaceVariant(
                    name="Scourge Aasimar",
                    ability_increases=[
                        AbilityScoreIncrease("charisma", 2),
                        AbilityScoreIncrease("constitution", 1)
                    ],
                    traits=[
                        RacialTrait("Radiant Consumption", "Transformation: radiant damage aura, damage yourself and enemies")
                    ]
                ),
                "Fallen Aasimar": RaceVariant(
                    name="Fallen Aasimar",
                    ability_increases=[
                        AbilityScoreIncrease("charisma", 2),
                        AbilityScoreIncrease("strength", 1)
                    ],
                    traits=[
                        RacialTrait("Necrotic Shroud", "Transformation: skeletal wings, frighten enemies, extra necrotic damage")
                    ]
                )
            }
        },

        "Bugbear": {
            "base_speed": 30,
            "size": "Medium",
            "languages": ["Common", "Goblin"],
            "traits": [
                RacialTrait("Darkvision", "60 feet"),
                RacialTrait("Long-Limbed", "Extra 5 feet reach on melee attacks"),
                RacialTrait("Powerful Build", "Count as one size larger for carrying capacity"),
                RacialTrait("Sneaky", "Proficiency in Stealth"),
                RacialTrait("Surprise Attack", "Extra 2d6 damage on first turn if you hit surprised creature")
            ],
            "variants": {
                "Bugbear": RaceVariant(
                    name="Bugbear",
                    ability_increases=[
                        AbilityScoreIncrease("strength", 2),
                        AbilityScoreIncrease("dexterity", 1)
                    ],
                    traits=[]
                )
            }
        },

        "Firbolg": {
            "base_speed": 30,
            "size": "Medium",
            "languages": ["Common", "Elvish", "Giant"],
            "traits": [
                RacialTrait("Firbolg Magic", "Detect magic and disguise self spells once per rest"),
                RacialTrait("Hidden Step", "Turn invisible as bonus action once per rest"),
                RacialTrait("Powerful Build", "Count as one size larger for carrying capacity"),
                RacialTrait("Speech of Beast and Leaf", "Limited communication with beasts and plants")
            ],
            "variants": {
                "Firbolg": RaceVariant(
                    name="Firbolg",
                    ability_increases=[
                        AbilityScoreIncrease("wisdom", 2),
                        AbilityScoreIncrease("strength", 1)
                    ],
                    traits=[]
                )
            }
        },

        "Goliath": {
            "base_speed": 30,
            "size": "Medium",
            "languages": ["Common", "Giant"],
            "traits": [
                RacialTrait("Natural Athlete", "Proficiency in Athletics"),
                RacialTrait("Stone's Endurance", "Reduce damage by 1d12 + Con modifier once per rest"),
                RacialTrait("Powerful Build", "Count as one size larger for carrying capacity"),
                RacialTrait("Mountain Born", "Acclimated to high altitude and cold climate")
            ],
            "variants": {
                "Goliath": RaceVariant(
                    name="Goliath",
                    ability_increases=[
                        AbilityScoreIncrease("strength", 2),
                        AbilityScoreIncrease("constitution", 1)
                    ],
                    traits=[]
                )
            }
        },

        "Kenku": {
            "base_speed": 30,
            "size": "Medium",
            "languages": ["Common", "Aulran"],
            "traits": [
                RacialTrait("Expert Forgery", "Advantage on forgery checks and checks to produce duplicates"),
                RacialTrait("Kenku Training", "Proficiency in two skills of choice"),
                RacialTrait("Mimicry", "Mimic sounds and voices you have heard")
            ],
            "variants": {
                "Kenku": RaceVariant(
                    name="Kenku",
                    ability_increases=[
                        AbilityScoreIncrease("dexterity", 2),
                        AbilityScoreIncrease("wisdom", 1)
                    ],
                    traits=[]
                )
            }
        },

        "Lizardfolk": {
            "base_speed": 30,
            "size": "Medium",
            "languages": ["Common", "Draconic"],
            "traits": [
                RacialTrait("Bite", "1d6 + Strength piercing damage unarmed strike"),
                RacialTrait("Cunning Artisan", "Craft tools and weapons from corpses"),
                RacialTrait("Hold Breath", "Hold breath for 15 minutes"),
                RacialTrait("Hunter's Lore", "Proficiency with two skills from Animal Handling, Nature, Perception, Stealth, Survival"),
                RacialTrait("Natural Armor", "13 + Dex modifier AC when not wearing armor"),
                RacialTrait("Swimming", "30 feet swim speed")
            ],
            "variants": {
                "Lizardfolk": RaceVariant(
                    name="Lizardfolk",
                    ability_increases=[
                        AbilityScoreIncrease("constitution", 2),
                        AbilityScoreIncrease("wisdom", 1)
                    ],
                    traits=[]
                )
            }
        },

        "Tabaxi": {
            "base_speed": 30,
            "size": "Medium",
            "languages": ["Common"],
            "traits": [
                RacialTrait("Darkvision", "60 feet"),
                RacialTrait("Feline Agility", "Double speed until you move 0 feet on a turn"),
                RacialTrait("Cat's Claws", "Climbing speed of 20 feet"),
                RacialTrait("Cat's Talents", "Proficiency in Perception and Stealth")
            ],
            "variants": {
                "Tabaxi": RaceVariant(
                    name="Tabaxi",
                    ability_increases=[
                        AbilityScoreIncrease("dexterity", 2),
                        AbilityScoreIncrease("charisma", 1)
                    ],
                    traits=[],
                    extra_language=True
                )
            }
        },

        "Triton": {
            "base_speed": 30,
            "size": "Medium",
            "languages": ["Common", "Primordial"],
            "traits": [
                RacialTrait("Amphibious", "Breathe air and water"),
                RacialTrait("Control Air and Water", "Fog cloud spell, other spells at higher levels"),
                RacialTrait("Emissary of the Sea", "Limited communication with beasts that have swimming speed"),
                RacialTrait("Guardians of the Depths", "Resistance to cold damage"),
                RacialTrait("Swimming", "30 feet swim speed")
            ],
            "variants": {
                "Triton": RaceVariant(
                    name="Triton",
                    ability_increases=[
                        AbilityScoreIncrease("strength", 1),
                        AbilityScoreIncrease("constitution", 1),
                        AbilityScoreIncrease("charisma", 1)
                    ],
                    traits=[]
                )
            }
        },

        # Eberron Races
        "Changeling": {
            "base_speed": 30,
            "size": "Medium",
            "languages": ["Common"],
            "traits": [
                RacialTrait("Shapechanger", "Change appearance and voice as action"),
                RacialTrait("Changeling Instincts", "Proficiency with two skills and thieves' tools or another tool"),
                RacialTrait("Divergent Persona", "Proficiency with one tool, different persona for each tool")
            ],
            "variants": {
                "Changeling": RaceVariant(
                    name="Changeling",
                    ability_increases=[
                        AbilityScoreIncrease("charisma", 2)
                        # Player chooses one other ability to increase by 1
                    ],
                    traits=[],
                    extra_language=True
                )
            }
        },

        "Kalashtar": {
            "base_speed": 30,
            "size": "Medium",
            "languages": ["Common", "Quori"],
            "traits": [
                RacialTrait("Dual Mind", "Advantage on Wisdom saving throws"),
                RacialTrait("Mental Discipline", "Resistance to psychic damage"),
                RacialTrait("Mind Link", "Telepathic communication"),
                RacialTrait("Severed from Dreams", "Don't need sleep, can't be forced to sleep"),
                RacialTrait("Telepathic", "Telepathic communication")
            ],
            "variants": {
                "Kalashtar": RaceVariant(
                    name="Kalashtar",
                    ability_increases=[
                        AbilityScoreIncrease("wisdom", 2),
                        AbilityScoreIncrease("charisma", 1)
                    ],
                    traits=[]
                )
            }
        },

        "Warforged": {
            "base_speed": 30,
            "size": "Medium",
            "languages": ["Common"],
            "traits": [
                RacialTrait("Constructed Resilience", "Advantage on saves vs disease, don't need food/drink/air/sleep"),
                RacialTrait("Sentry's Rest", "Long rest in 6 hours while conscious"),
                RacialTrait("Integrated Protection", "AC = 11 + Dex modifier + proficiency bonus"),
                RacialTrait("Specialized Design", "Proficiency with one skill and one tool")
            ],
            "variants": {
                "Warforged": RaceVariant(
                    name="Warforged",
                    ability_increases=[
                        AbilityScoreIncrease("constitution", 2)
                        # Player chooses one other ability to increase by 1
                    ],
                    traits=[],
                    extra_language=True
                )
            }
        },

        "Shifter": {
            "base_speed": 30,
            "size": "Medium",
            "languages": ["Common"],
            "traits": [
                RacialTrait("Darkvision", "60 feet"),
                RacialTrait("Keen Senses", "Proficiency in Perception"),
                RacialTrait("Shifting", "Transform as bonus action, gain temporary hit points")
            ],
            "variants": {
                "Beasthide Shifter": RaceVariant(
                    name="Beasthide Shifter",
                    ability_increases=[
                        AbilityScoreIncrease("dexterity", 1),
                        AbilityScoreIncrease("constitution", 2)
                    ],
                    traits=[
                        RacialTrait("Shifting Feature", "Gain +1 AC while shifted"),
                        RacialTrait("Natural Athlete", "Proficiency in Athletics")
                    ]
                ),
                "Longtooth Shifter": RaceVariant(
                    name="Longtooth Shifter",
                    ability_increases=[
                        AbilityScoreIncrease("strength", 2),
                        AbilityScoreIncrease("dexterity", 1)
                    ],
                    traits=[
                        RacialTrait("Shifting Feature", "Bite attack (1d6 + Str modifier) while shifted"),
                        RacialTrait("Fierce", "Proficiency in Intimidation")
                    ]
                ),
                "Swiftstride Shifter": RaceVariant(
                    name="Swiftstride Shifter",
                    ability_increases=[
                        AbilityScoreIncrease("dexterity", 2),
                        AbilityScoreIncrease("charisma", 1)
                    ],
                    traits=[
                        RacialTrait("Shifting Feature", "Speed increases by 10 feet while shifted"),
                        RacialTrait("Graceful", "Proficiency in Acrobatics")
                    ]
                ),
                "Wildhunt Shifter": RaceVariant(
                    name="Wildhunt Shifter",
                    ability_increases=[
                        AbilityScoreIncrease("dexterity", 1),
                        AbilityScoreIncrease("wisdom", 2)
                    ],
                    traits=[
                        RacialTrait("Shifting Feature", "Advantage on Wisdom checks while shifted"),
                        RacialTrait("Natural Tracker", "Proficiency in Survival")
                    ]
                )
            }
        }
    }

class CharacterClass:
    """Comprehensive class definitions with subclasses and progression"""

    CLASSES = {
        "Fighter": {
            "hit_die": 10,
            "primary_abilities": ["Strength", "Dexterity"],
            "saving_throws": ["Strength", "Constitution"],
            "armor_proficiencies": ["All armor", "shields"],
            "weapon_proficiencies": ["Simple weapons", "martial weapons"],
            "skill_choices": 2,
            "skill_list": ["Acrobatics", "Animal Handling", "Athletics", "History",
                          "Insight", "Intimidation", "Perception", "Survival"],
            "starting_equipment": {
                "armor": "Chain mail OR leather armor + longbow + 20 arrows",
                "weapons": "Shield + martial weapon OR two martial weapons",
                "pack": "Dungeoneer's pack OR explorer's pack",
                "other": "Light crossbow + 20 bolts"
            },
            "subclasses": {
                "Champion": {
                    "level_gained": 3,
                    "features": {
                        3: ["Improved Critical"],
                        7: ["Remarkable Athlete"],
                        10: ["Additional Fighting Style"],
                        15: ["Superior Critical"],
                        18: ["Survivor"]
                    }
                },
                "Battle Master": {
                    "level_gained": 3,
                    "features": {
                        3: ["Combat Superiority", "Maneuvers"],
                        7: ["Know Your Enemy"],
                        10: ["Additional Maneuvers", "Improved Combat Superiority"],
                        15: ["Relentless"],
                        18: ["Improved Combat Superiority (d12)"]
                    }
                },
                "Eldritch Knight": {
                    "level_gained": 3,
                    "features": {
                        3: ["Spellcasting", "Weapon Bond"],
                        7: ["War Magic"],
                        10: ["Eldritch Strike"],
                        15: ["Arcane Charge"],
                        18: ["Improved War Magic"]
                    },
                    "spellcasting": {
                        "ability": "Intelligence",
                        "type": "third_caster",
                        "spell_list": "Wizard (Abjuration/Evocation focus)"
                    }
                }
            }
        },

        "Wizard": {
            "hit_die": 6,
            "primary_abilities": ["Intelligence"],
            "saving_throws": ["Intelligence", "Wisdom"],
            "armor_proficiencies": [],
            "weapon_proficiencies": ["Daggers", "darts", "slings", "quarterstaffs", "light crossbows"],
            "skill_choices": 2,
            "skill_list": ["Arcana", "History", "Insight", "Investigation", "Medicine", "Religion"],
            "spellcasting": {
                "ability": "Intelligence",
                "type": "full_caster",
                "ritual_casting": True,
                "spellbook": True,
                "cantrips_known": [3, 3, 3, 4, 4, 4, 4, 4, 4, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5],
                "spells_known": "2 + Int modifier + 2 per level"
            },
            "subclasses": {
                "School of Evocation": {
                    "level_gained": 2,
                    "features": {
                        2: ["Evocation Savant", "Sculpt Spells"],
                        6: ["Potent Cantrip"],
                        10: ["Empowered Evocation"],
                        14: ["Overchannel"]
                    }
                },
                "School of Abjuration": {
                    "level_gained": 2,
                    "features": {
                        2: ["Abjuration Savant", "Arcane Ward"],
                        6: ["Projected Ward"],
                        10: ["Improved Abjuration"],
                        14: ["Spell Resistance"]
                    }
                },
                "School of Conjuration": {
                    "level_gained": 2,
                    "features": {
                        2: ["Conjuration Savant", "Minor Conjuration"],
                        6: ["Benign Transposition"],
                        10: ["Focused Conjuration"],
                        14: ["Durable Summons"]
                    }
                },
                "School of Divination": {
                    "level_gained": 2,
                    "features": {
                        2: ["Divination Savant", "Portent"],
                        6: ["Expert Divination"],
                        10: ["The Third Eye"],
                        14: ["Greater Portent"]
                    }
                },
                "School of Enchantment": {
                    "level_gained": 2,
                    "features": {
                        2: ["Enchantment Savant", "Hypnotic Gaze"],
                        6: ["Split Enchantment"],
                        10: ["Misty Escape"],
                        14: ["Alter Memories"]
                    }
                },
                "School of Illusion": {
                    "level_gained": 2,
                    "features": {
                        2: ["Illusion Savant", "Improved Minor Illusion"],
                        6: ["Malleable Illusions"],
                        10: ["Illusory Self"],
                        14: ["Illusory Reality"]
                    }
                },
                "School of Necromancy": {
                    "level_gained": 2,
                    "features": {
                        2: ["Necromancy Savant", "Grim Harvest"],
                        6: ["Undead Thralls"],
                        10: ["Inured to Undeath"],
                        14: ["Command Undead"]
                    }
                },
                "School of Transmutation": {
                    "level_gained": 2,
                    "features": {
                        2: ["Transmutation Savant", "Minor Alchemy"],
                        6: ["Transmuter's Stone"],
                        10: ["Shapechanger"],
                        14: ["Master Transmuter"]
                    }
                },
                "War Magic": {
                    "level_gained": 2,
                    "features": {
                        2: ["Arcane Deflection", "Tactical Wit"],
                        6: ["Power Surge"],
                        10: ["Durable Magic"],
                        14: ["Deflecting Shroud"]
                    }
                },
                "Order of Scribes": {
                    "level_gained": 2,
                    "features": {
                        2: ["Wizardly Quill", "Awakened Spellbook"],
                        6: ["Manifest Mind"],
                        10: ["Master Scrivener"],
                        14: ["One with the Word"]
                    }
                },
                "Bladesinger": {
                    "level_gained": 2,
                    "features": {
                        2: ["Bladesong", "Training in War and Song"],
                        6: ["Extra Attack"],
                        10: ["Song of Defense"],
                        14: ["Song of Victory"]
                    }
                }
            }
        },

        "Barbarian": {
            "hit_die": 12,
            "primary_abilities": ["Strength"],
            "saving_throws": ["Strength", "Constitution"],
            "armor_proficiencies": ["Light armor", "medium armor", "shields"],
            "weapon_proficiencies": ["Simple weapons", "martial weapons"],
            "skill_choices": 2,
            "skill_list": ["Animal Handling", "Athletics", "Intimidation", "Nature", "Perception", "Survival"],
            "subclasses": {
                "Path of the Berserker": {
                    "level_gained": 3,
                    "features": {
                        3: ["Frenzy"],
                        6: ["Mindless Rage"],
                        10: ["Intimidating Presence"],
                        14: ["Retaliation"]
                    }
                },
                "Path of the Totem Warrior": {
                    "level_gained": 3,
                    "features": {
                        3: ["Spirit Seeker", "Totem Spirit"],
                        6: ["Aspect of the Beast"],
                        10: ["Spirit Walker"],
                        14: ["Totemic Attunement"]
                    }
                },
                "Path of the Ancestral Guardian": {
                    "level_gained": 3,
                    "features": {
                        3: ["Ancestral Protectors"],
                        6: ["Spirit Shield"],
                        10: ["Consult the Spirits"],
                        14: ["Vengeful Ancestors"]
                    }
                },
                "Path of the Storm Herald": {
                    "level_gained": 3,
                    "features": {
                        3: ["Storm Aura"],
                        6: ["Storm Soul"],
                        10: ["Shielding Storm"],
                        14: ["Raging Storm"]
                    }
                },
                "Path of the Zealot": {
                    "level_gained": 3,
                    "features": {
                        3: ["Divine Fury", "Warrior of the Gods"],
                        6: ["Fanatical Focus"],
                        10: ["Zealous Presence"],
                        14: ["Rage Beyond Death"]
                    }
                },
                "Path of the Beast": {
                    "level_gained": 3,
                    "features": {
                        3: ["Form of the Beast"],
                        6: ["Bestial Soul"],
                        10: ["Infectious Fury"],
                        14: ["Call the Hunt"]
                    }
                },
                "Path of Wild Magic": {
                    "level_gained": 3,
                    "features": {
                        3: ["Magic Awareness", "Wild Surge"],
                        6: ["Bolstering Magic"],
                        10: ["Unstable Backlash"],
                        14: ["Controlled Surge"]
                    }
                }
            }
        },

        "Bard": {
            "hit_die": 8,
            "primary_abilities": ["Charisma"],
            "saving_throws": ["Dexterity", "Charisma"],
            "armor_proficiencies": ["Light armor"],
            "weapon_proficiencies": ["Simple weapons", "hand crossbows", "longswords", "rapiers", "shortswords"],
            "skill_choices": 3,
            "skill_list": ["Acrobatics", "Animal Handling", "Arcana", "Athletics", "Deception",
                          "History", "Insight", "Intimidation", "Investigation", "Medicine",
                          "Nature", "Perception", "Performance", "Persuasion", "Religion",
                          "Sleight of Hand", "Stealth", "Survival"],
            "spellcasting": {
                "ability": "Charisma",
                "type": "full_caster",
                "ritual_casting": True
            },
            "subclasses": {
                "College of Lore": {
                    "level_gained": 3,
                    "features": {
                        3: ["Bonus Proficiencies", "Cutting Words"],
                        6: ["Additional Magical Secrets"],
                        14: ["Peerless Skill"]
                    }
                },
                "College of Valor": {
                    "level_gained": 3,
                    "features": {
                        3: ["Bonus Proficiencies", "Combat Inspiration"],
                        6: ["Extra Attack"],
                        14: ["Improved Combat Inspiration"]
                    }
                },
                "College of Glamour": {
                    "level_gained": 3,
                    "features": {
                        3: ["Mantle of Inspiration", "Enthralling Performance"],
                        6: ["Mantle of Majesty"],
                        14: ["Unbreakable Majesty"]
                    }
                },
                "College of Swords": {
                    "level_gained": 3,
                    "features": {
                        3: ["Bonus Proficiencies", "Fighting Style", "Blade Flourish"],
                        6: ["Extra Attack"],
                        14: ["Master's Flourish"]
                    }
                },
                "College of Whispers": {
                    "level_gained": 3,
                    "features": {
                        3: ["Psychic Blades", "Words of Terror"],
                        6: ["Mantle of Whispers"],
                        14: ["Shadow Lore"]
                    }
                },
                "College of Creation": {
                    "level_gained": 3,
                    "features": {
                        3: ["Note of Potential", "Performance of Creation"],
                        6: ["Animating Performance"],
                        14: ["Creative Crescendo"]
                    }
                },
                "College of Eloquence": {
                    "level_gained": 3,
                    "features": {
                        3: ["Silver Tongue", "Unsettling Words"],
                        6: ["Universal Speech"],
                        14: ["Infectious Inspiration"]
                    }
                }
            }
        },

        "Cleric": {
            "hit_die": 8,
            "primary_abilities": ["Wisdom"],
            "saving_throws": ["Wisdom", "Charisma"],
            "armor_proficiencies": ["Light armor", "medium armor", "shields"],
            "weapon_proficiencies": ["Simple weapons"],
            "skill_choices": 2,
            "skill_list": ["History", "Insight", "Medicine", "Persuasion", "Religion"],
            "spellcasting": {
                "ability": "Wisdom",
                "type": "full_caster",
                "ritual_casting": True
            },
            "subclasses": {
                "Knowledge Domain": {
                    "level_gained": 1,
                    "features": {
                        1: ["Blessings of Knowledge"],
                        2: ["Channel Divinity: Knowledge of the Ages"],
                        6: ["Channel Divinity: Read Thoughts"],
                        8: ["Potent Spellcasting"],
                        17: ["Visions of the Past"]
                    }
                },
                "Life Domain": {
                    "level_gained": 1,
                    "features": {
                        1: ["Bonus Proficiency", "Disciple of Life"],
                        2: ["Channel Divinity: Preserve Life"],
                        6: ["Blessed Healer"],
                        8: ["Divine Strike"],
                        17: ["Supreme Healing"]
                    }
                },
                "Light Domain": {
                    "level_gained": 1,
                    "features": {
                        1: ["Bonus Cantrip", "Warding Flare"],
                        2: ["Channel Divinity: Radiance of the Dawn"],
                        6: ["Improved Flare"],
                        8: ["Potent Spellcasting"],
                        17: ["Corona of Light"]
                    }
                },
                "Nature Domain": {
                    "level_gained": 1,
                    "features": {
                        1: ["Acolyte of Nature", "Bonus Proficiency"],
                        2: ["Channel Divinity: Charm Animals and Plants"],
                        6: ["Dampen Elements"],
                        8: ["Divine Strike"],
                        17: ["Master of Nature"]
                    }
                },
                "Tempest Domain": {
                    "level_gained": 1,
                    "features": {
                        1: ["Bonus Proficiencies", "Wrath of the Storm"],
                        2: ["Channel Divinity: Destructive Wrath"],
                        6: ["Thunderbolt Strike"],
                        8: ["Divine Strike"],
                        17: ["Stormborn"]
                    }
                },
                "Trickery Domain": {
                    "level_gained": 1,
                    "features": {
                        1: ["Blessing of the Trickster"],
                        2: ["Channel Divinity: Invoke Duplicity"],
                        6: ["Channel Divinity: Cloak of Shadows"],
                        8: ["Divine Strike"],
                        17: ["Improved Duplicity"]
                    }
                },
                "War Domain": {
                    "level_gained": 1,
                    "features": {
                        1: ["Bonus Proficiencies", "War Priest"],
                        2: ["Channel Divinity: Guided Strike"],
                        6: ["Channel Divinity: War God's Blessing"],
                        8: ["Divine Strike"],
                        17: ["Avatar of Battle"]
                    }
                },
                "Forge Domain": {
                    "level_gained": 1,
                    "features": {
                        1: ["Bonus Proficiencies", "Blessing of the Forge"],
                        2: ["Channel Divinity: Artisan's Blessing"],
                        6: ["Soul of the Forge"],
                        8: ["Divine Strike"],
                        17: ["Saint of Forge and Fire"]
                    }
                },
                "Grave Domain": {
                    "level_gained": 1,
                    "features": {
                        1: ["Circle of Mortality", "Eyes of the Grave"],
                        2: ["Channel Divinity: Path to the Grave"],
                        6: ["Sentinel at Death's Door"],
                        8: ["Potent Spellcasting"],
                        17: ["Keeper of Souls"]
                    }
                },
                "Order Domain": {
                    "level_gained": 1,
                    "features": {
                        1: ["Bonus Proficiencies", "Voice of Authority"],
                        2: ["Channel Divinity: Order's Demand"],
                        6: ["Embodiment of the Law"],
                        8: ["Divine Strike"],
                        17: ["Order's Wrath"]
                    }
                },
                "Peace Domain": {
                    "level_gained": 1,
                    "features": {
                        1: ["Implement of Peace", "Emboldening Bond"],
                        2: ["Channel Divinity: Balm of Peace"],
                        6: ["Protective Bond"],
                        8: ["Potent Spellcasting"],
                        17: ["Expansive Bond"]
                    }
                },
                "Twilight Domain": {
                    "level_gained": 1,
                    "features": {
                        1: ["Bonus Proficiencies", "Eyes of Night", "Vigilant Blessing"],
                        2: ["Channel Divinity: Twilight Sanctuary"],
                        6: ["Steps of Night"],
                        8: ["Divine Strike"],
                        17: ["Twilight Shroud"]
                    }
                }
            }
        },

        "Druid": {
            "hit_die": 8,
            "primary_abilities": ["Wisdom"],
            "saving_throws": ["Intelligence", "Wisdom"],
            "armor_proficiencies": ["Light armor", "medium armor", "shields (nonmetal only)"],
            "weapon_proficiencies": ["Clubs", "daggers", "darts", "javelins", "maces", "quarterstaffs", "scimitars", "sickles", "slings", "spears"],
            "skill_choices": 2,
            "skill_list": ["Arcana", "Animal Handling", "Insight", "Medicine", "Nature", "Perception", "Religion", "Survival"],
            "spellcasting": {
                "ability": "Wisdom",
                "type": "full_caster",
                "ritual_casting": True
            },
            "subclasses": {
                "Circle of the Land": {
                    "level_gained": 2,
                    "features": {
                        2: ["Bonus Cantrip", "Natural Recovery"],
                        3: ["Circle Spells"],
                        6: ["Land's Stride"],
                        10: ["Nature's Ward"],
                        14: ["Nature's Sanctuary"]
                    }
                },
                "Circle of the Moon": {
                    "level_gained": 2,
                    "features": {
                        2: ["Combat Wild Shape", "Circle Forms"],
                        4: ["Ability Score Improvement"],
                        6: ["Primal Strike"],
                        10: ["Elemental Wild Shape"],
                        14: ["Thousand Forms"]
                    }
                },
                "Circle of Dreams": {
                    "level_gained": 2,
                    "features": {
                        2: ["Balm of the Summer Court"],
                        6: ["Hearth of Moonlight and Shadow"],
                        10: ["Hidden Paths"],
                        14: ["Walker in Dreams"]
                    }
                },
                "Circle of the Shepherd": {
                    "level_gained": 2,
                    "features": {
                        2: ["Speech of the Woods", "Spirit Totem"],
                        6: ["Mighty Summoner"],
                        10: ["Guardian Spirit"],
                        14: ["Faithful Summons"]
                    }
                },
                "Circle of Spores": {
                    "level_gained": 2,
                    "features": {
                        2: ["Circle Spells", "Halo of Spores", "Symbiotic Entity"],
                        6: ["Fungal Infestation"],
                        10: ["Spreading Spores"],
                        14: ["Fungal Body"]
                    }
                },
                "Circle of Stars": {
                    "level_gained": 2,
                    "features": {
                        2: ["Star Map", "Starry Form"],
                        6: ["Cosmic Omen"],
                        10: ["Twinkling Constellations"],
                        14: ["Full of Stars"]
                    }
                },
                "Circle of Wildfire": {
                    "level_gained": 2,
                    "features": {
                        2: ["Circle Spells", "Summon Wildfire Spirit"],
                        6: ["Enhanced Bond"],
                        10: ["Cauterizing Flames"],
                        14: ["Blazing Revival"]
                    }
                }
            }
        },

        "Monk": {
            "hit_die": 8,
            "primary_abilities": ["Dexterity", "Wisdom"],
            "saving_throws": ["Strength", "Dexterity"],
            "armor_proficiencies": [],
            "weapon_proficiencies": ["Simple weapons", "shortswords"],
            "skill_choices": 2,
            "skill_list": ["Acrobatics", "Athletics", "History", "Insight", "Religion", "Stealth"],
            "subclasses": {
                "Way of the Open Hand": {
                    "level_gained": 3,
                    "features": {
                        3: ["Open Hand Technique"],
                        6: ["Wholeness of Body"],
                        11: ["Tranquility"],
                        17: ["Quivering Palm"]
                    }
                },
                "Way of Shadow": {
                    "level_gained": 3,
                    "features": {
                        3: ["Shadow Arts"],
                        6: ["Shadow Step"],
                        11: ["Cloak of Shadows"],
                        17: ["Opportunist"]
                    }
                },
                "Way of the Four Elements": {
                    "level_gained": 3,
                    "features": {
                        3: ["Disciple of the Elements"],
                        6: ["Extra Elemental Discipline"],
                        11: ["Extra Elemental Discipline"],
                        17: ["Extra Elemental Discipline"]
                    }
                },
                "Way of the Drunken Master": {
                    "level_gained": 3,
                    "features": {
                        3: ["Bonus Proficiencies", "Drunken Technique"],
                        6: ["Tipsy Sway"],
                        11: ["Drunkard's Luck"],
                        17: ["Intoxicated Frenzy"]
                    }
                },
                "Way of the Kensei": {
                    "level_gained": 3,
                    "features": {
                        3: ["Path of the Kensei"],
                        6: ["One with the Blade"],
                        11: ["Sharpen the Blade"],
                        17: ["Unerring Accuracy"]
                    }
                },
                "Way of the Sun Soul": {
                    "level_gained": 3,
                    "features": {
                        3: ["Radiant Sun Bolt"],
                        6: ["Searing Arc Strike"],
                        11: ["Searing Sunburst"],
                        17: ["Sun Shield"]
                    }
                },
                "Way of Mercy": {
                    "level_gained": 3,
                    "features": {
                        3: ["Implements of Mercy", "Hand of Healing", "Hand of Harm"],
                        6: ["Physician's Touch"],
                        11: ["Flurry of Healing and Harm"],
                        17: ["Hand of Ultimate Mercy"]
                    }
                },
                "Way of the Astral Self": {
                    "level_gained": 3,
                    "features": {
                        3: ["Form of the Astral Self"],
                        6: ["Visage of the Astral Self"],
                        11: ["Body of the Astral Self"],
                        17: ["Awakened Astral Self"]
                    }
                }
            }
        },

        "Paladin": {
            "hit_die": 10,
            "primary_abilities": ["Strength", "Charisma"],
            "saving_throws": ["Wisdom", "Charisma"],
            "armor_proficiencies": ["All armor", "shields"],
            "weapon_proficiencies": ["Simple weapons", "martial weapons"],
            "skill_choices": 2,
            "skill_list": ["Athletics", "Insight", "Intimidation", "Medicine", "Persuasion", "Religion"],
            "spellcasting": {
                "ability": "Charisma",
                "type": "half_caster"
            },
            "subclasses": {
                "Oath of Devotion": {
                    "level_gained": 3,
                    "features": {
                        3: ["Oath Spells", "Channel Divinity"],
                        7: ["Aura of Devotion"],
                        15: ["Purity of Spirit"],
                        20: ["Holy Nimbus"]
                    }
                },
                "Oath of the Ancients": {
                    "level_gained": 3,
                    "features": {
                        3: ["Oath Spells", "Channel Divinity"],
                        7: ["Aura of Warding"],
                        15: ["Undying Sentinel"],
                        20: ["Elder Champion"]
                    }
                },
                "Oath of Vengeance": {
                    "level_gained": 3,
                    "features": {
                        3: ["Oath Spells", "Channel Divinity"],
                        7: ["Relentless Avenger"],
                        15: ["Soul of Vengeance"],
                        20: ["Avenging Angel"]
                    }
                },
                "Oath of Conquest": {
                    "level_gained": 3,
                    "features": {
                        3: ["Oath Spells", "Channel Divinity"],
                        7: ["Aura of Conquest"],
                        15: ["Scornful Rebuke"],
                        20: ["Final Punishment"]
                    }
                },
                "Oath of Redemption": {
                    "level_gained": 3,
                    "features": {
                        3: ["Oath Spells", "Channel Divinity"],
                        7: ["Aura of the Guardian"],
                        15: ["Protective Spirit"],
                        20: ["Emissary of Redemption"]
                    }
                },
                "Oath of Glory": {
                    "level_gained": 3,
                    "features": {
                        3: ["Oath Spells", "Channel Divinity"],
                        7: ["Aura of Alacrity"],
                        15: ["Glorious Defense"],
                        20: ["Living Legend"]
                    }
                },
                "Oath of the Watchers": {
                    "level_gained": 3,
                    "features": {
                        3: ["Oath Spells", "Channel Divinity"],
                        7: ["Aura of the Sentinel"],
                        15: ["Vigilant Rebuke"],
                        20: ["Mortal Bulwark"]
                    }
                },
                "Oathbreaker": {
                    "level_gained": 3,
                    "features": {
                        3: ["Oath Spells", "Channel Divinity"],
                        7: ["Aura of Hate"],
                        15: ["Supernatural Resistance"],
                        20: ["Dread Lord"]
                    }
                }
            }
        },

        "Ranger": {
            "hit_die": 10,
            "primary_abilities": ["Dexterity", "Wisdom"],
            "saving_throws": ["Strength", "Dexterity"],
            "armor_proficiencies": ["Light armor", "medium armor", "shields"],
            "weapon_proficiencies": ["Simple weapons", "martial weapons"],
            "skill_choices": 3,
            "skill_list": ["Animal Handling", "Athletics", "Insight", "Investigation", "Nature", "Perception", "Stealth", "Survival"],
            "spellcasting": {
                "ability": "Wisdom",
                "type": "half_caster"
            },
            "subclasses": {
                "Hunter": {
                    "level_gained": 3,
                    "features": {
                        3: ["Hunter's Prey"],
                        7: ["Defensive Tactics"],
                        11: ["Multiattack"],
                        15: ["Superior Hunter's Defense"]
                    }
                },
                "Beast Master": {
                    "level_gained": 3,
                    "features": {
                        3: ["Ranger's Companion"],
                        7: ["Exceptional Training"],
                        11: ["Bestial Fury"],
                        15: ["Share Spells"]
                    }
                },
                "Gloom Stalker": {
                    "level_gained": 3,
                    "features": {
                        3: ["Gloom Stalker Magic", "Dread Ambusher", "Umbral Sight"],
                        7: ["Iron Mind"],
                        11: ["Stalker's Flurry"],
                        15: ["Shadowy Dodge"]
                    }
                },
                "Horizon Walker": {
                    "level_gained": 3,
                    "features": {
                        3: ["Horizon Walker Magic", "Detect Portal", "Planar Warrior"],
                        7: ["Ethereal Step"],
                        11: ["Distant Strike"],
                        15: ["Spectral Defense"]
                    }
                },
                "Monster Slayer": {
                    "level_gained": 3,
                    "features": {
                        3: ["Monster Slayer Magic", "Hunter's Sense", "Slayer's Prey"],
                        7: ["Supernatural Defense"],
                        11: ["Magic-User's Nemesis"],
                        15: ["Slayer's Counter"]
                    }
                },
                "Fey Wanderer": {
                    "level_gained": 3,
                    "features": {
                        3: ["Fey Wanderer Magic", "Otherworldly Glamour", "Dreadful Strikes"],
                        7: ["Beguiling Twist"],
                        11: ["Fey Reinforcements"],
                        15: ["Misty Wanderer"]
                    }
                },
                "Swarmkeeper": {
                    "level_gained": 3,
                    "features": {
                        3: ["Swarmkeeper Magic", "Gathered Swarm"],
                        7: ["Writhing Tide"],
                        11: ["Mighty Swarm"],
                        15: ["Swarming Dispersal"]
                    }
                }
            }
        },

        "Rogue": {
            "hit_die": 8,
            "primary_abilities": ["Dexterity"],
            "saving_throws": ["Dexterity", "Intelligence"],
            "armor_proficiencies": ["Light armor"],
            "weapon_proficiencies": ["Simple weapons", "hand crossbows", "longswords", "rapiers", "shortswords"],
            "skill_choices": 4,
            "skill_list": ["Acrobatics", "Athletics", "Deception", "Insight", "Intimidation", "Investigation", "Perception", "Performance", "Persuasion", "Sleight of Hand", "Stealth"],
            "subclasses": {
                "Thief": {
                    "level_gained": 3,
                    "features": {
                        3: ["Fast Hands", "Second-Story Work"],
                        9: ["Supreme Sneak"],
                        13: ["Use Magic Device"],
                        17: ["Thief's Reflexes"]
                    }
                },
                "Assassin": {
                    "level_gained": 3,
                    "features": {
                        3: ["Bonus Proficiencies", "Assassinate"],
                        9: ["Infiltration Expertise"],
                        13: ["Impostor"],
                        17: ["Death Strike"]
                    }
                },
                "Arcane Trickster": {
                    "level_gained": 3,
                    "features": {
                        3: ["Spellcasting", "Mage Hand Legerdemain"],
                        9: ["Magical Ambush"],
                        13: ["Versatile Trickster"],
                        17: ["Spell Thief"]
                    },
                    "spellcasting": {
                        "ability": "Intelligence",
                        "type": "third_caster",
                        "spell_list": "Wizard (Enchantment/Illusion focus)"
                    }
                },
                "Inquisitive": {
                    "level_gained": 3,
                    "features": {
                        3: ["Ear for Deceit", "Eye for Detail", "Insightful Fighting"],
                        9: ["Steady Eye"],
                        13: ["Unerring Eye"],
                        17: ["Eye for Weakness"]
                    }
                },
                "Mastermind": {
                    "level_gained": 3,
                    "features": {
                        3: ["Master of Disguise and Forgery", "Master of Tactics"],
                        9: ["Insightful Manipulator"],
                        13: ["Misdirection"],
                        17: ["Soul of Deceit"]
                    }
                },
                "Scout": {
                    "level_gained": 3,
                    "features": {
                        3: ["Skirmisher", "Survivalist"],
                        9: ["Superior Mobility"],
                        13: ["Ambush Master"],
                        17: ["Sudden Strike"]
                    }
                },
                "Swashbuckler": {
                    "level_gained": 3,
                    "features": {
                        3: ["Fancy Footwork", "Rakish Audacity"],
                        9: ["Panache"],
                        13: ["Elegant Maneuver"],
                        17: ["Master Duelist"]
                    }
                },
                "Phantom": {
                    "level_gained": 3,
                    "features": {
                        3: ["Whispers of the Dead", "Wails from the Grave"],
                        9: ["Tokens of the Departed"],
                        13: ["Ghost Walk"],
                        17: ["Death's Friend"]
                    }
                },
                "Soulknife": {
                    "level_gained": 3,
                    "features": {
                        3: ["Psionic Power", "Psychic Blades"],
                        9: ["Soul Blades"],
                        13: ["Psychic Veil"],
                        17: ["Rend Mind"]
                    }
                }
            }
        },

        "Sorcerer": {
            "hit_die": 6,
            "primary_abilities": ["Charisma"],
            "saving_throws": ["Constitution", "Charisma"],
            "armor_proficiencies": [],
            "weapon_proficiencies": ["Daggers", "darts", "slings", "quarterstaffs", "light crossbows"],
            "skill_choices": 2,
            "skill_list": ["Arcana", "Deception", "Insight", "Intimidation", "Persuasion", "Religion"],
            "spellcasting": {
                "ability": "Charisma",
                "type": "full_caster"
            },
            "subclasses": {
                "Draconic Bloodline": {
                    "level_gained": 1,
                    "features": {
                        1: ["Dragon Ancestor", "Draconic Resilience"],
                        6: ["Elemental Affinity"],
                        14: ["Dragon Wings"],
                        18: ["Draconic Presence"]
                    }
                },
                "Wild Magic": {
                    "level_gained": 1,
                    "features": {
                        1: ["Wild Magic Surge", "Tides of Chaos"],
                        6: ["Bend Luck"],
                        14: ["Controlled Chaos"],
                        18: ["Spell Bombardment"]
                    }
                },
                "Divine Soul": {
                    "level_gained": 1,
                    "features": {
                        1: ["Divine Magic", "Favored by the Gods"],
                        6: ["Empowered Healing"],
                        14: ["Otherworldly Wings"],
                        18: ["Unearthly Recovery"]
                    }
                },
                "Shadow Magic": {
                    "level_gained": 1,
                    "features": {
                        1: ["Eyes of the Dark", "Strength of the Grave"],
                        6: ["Hound of Ill Omen"],
                        14: ["Shadow Walk"],
                        18: ["Umbral Form"]
                    }
                },
                "Storm Sorcery": {
                    "level_gained": 1,
                    "features": {
                        1: ["Wind Speaker", "Tempestuous Magic"],
                        6: ["Heart of the Storm", "Storm Guide"],
                        14: ["Storm's Fury"],
                        18: ["Wind Soul"]
                    }
                },
                "Aberrant Mind": {
                    "level_gained": 1,
                    "features": {
                        1: ["Telepathic Speech", "Psionic Spells"],
                        6: ["Psionic Sorcery", "Psychic Defenses"],
                        14: ["Psionic Sorcery"],
                        18: ["Warping Implosion"]
                    }
                },
                "Clockwork Soul": {
                    "level_gained": 1,
                    "features": {
                        1: ["Clockwork Magic", "Restore Balance"],
                        6: ["Bastion of Law"],
                        14: ["Trance of Order"],
                        18: ["Clockwork Cavalcade"]
                    }
                }
            }
        },

        "Warlock": {
            "hit_die": 8,
            "primary_abilities": ["Charisma"],
            "saving_throws": ["Wisdom", "Charisma"],
            "armor_proficiencies": ["Light armor"],
            "weapon_proficiencies": ["Simple weapons"],
            "skill_choices": 2,
            "skill_list": ["Arcana", "Deception", "History", "Intimidation", "Investigation", "Nature", "Religion"],
            "spellcasting": {
                "ability": "Charisma",
                "type": "pact_magic"
            },
            "subclasses": {
                "The Archfey": {
                    "level_gained": 1,
                    "features": {
                        1: ["Expanded Spell List", "Fey Presence"],
                        6: ["Misty Escape"],
                        10: ["Beguiling Defenses"],
                        14: ["Dark Delirium"]
                    }
                },
                "The Fiend": {
                    "level_gained": 1,
                    "features": {
                        1: ["Expanded Spell List", "Dark One's Blessing"],
                        6: ["Dark One's Own Luck"],
                        10: ["Fiendish Resilience"],
                        14: ["Hurl Through Hell"]
                    }
                },
                "The Great Old One": {
                    "level_gained": 1,
                    "features": {
                        1: ["Expanded Spell List", "Telepathic Communication"],
                        6: ["Entropic Ward"],
                        10: ["Thought Shield"],
                        14: ["Create Thrall"]
                    }
                },
                "The Celestial": {
                    "level_gained": 1,
                    "features": {
                        1: ["Expanded Spell List", "Healing Light"],
                        6: ["Radiant Soul"],
                        10: ["Celestial Resilience"],
                        14: ["Searing Vengeance"]
                    }
                },
                "The Hexblade": {
                    "level_gained": 1,
                    "features": {
                        1: ["Expanded Spell List", "Hexblade's Curse", "Hex Warrior"],
                        6: ["Accursed Specter"],
                        10: ["Armor of Hexes"],
                        14: ["Master of Hexes"]
                    }
                },
                "The Fathomless": {
                    "level_gained": 1,
                    "features": {
                        1: ["Expanded Spell List", "Tentacle of the Deeps"],
                        6: ["Gift of the Sea"],
                        10: ["Oceanic Soul"],
                        14: ["Grasping Tentacles"]
                    }
                },
                "The Genie": {
                    "level_gained": 1,
                    "features": {
                        1: ["Expanded Spell List", "Genie's Vessel"],
                        6: ["Elemental Gift"],
                        10: ["Sanctuary Vessel"],
                        14: ["Limited Wish"]
                    }
                },
                "The Undead": {
                    "level_gained": 1,
                    "features": {
                        1: ["Expanded Spell List", "Form of Dread"],
                        6: ["Grave Touched"],
                        10: ["Necrotic Husk"],
                        14: ["Spirit Projection"]
                    }
                }
            }
        },

        "Artificer": {
            "hit_die": 8,
            "primary_abilities": ["Intelligence"],
            "saving_throws": ["Constitution", "Intelligence"],
            "armor_proficiencies": ["Light armor", "medium armor", "shields"],
            "weapon_proficiencies": ["Simple weapons", "firearms"],
            "skill_choices": 2,
            "skill_list": ["Arcana", "History", "Investigation", "Medicine", "Nature", "Perception", "Sleight of Hand"],
            "spellcasting": {
                "ability": "Intelligence",
                "type": "half_caster",
                "ritual_casting": True
            },
            "subclasses": {
                "Alchemist": {
                    "level_gained": 3,
                    "features": {
                        3: ["Tool Expertise", "Alchemist Spells", "Experimental Elixir"],
                        5: ["Alchemical Savant"],
                        9: ["Restorative Reagents"],
                        15: ["Chemical Mastery"]
                    }
                },
                "Armorer": {
                    "level_gained": 3,
                    "features": {
                        3: ["Tools of the Trade", "Armorer Spells", "Arcane Armor", "Armor Model"],
                        5: ["Extra Attack"],
                        9: ["Armor Modifications"],
                        15: ["Perfected Armor"]
                    }
                },
                "Artillerist": {
                    "level_gained": 3,
                    "features": {
                        3: ["Tool Expertise", "Artillerist Spells", "Eldritch Cannons"],
                        5: ["Arcane Firearm"],
                        9: ["Explosive Cannon"],
                        15: ["Fortified Position"]
                    }
                },
                "Battle Smith": {
                    "level_gained": 3,
                    "features": {
                        3: ["Tool Expertise", "Battle Smith Spells", "Battle Ready", "Steel Defender"],
                        5: ["Extra Attack"],
                        9: ["Arcane Jolt"],
                        15: ["Improved Defender"]
                    }
                }
            }
        }
    }

class FeatSystem:
    """Complete feat system with prerequisites and benefits"""

    FEATS = {
        "Alert": {
            "prerequisites": [],
            "benefits": [
                "+5 bonus to initiative",
                "Cannot be surprised while conscious",
                "Hidden creatures don't gain advantage on attacks"
            ],
            "ability_increase": None
        },

        "Athlete": {
            "prerequisites": [],
            "benefits": [
                "Standing up costs only 5 feet of movement",
                "Climbing doesn't cost extra movement",
                "Running long jump distance increases by feet equal to Strength modifier"
            ],
            "ability_increase": ["Strength", "Dexterity"]  # Choose one
        },

        "Great Weapon Master": {
            "prerequisites": [],
            "benefits": [
                "Bonus action attack when you score critical or reduce to 0 HP",
                "Take -5 to attack for +10 damage with heavy melee weapons"
            ],
            "ability_increase": None
        },

        "Sharpshooter": {
            "prerequisites": [],
            "benefits": [
                "Attacking at long range doesn't impose disadvantage",
                "Ranged attacks ignore half and three-quarters cover",
                "Take -5 to attack for +10 damage with ranged weapons"
            ],
            "ability_increase": None
        },

        "War Caster": {
            "prerequisites": ["Ability to cast at least one spell"],
            "benefits": [
                "Advantage on Constitution saves to maintain concentration",
                "Perform somatic components with weapons/shield in hands",
                "Cast a spell as opportunity attack instead of melee attack"
            ],
            "ability_increase": None
        },

        # Racial feats
        "Elven Accuracy": {
            "prerequisites": ["Elf or half-elf"],
            "benefits": [
                "Reroll one attack die when you have advantage (Dex, Int, Wis, or Cha attacks)"
            ],
            "ability_increase": ["Dexterity", "Intelligence", "Wisdom", "Charisma"]
        },

        "Dwarven Fortitude": {
            "prerequisites": ["Dwarf"],
            "benefits": [
                "When you take Dodge action, spend Hit Die to heal"
            ],
            "ability_increase": ["Constitution"]
        },

        # Player's Handbook Feats
        "Actor": {
            "prerequisites": [],
            "benefits": [
                "Advantage on Deception and Performance checks when mimicking",
                "Mimic speech of another person or creature sounds"
            ],
            "ability_increase": ["Charisma"]
        },

        "Charger": {
            "prerequisites": [],
            "benefits": [
                "Dash and make melee attack or shove as bonus action",
                "+5 damage if moved at least 10 feet in straight line"
            ],
            "ability_increase": None
        },

        "Crossbow Expert": {
            "prerequisites": [],
            "benefits": [
                "Ignore loading property of crossbows",
                "No disadvantage for ranged attacks in melee",
                "Bonus action hand crossbow attack when using one-handed weapon"
            ],
            "ability_increase": None
        },

        "Defensive Duelist": {
            "prerequisites": ["Dexterity 13+"],
            "benefits": [
                "Add proficiency bonus to AC as reaction when wielding finesse weapon"
            ],
            "ability_increase": None
        },

        "Dual Wielder": {
            "prerequisites": [],
            "benefits": [
                "AC +1 when wielding separate melee weapons in each hand",
                "Two-weapon fighting with non-light weapons",
                "Draw/stow two weapons when you would normally draw/stow one"
            ],
            "ability_increase": None
        },

        "Dungeon Delver": {
            "prerequisites": [],
            "benefits": [
                "Advantage on Perception and Investigation for secret doors",
                "Advantage on saves vs traps",
                "Resistance to trap damage",
                "Move at normal speed while searching for traps"
            ],
            "ability_increase": None
        },

        "Durable": {
            "prerequisites": [],
            "benefits": [
                "Regain minimum hit points equal to 2×Constitution modifier when using Hit Dice"
            ],
            "ability_increase": ["Constitution"]
        },

        "Elemental Adept": {
            "prerequisites": ["Ability to cast at least one spell"],
            "benefits": [
                "Choose acid, cold, fire, lightning, or thunder",
                "Spells ignore resistance to chosen damage type",
                "Treat 1s on damage dice as 2s for chosen type"
            ],
            "ability_increase": None
        },

        "Fey Touched": {
            "prerequisites": [],
            "benefits": [
                "Learn misty step and one 1st-level divination/enchantment spell",
                "Cast each once per long rest without expending spell slot",
                "Can also cast using spell slots"
            ],
            "ability_increase": ["Intelligence", "Wisdom", "Charisma"]
        },

        "Grappler": {
            "prerequisites": ["Strength 13+"],
            "benefits": [
                "Advantage on attacks against grappled creatures",
                "Restrain grappled creature (both restrained until grapple ends)"
            ],
            "ability_increase": None
        },

        "Great Weapon Master": {
            "prerequisites": [],
            "benefits": [
                "Bonus action attack when you score critical or reduce to 0 HP",
                "Take -5 to attack for +10 damage with heavy melee weapons"
            ],
            "ability_increase": None
        },

        "Healer": {
            "prerequisites": [],
            "benefits": [
                "Stabilize with healer's kit restores 1 HP",
                "Heal for 1d4+4+level HP once per short/long rest per creature"
            ],
            "ability_increase": None
        },

        "Heavy Armor Master": {
            "prerequisites": ["Proficiency with heavy armor"],
            "benefits": [
                "Reduce bludgeoning, piercing, slashing damage by 3 from nonmagical weapons"
            ],
            "ability_increase": ["Strength"]
        },

        "Inspiring Leader": {
            "prerequisites": ["Charisma 13+"],
            "benefits": [
                "Give temporary HP equal to level + Charisma modifier to 6 creatures"
            ],
            "ability_increase": None
        },

        "Keen Mind": {
            "prerequisites": [],
            "benefits": [
                "Always know which way is north and hours until sunrise/sunset",
                "Recall anything seen/heard within past month"
            ],
            "ability_increase": ["Intelligence"]
        },

        "Linguist": {
            "prerequisites": [],
            "benefits": [
                "Learn three languages",
                "Create written ciphers (DC = Intelligence score + proficiency bonus)"
            ],
            "ability_increase": ["Intelligence"]
        },

        "Lucky": {
            "prerequisites": [],
            "benefits": [
                "3 luck points per long rest",
                "Spend to reroll attack, ability check, or saving throw",
                "Force reroll of attack made against you"
            ],
            "ability_increase": None
        },

        "Mage Slayer": {
            "prerequisites": [],
            "benefits": [
                "Opportunity attack when creature casts spell within 5 feet",
                "Advantage on saves vs spells cast within 5 feet",
                "Concentration saves have disadvantage when damaged by your attacks"
            ],
            "ability_increase": None
        },

        "Magic Initiate": {
            "prerequisites": [],
            "benefits": [
                "Choose class: learn 2 cantrips and one 1st-level spell",
                "Cast 1st-level spell once per long rest",
                "Can also cast using spell slots if of appropriate class"
            ],
            "ability_increase": None
        },

        "Martial Adept": {
            "prerequisites": [],
            "benefits": [
                "Learn two maneuvers from Battle Master archetype",
                "Gain one superiority die (d6)"
            ],
            "ability_increase": None
        },

        "Medium Armor Master": {
            "prerequisites": ["Proficiency with medium armor"],
            "benefits": [
                "Medium armor doesn't impose disadvantage on stealth",
                "Max Dex bonus in medium armor increases to 3"
            ],
            "ability_increase": None
        },

        "Mobile": {
            "prerequisites": [],
            "benefits": [
                "Speed increases by 10 feet",
                "Dash in difficult terrain doesn't cost extra movement",
                "No opportunity attacks from creatures you've attacked this turn"
            ],
            "ability_increase": None
        },

        "Moderately Armored": {
            "prerequisites": ["Proficiency with light armor"],
            "benefits": [
                "Proficiency with medium armor and shields"
            ],
            "ability_increase": ["Strength", "Dexterity"]
        },

        "Mounted Combatant": {
            "prerequisites": [],
            "benefits": [
                "Advantage on attacks vs unmounted creatures smaller than mount",
                "Force attacks vs mount to target you instead",
                "Mount takes no damage on successful Dex save (half damage on failure)"
            ],
            "ability_increase": None
        },

        "Observant": {
            "prerequisites": [],
            "benefits": [
                "Read lips if you know language and can see speaker's mouth",
                "+5 bonus to passive Perception and Investigation"
            ],
            "ability_increase": ["Intelligence", "Wisdom"]
        },

        "Polearm Master": {
            "prerequisites": [],
            "benefits": [
                "Bonus action attack with opposite end (d4) when using glaive, halberd, pike, or quarterstaff",
                "Opportunity attacks when creatures enter your reach with these weapons"
            ],
            "ability_increase": None
        },

        "Resilient": {
            "prerequisites": [],
            "benefits": [
                "Choose ability score",
                "Gain proficiency in saves using chosen ability"
            ],
            "ability_increase": ["Strength", "Dexterity", "Constitution", "Intelligence", "Wisdom", "Charisma"]
        },

        "Ritual Caster": {
            "prerequisites": ["Intelligence or Wisdom 13+"],
            "benefits": [
                "Choose class with ritual casting",
                "Learn two 1st-level ritual spells from that class",
                "Find and copy ritual spells into ritual book"
            ],
            "ability_increase": None
        },

        "Savage Attacker": {
            "prerequisites": [],
            "benefits": [
                "Reroll weapon damage dice once per turn, use either result"
            ],
            "ability_increase": None
        },

        "Sentinel": {
            "prerequisites": [],
            "benefits": [
                "Opportunity attacks reduce speed to 0",
                "Opportunity attacks even when target Disengages",
                "Attack creatures within 5 feet that attack someone else"
            ],
            "ability_increase": None
        },

        "Shadow Touched": {
            "prerequisites": [],
            "benefits": [
                "Learn invisibility and one 1st-level necromancy/illusion spell",
                "Cast each once per long rest without expending spell slot",
                "Can also cast using spell slots"
            ],
            "ability_increase": ["Intelligence", "Wisdom", "Charisma"]
        },

        "Shield Master": {
            "prerequisites": [],
            "benefits": [
                "Bonus action shove with shield after Attack action",
                "Add shield AC to Dex saves vs single target",
                "No damage on successful Dex save vs spells (half damage on failure)"
            ],
            "ability_increase": None
        },

        "Skilled": {
            "prerequisites": [],
            "benefits": [
                "Gain proficiency in any combination of three skills or tools"
            ],
            "ability_increase": None
        },

        "Skulker": {
            "prerequisites": ["Dexterity 13+"],
            "benefits": [
                "Hide when lightly obscured",
                "Dim light doesn't impose disadvantage on Perception",
                "Missing with ranged attack doesn't reveal position"
            ],
            "ability_increase": None
        },

        "Spell Sniper": {
            "prerequisites": ["Ability to cast at least one spell"],
            "benefits": [
                "Double range of spells that require attack roll",
                "Ignore half and three-quarters cover for spell attacks",
                "Learn one cantrip that requires attack roll"
            ],
            "ability_increase": None
        },

        "Tavern Brawler": {
            "prerequisites": [],
            "benefits": [
                "Proficiency with improvised weapons",
                "Improvised weapons deal 1d4 damage",
                "Grapple as bonus action when hitting with unarmed or improvised weapon"
            ],
            "ability_increase": ["Strength", "Constitution"]
        },

        "Telekinetic": {
            "prerequisites": [],
            "benefits": [
                "Learn mage hand cantrip (invisible hand, 30-foot range)",
                "Bonus action to shove creature within 30 feet (Strength save)",
                "No opportunity attacks when pushed"
            ],
            "ability_increase": ["Intelligence", "Wisdom", "Charisma"]
        },

        "Telepathic": {
            "prerequisites": [],
            "benefits": [
                "Telepathically communicate with creature within 60 feet (1 minute)",
                "Cast detect thoughts once per long rest without spell slot",
                "Can also cast using spell slots"
            ],
            "ability_increase": ["Intelligence", "Wisdom", "Charisma"]
        },

        "Tough": {
            "prerequisites": [],
            "benefits": [
                "Hit point maximum increases by 2 × level"
            ],
            "ability_increase": None
        },

        "War Caster": {
            "prerequisites": ["Ability to cast at least one spell"],
            "benefits": [
                "Advantage on Constitution saves to maintain concentration",
                "Perform somatic components with weapons/shield in hands",
                "Cast a spell as opportunity attack instead of melee attack"
            ],
            "ability_increase": None
        },

        "Weapon Master": {
            "prerequisites": [],
            "benefits": [
                "Proficiency with four weapons of your choice"
            ],
            "ability_increase": ["Strength", "Dexterity"]
        },

        # Additional Racial Feats
        "Dragon Fear": {
            "prerequisites": ["Dragonborn"],
            "benefits": [
                "Roar instead of breath weapon to frighten creatures within 30 feet"
            ],
            "ability_increase": ["Strength", "Constitution", "Charisma"]
        },

        "Dragon Hide": {
            "prerequisites": ["Dragonborn"],
            "benefits": [
                "Natural armor: 13 + Dex modifier when not wearing armor",
                "Retractable claws deal 1d4 + Str slashing damage"
            ],
            "ability_increase": ["Strength", "Constitution", "Charisma"]
        },

        "Fey Teleportation": {
            "prerequisites": ["Elf (high)"],
            "benefits": [
                "Learn misty step, cast once per short/long rest",
                "Learn Sylvan language"
            ],
            "ability_increase": ["Intelligence", "Charisma"]
        },

        "Flames of Phlegethos": {
            "prerequisites": ["Tiefling"],
            "benefits": [
                "Reroll 1s on fire damage dice",
                "When casting fire spell, sheath in flames until end of next turn"
            ],
            "ability_increase": ["Intelligence", "Charisma"]
        },

        "Infernal Constitution": {
            "prerequisites": ["Tiefling"],
            "benefits": [
                "Resistance to cold and poison damage",
                "Advantage on saves vs being poisoned"
            ],
            "ability_increase": ["Constitution"]
        },

        "Orcish Fury": {
            "prerequisites": ["Half-orc"],
            "benefits": [
                "Extra damage die when using Savage Attacks",
                "Bonus action attack when using Relentless Endurance"
            ],
            "ability_increase": ["Strength", "Constitution"]
        },

        "Prodigy": {
            "prerequisites": ["Half-elf, half-orc, or human"],
            "benefits": [
                "One skill proficiency",
                "One language or tool proficiency",
                "Expertise with one skill proficiency"
            ],
            "ability_increase": ["Strength", "Dexterity", "Constitution", "Intelligence", "Wisdom", "Charisma"]
        },

        "Second Chance": {
            "prerequisites": ["Halfling"],
            "benefits": [
                "Force attacker to reroll when they hit you (3/long rest)"
            ],
            "ability_increase": ["Dexterity", "Constitution", "Charisma"]
        },

        "Squat Nimbleness": {
            "prerequisites": ["Dwarf or small race"],
            "benefits": [
                "Speed increases by 5 feet",
                "Proficiency in Acrobatics or Athletics",
                "Advantage on checks to escape grapples"
            ],
            "ability_increase": ["Strength", "Dexterity"]
        },

        # Additional Core PHB Feats
        "Heavily Armored": {
            "prerequisites": ["Proficiency with medium armor"],
            "benefits": [
                "Proficiency with heavy armor"
            ],
            "ability_increase": ["Strength"]
        },

        "Lightly Armored": {
            "prerequisites": [],
            "benefits": [
                "Proficiency with light armor"
            ],
            "ability_increase": ["Strength", "Dexterity"]
        },

        # Tasha's Cauldron of Everything Feats
        "Artificer Initiate": {
            "prerequisites": [],
            "benefits": [
                "Learn two cantrips from artificer spell list",
                "Learn one 1st-level artificer spell",
                "Cast 1st-level spell once per long rest",
                "Can cast using spell slots if you're an artificer"
            ],
            "ability_increase": None
        },

        "Chef": {
            "prerequisites": [],
            "benefits": [
                "Proficiency with cook's utensils if not already proficient",
                "Short rest cooking: heal 1d8 to number of creatures equal to proficiency bonus",
                "Create treats during long rest: proficiency bonus + 1 treats that give temp HP"
            ],
            "ability_increase": ["Constitution", "Wisdom"]
        },

        "Crusher": {
            "prerequisites": [],
            "benefits": [
                "Once per turn, move Large or smaller creature 5 feet when dealing bludgeoning damage",
                "Critical hits with bludgeoning give advantage to attacks against target until start of next turn"
            ],
            "ability_increase": ["Strength", "Constitution"]
        },

        "Eldritch Adept": {
            "prerequisites": ["Spellcasting or Pact Magic feature"],
            "benefits": [
                "Learn one Eldritch Invocation of your choice from warlock",
                "If invocation has prerequisite, you can choose it only if you're a warlock and meet prerequisite"
            ],
            "ability_increase": None
        },

        "Fighting Initiate": {
            "prerequisites": ["Proficiency with a martial weapon"],
            "benefits": [
                "Learn one Fighting Style option from fighter class",
                "Cannot take same Fighting Style more than once"
            ],
            "ability_increase": None
        },

        "Gunner": {
            "prerequisites": [],
            "benefits": [
                "Proficiency with firearms",
                "Ignore loading property of firearms",
                "No disadvantage for ranged attacks while within 5 feet of hostile creature"
            ],
            "ability_increase": ["Dexterity"]
        },

        "Metamagic Adept": {
            "prerequisites": ["Spellcasting or Pact Magic feature"],
            "benefits": [
                "Learn two Metamagic options from sorcerer class",
                "Gain 2 sorcery points to spend on Metamagic",
                "Regain sorcery points on long rest"
            ],
            "ability_increase": None
        },

        "Piercer": {
            "prerequisites": [],
            "benefits": [
                "Once per turn, reroll one damage die when dealing piercing damage",
                "Critical hits with piercing add one extra damage die"
            ],
            "ability_increase": ["Strength", "Dexterity"]
        },

        "Poisoner": {
            "prerequisites": [],
            "benefits": [
                "Proficiency with poisoner's kit",
                "Ignore resistance to poison damage",
                "Coat weapons: bonus action, next hit deals extra 2d8 poison, target saves vs poison"
            ],
            "ability_increase": ["Dexterity", "Intelligence"]
        },

        "Shadow Touched": {
            "prerequisites": [],
            "benefits": [
                "Learn invisibility and one 1st-level necromancy or illusion spell",
                "Cast each once per long rest without expending spell slot",
                "Can also cast using spell slots"
            ],
            "ability_increase": ["Intelligence", "Wisdom", "Charisma"]
        },

        "Shield Training": {
            "prerequisites": [],
            "benefits": [
                "Proficiency with shields",
                "If using only a shield (no weapon), can use shield as weapon (1d4 bludgeoning)"
            ],
            "ability_increase": ["Strength", "Constitution"]
        },

        "Skill Expert": {
            "prerequisites": [],
            "benefits": [
                "Proficiency in one skill of your choice",
                "Expertise with one skill you're proficient with"
            ],
            "ability_increase": ["Strength", "Dexterity", "Constitution", "Intelligence", "Wisdom", "Charisma"]
        },

        "Slasher": {
            "prerequisites": [],
            "benefits": [
                "Once per turn, reduce target's speed by 10 feet when dealing slashing damage",
                "Critical hits with slashing impose disadvantage on target's attack rolls"
            ],
            "ability_increase": ["Strength", "Dexterity"]
        },

        # Xanathar's Guide Feats
        "Bountiful Luck": {
            "prerequisites": ["Halfling"],
            "benefits": [
                "When ally within 30 feet rolls a 1 on d20, use reaction to reroll (3/long rest)"
            ],
            "ability_increase": None
        },

        "Fade Away": {
            "prerequisites": ["Gnome"],
            "benefits": [
                "When you take damage, use reaction to become invisible until end of next turn or until you attack"
            ],
            "ability_increase": ["Dexterity", "Intelligence"]
        },

        "Wood Elf Magic": {
            "prerequisites": ["Elf (wood)"],
            "benefits": [
                "Learn one druid cantrip",
                "Learn longstrider and pass without trace spells",
                "Cast each spell once per long rest without expending spell slot"
            ],
            "ability_increase": ["Wisdom"]
        },

        # Fizban's Treasury of Dragons Feats
        "Gift of the Chromatic Dragon": {
            "prerequisites": [],
            "benefits": [
                "Bonus action: infuse weapon/20 ammunition with acid, cold, fire, lightning, or poison for 1 minute",
                "Reaction when taking acid, cold, fire, lightning, or poison damage: gain resistance until start of next turn"
            ],
            "ability_increase": None
        },

        "Gift of the Metallic Dragon": {
            "prerequisites": [],
            "benefits": [
                "Learn cure wounds spell, cast once per long rest at 1st level",
                "Protective wings: reaction when ally within 5 feet takes damage, grant +1 AC"
            ],
            "ability_increase": None
        },

        # Acquisitions Incorporated Feats
        "Aberrant Dragonmark": {
            "prerequisites": ["No existing dragonmark"],
            "benefits": [
                "Learn one sorcerer cantrip",
                "Learn one 1st-level sorcerer spell, cast once per long rest",
                "Can cast spell using sorcerer spell slots if you have them"
            ],
            "ability_increase": ["Constitution"]
        },

        # Mordenkainen's Tome of Foes Feats
        "Svirfneblin Magic": {
            "prerequisites": ["Gnome (deep)"],
            "benefits": [
                "Learn nondetection spell, always active on you",
                "Learn blindness/deafness, blur, and disguise self, each once per long rest"
            ],
            "ability_increase": None
        },

        # Ghosts of Saltmarsh Feats
        "Revenant Blade": {
            "prerequisites": ["Elf"],
            "benefits": [
                "Double-bladed scimitar gains finesse property",
                "Defensive: +1 AC while wielding double-bladed scimitar with no other weapons"
            ],
            "ability_increase": ["Strength", "Dexterity"]
        },

        # Strixhaven Feats
        "Strixhaven Initiate": {
            "prerequisites": [],
            "benefits": [
                "Choose college: Lorehold, Prismari, Quandrix, Silverquill, or Witherbloom",
                "Learn two cantrips and one 1st-level spell from college's spell list",
                "Cast 1st-level spell once per long rest"
            ],
            "ability_increase": None
        },

        "Strixhaven Mascot": {
            "prerequisites": ["4th level", "Strixhaven Initiate feat"],
            "benefits": [
                "Learn one spell from your college's expanded spell list",
                "Cast it once per long rest without expending spell slot"
            ],
            "ability_increase": None
        },

        # Van Richten's Guide to Ravenloft Feats
        "Dark Gift": {
            "prerequisites": ["DM permission"],
            "benefits": [
                "Varies based on specific dark gift received",
                "Powerful supernatural ability with potential drawbacks"
            ],
            "ability_increase": None
        },

        # Spelljammer Feats
        "Spelljammer Pilot": {
            "prerequisites": ["Proficiency with vehicles (space)"],
            "benefits": [
                "Double proficiency bonus for checks with spelljamming helms",
                "Advantage on saving throws while piloting a spelljammer"
            ],
            "ability_increase": None
        },

        # Additional Variant/Optional Feats
        "Great Weapon Fighting": {
            "prerequisites": ["Proficiency with martial weapons"],
            "benefits": [
                "Reroll 1s and 2s on damage dice for two-handed weapons"
            ],
            "ability_increase": None
        },

        "Two-Weapon Fighting": {
            "prerequisites": [],
            "benefits": [
                "Add ability modifier to damage of second attack when two-weapon fighting"
            ],
            "ability_increase": None
        },

        "Archery": {
            "prerequisites": ["Proficiency with martial weapons"],
            "benefits": [
                "+2 bonus to attack rolls with ranged weapons"
            ],
            "ability_increase": None
        },

        "Defense": {
            "prerequisites": ["Proficiency with armor"],
            "benefits": [
                "+1 bonus to AC while wearing armor"
            ],
            "ability_increase": None
        },

        "Dueling": {
            "prerequisites": [],
            "benefits": [
                "+2 damage when wielding one-handed weapon with no other weapons"
            ],
            "ability_increase": None
        },

        "Protection": {
            "prerequisites": ["Proficiency with shields"],
            "benefits": [
                "Reaction to impose disadvantage on attack against ally within 5 feet"
            ],
            "ability_increase": None
        }
    }

class DetailedCharacterCreator:
    """Enhanced character creator with comprehensive D&D 5e rule support"""

    def __init__(self):
        self.races = CharacterRace.RACES
        self.classes = CharacterClass.CLASSES
        self.feats = FeatSystem.FEATS

    def get_race_options(self) -> Dict[str, List[str]]:
        """Get all race and subrace options"""
        race_options = {}
        for race_name, race_data in self.races.items():
            if "variants" in race_data:
                race_options[race_name] = list(race_data["variants"].keys())
            else:
                race_options[race_name] = [race_name]
        return race_options

    def get_class_options(self) -> Dict[str, List[str]]:
        """Get all class and subclass options"""
        class_options = {}
        for class_name, class_data in self.classes.items():
            if "subclasses" in class_data:
                class_options[class_name] = list(class_data["subclasses"].keys())
            else:
                class_options[class_name] = [class_name]
        return class_options

    def get_ability_score_methods(self) -> List[str]:
        """Get ability score generation methods"""
        return [
            "Standard Array (15, 14, 13, 12, 10, 8)",
            "Point Buy (27 points)",
            "Roll 4d6 drop lowest (6 times)",
            "Manual Entry"
        ]

    def calculate_ability_modifiers(self, abilities: Dict[str, int]) -> Dict[str, int]:
        """Calculate ability modifiers from scores"""
        modifiers = {}
        for ability, score in abilities.items():
            modifiers[ability] = (score - 10) // 2
        return modifiers

    def apply_racial_bonuses(self, base_abilities: Dict[str, int], race: str, variant: str) -> Dict[str, int]:
        """Apply racial ability score increases"""
        if race not in self.races:
            return base_abilities

        race_data = self.races[race]
        if "variants" not in race_data or variant not in race_data["variants"]:
            return base_abilities

        variant_data = race_data["variants"][variant]
        modified_abilities = base_abilities.copy()

        for increase in variant_data.ability_increases:
            ability = increase.ability.lower()
            if ability in modified_abilities:
                modified_abilities[ability] += increase.amount

        return modified_abilities

    def get_racial_traits(self, race: str, variant: str) -> List[RacialTrait]:
        """Get all racial traits for a race/variant"""
        traits = []

        if race not in self.races:
            return traits

        race_data = self.races[race]

        # Add base racial traits
        if "traits" in race_data:
            traits.extend(race_data["traits"])

        # Add variant-specific traits
        if "variants" in race_data and variant in race_data["variants"]:
            variant_data = race_data["variants"][variant]
            traits.extend(variant_data.traits)

        return traits

    def get_class_features(self, class_name: str, level: int, subclass: str = None) -> List[str]:
        """Get class features for a given level"""
        if class_name not in self.classes:
            return []

        class_data = self.classes[class_name]
        features = []

        # Add base class features for level
        # This would need to be expanded with full feature tables

        # Add subclass features
        if subclass and "subclasses" in class_data and subclass in class_data["subclasses"]:
            subclass_data = class_data["subclasses"][subclass]
            if "features" in subclass_data:
                for feature_level, feature_list in subclass_data["features"].items():
                    if feature_level <= level:
                        features.extend(feature_list)

        return features

    def calculate_hit_points(self, class_name: str, level: int, constitution_modifier: int, tough_feat: bool = False) -> Tuple[int, int]:
        """Calculate hit points (average and max possible)"""
        if class_name not in self.classes:
            return 1, 1

        hit_die = self.classes[class_name]["hit_die"]

        # First level gets max HP
        base_hp = hit_die + constitution_modifier

        # Additional levels (average method)
        if level > 1:
            additional_levels = level - 1
            average_per_level = (hit_die + 1) / 2  # Average of hit die
            additional_hp = int(additional_levels * (average_per_level + constitution_modifier))
            base_hp += additional_hp

        # Tough feat adds 2 HP per level
        if tough_feat:
            base_hp += 2 * level

        # Hill dwarf bonus (would need racial trait checking)
        # +1 HP per level for hill dwarves

        max_possible = hit_die + (level - 1) * hit_die + (constitution_modifier * level)
        if tough_feat:
            max_possible += 2 * level

        return max(1, base_hp), max(1, max_possible)

    def calculate_armor_class(self, dexterity_modifier: int, armor_type: str = "none", shield: bool = False) -> int:
        """Calculate armor class based on equipment"""
        base_ac = 10

        armor_values = {
            "none": 10,
            "leather": 11,
            "studded_leather": 12,
            "chain_shirt": 13,
            "scale_mail": 14,
            "chain_mail": 16,
            "splint": 17,
            "plate": 18
        }

        if armor_type in ["none", "leather", "studded_leather"]:
            # Light armor - full dex bonus
            ac = armor_values.get(armor_type, 10) + dexterity_modifier
        elif armor_type in ["chain_shirt", "scale_mail"]:
            # Medium armor - max +2 dex bonus
            ac = armor_values.get(armor_type, 10) + min(2, dexterity_modifier)
        else:
            # Heavy armor - no dex bonus
            ac = armor_values.get(armor_type, 10)

        if shield:
            ac += 2

        return ac

    def get_skill_proficiencies(self, class_name: str, background: str, race_variant: str = None) -> Dict[str, List[str]]:
        """Get available skill proficiencies by source"""
        skills = {"class": [], "background": [], "racial": []}

        # Class skills
        if class_name in self.classes:
            class_data = self.classes[class_name]
            skills["class"] = class_data.get("skill_list", [])

        # Background skills - comprehensive D&D 5e backgrounds
        background_skills = {
            # Player's Handbook
            "Acolyte": ["Insight", "Religion"],
            "Charlatan": ["Deception", "Sleight of Hand"],
            "Criminal": ["Deception", "Stealth"],
            "Entertainer": ["Acrobatics", "Performance"],
            "Folk Hero": ["Animal Handling", "Survival"],
            "Guild Artisan": ["Insight", "Persuasion"],
            "Hermit": ["Medicine", "Religion"],
            "Noble": ["History", "Persuasion"],
            "Outlander": ["Athletics", "Survival"],
            "Sage": ["Arcana", "History"],
            "Sailor": ["Athletics", "Perception"],
            "Soldier": ["Athletics", "Intimidation"],
            "Urchin": ["Sleight of Hand", "Stealth"],

            # Sword Coast Adventurer's Guide
            "City Watch": ["Athletics", "Insight"],
            "Clan Crafter": ["History", "Insight"],
            "Cloistered Scholar": ["History", "Religion"],
            "Courtier": ["Insight", "Persuasion"],
            "Faction Agent": ["Insight", "Persuasion"],
            "Far Traveler": ["Insight", "Perception"],
            "Inheritor": ["Survival", "Arcana"],
            "Investigator": ["Insight", "Investigation"],
            "Knight of the Order": ["Arcana", "Religion"],
            "Mercenary Veteran": ["Athletics", "Persuasion"],
            "Urban Bounty Hunter": ["Deception", "Insight", "Persuasion", "Stealth"],
            "Uthgardt Tribe Member": ["Athletics", "Survival"],
            "Waterdhavian Noble": ["History", "Persuasion"],

            # Adventure-specific
            "Haunted One": ["Arcana", "Investigation", "Religion", "Survival"],
            "Storm Herald": ["Athletics", "Survival"],
            "Anthropologist": ["Insight", "Religion"],
            "Archaeologist": ["History", "Survival"],
            "Grinner": ["Deception", "Performance"],
            "Harpers Agent": ["Investigation", "Insight"],
            "Lords' Alliance Agent": ["Investigation", "Persuasion"],
            "Zhentarim Agent": ["Deception", "Intimidation"],
            "Fisher": ["History", "Survival"],
            "Marine": ["Athletics", "Survival"],
            "Shipwright": ["History", "Perception"],
            "Smuggler": ["Athletics", "Deception"],
            "Flaming Fist": ["Athletics", "Intimidation"],
            "Guild Member": ["Insight", "Persuasion"],
            "Lower City": ["Intimidation", "Sleight of Hand"],
            "Outer City": ["Animal Handling", "Survival"],
            "Patriar": ["History", "Persuasion"],
            "Upper City": ["History", "Persuasion"],
            "Reghed Nomad": ["Animal Handling", "Survival"],
            "Ten-Towns Trader": ["History", "Persuasion"],
            "Candlekeep Researcher": ["History", "Investigation"],
            "Feylost": ["Deception", "Survival"],
            "Witchlight Hand": ["Performance", "Sleight of Hand"],
            "Lorehold Student": ["History", "Religion"],
            "Prismari Student": ["Acrobatics", "Performance"],
            "Quandrix Student": ["Arcana", "Nature"],
            "Silverquill Student": ["Intimidation", "Persuasion"],
            "Witherbloom Student": ["Arcana", "Nature"],
            "Astral Drifter": ["Insight", "Religion"],
            "Wildspacer": ["Athletics", "Survival"],
            "Knight of Solamnia": ["Athletics", "Survival"],
            "Mage of High Sorcery": ["Arcana", "History"]
        }
        skills["background"] = background_skills.get(background, [])

        # Racial skills would be determined by race/variant

        return skills

    def validate_character_build(self, character_data: Dict[str, Any]) -> List[str]:
        """Validate character build for rule compliance"""
        errors = []

        # Validate ability scores
        abilities = character_data.get("abilities", {})
        for ability, score in abilities.items():
            if score < 3 or score > 20:
                errors.append(f"{ability.title()} score {score} is outside valid range (3-20)")

        # Validate race/class combination
        race = character_data.get("race")
        class_name = character_data.get("class_name")

        if race not in self.races:
            errors.append(f"Invalid race: {race}")

        if class_name not in self.classes:
            errors.append(f"Invalid class: {class_name}")

        # Validate feat prerequisites
        feats = character_data.get("feats", [])
        for feat_name in feats:
            if feat_name in self.feats:
                prerequisites = self.feats[feat_name]["prerequisites"]
                # Check prerequisites logic would go here

        return errors

# Usage example and API integration points
def create_character_creation_api():
    """API endpoints for enhanced character creation"""
    creator = DetailedCharacterCreator()

    # This would integrate with FastAPI endpoints
    return {
        "races": creator.get_race_options(),
        "classes": creator.get_class_options(),
        "ability_methods": creator.get_ability_score_methods(),
        "feats": list(creator.feats.keys())
    }