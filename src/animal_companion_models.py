# src/animal_companion_models.py
"""
Animal Companion Models for Beast Master Rangers and other classes
Handles animal companions, familiars, and similar creature companions
"""

from sqlalchemy import Column, Integer, String, Boolean, Text, ForeignKey, DateTime, JSON
from sqlalchemy.orm import relationship
from datetime import datetime
from typing import Dict, List, Optional
from .models import Base

class CompanionTemplate(Base):
    """Base template for different types of animal companions"""
    __tablename__ = 'companion_templates'

    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)  # e.g., "Wolf", "Panther", "Eagle"
    creature_type = Column(String(50), nullable=False, default="beast")  # beast, fey, etc.
    size = Column(String(20), nullable=False)  # Tiny, Small, Medium, Large
    challenge_rating = Column(String(10), nullable=False)  # "0", "1/8", "1/4", etc.

    # Base Stats
    armor_class = Column(Integer, nullable=False)
    hit_points = Column(Integer, nullable=False)
    hit_dice = Column(String(20), nullable=False)  # e.g., "2d8+2"

    # Ability Scores
    strength = Column(Integer, nullable=False)
    dexterity = Column(Integer, nullable=False)
    constitution = Column(Integer, nullable=False)
    intelligence = Column(Integer, nullable=False)
    wisdom = Column(Integer, nullable=False)
    charisma = Column(Integer, nullable=False)

    # Movement
    speed_land = Column(Integer, default=0)
    speed_fly = Column(Integer, default=0)
    speed_swim = Column(Integer, default=0)
    speed_climb = Column(Integer, default=0)
    speed_burrow = Column(Integer, default=0)

    # Skills (JSON: {"perception": 3, "stealth": 4})
    skills = Column(JSON, default=dict)

    # Senses
    darkvision = Column(Integer, default=0)  # Range in feet
    blindsight = Column(Integer, default=0)
    passive_perception = Column(Integer, nullable=False)

    # Special Abilities (JSON array of ability descriptions)
    special_abilities = Column(JSON, default=list)

    # Attacks (JSON array of attack data)
    attacks = Column(JSON, default=list)

    # Beast Master specific flags
    is_beast_master_eligible = Column(Boolean, default=False)
    is_familiar_eligible = Column(Boolean, default=False)
    is_mount_eligible = Column(Boolean, default=False)

    # Description and flavor
    description = Column(Text)
    environment = Column(String(100))  # Forest, Mountains, Coast, etc.

    created_at = Column(DateTime, default=datetime.utcnow)

class AnimalCompanion(Base):
    """Individual animal companion belonging to a character"""
    __tablename__ = 'animal_companions'

    id = Column(Integer, primary_key=True)
    character_id = Column(Integer, ForeignKey('characters.id'), nullable=False)
    template_id = Column(Integer, ForeignKey('companion_templates.id'), nullable=False)
    campaign_id = Column(Integer, ForeignKey('campaigns.id'), nullable=False)

    # Custom name for this companion
    name = Column(String(100), nullable=False)

    # Current Stats (can be modified from template)
    current_hp = Column(Integer, nullable=False)
    max_hp = Column(Integer, nullable=False)

    # Level-based improvements (Beast Master scaling)
    companion_level = Column(Integer, default=1)

    # Temporary conditions
    is_unconscious = Column(Boolean, default=False)
    is_dead = Column(Boolean, default=False)

    # Experience and progression
    experience_points = Column(Integer, default=0)

    # Custom modifications (JSON for any special bonuses)
    custom_stats = Column(JSON, default=dict)

    # Relationship tracking
    relationship_level = Column(Integer, default=1)  # Bond strength 1-5

    # Notes
    personality_traits = Column(Text)
    backstory = Column(Text)
    notes = Column(Text)

    # Timestamps
    acquired_at = Column(DateTime, default=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    character = relationship("Character", back_populates="animal_companions")
    template = relationship("CompanionTemplate")

class CompanionProgression(Base):
    """Tracks companion level progression and improvements"""
    __tablename__ = 'companion_progression'

    id = Column(Integer, primary_key=True)
    companion_id = Column(Integer, ForeignKey('animal_companions.id'), nullable=False)

    level = Column(Integer, nullable=False)
    hp_gained = Column(Integer, nullable=False)
    improvements_gained = Column(JSON, default=list)  # List of improvements at this level

    # Timestamp
    gained_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    companion = relationship("AnimalCompanion")

class CompanionAbility(Base):
    """Special abilities that companions can learn"""
    __tablename__ = 'companion_abilities'

    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=False)
    ability_type = Column(String(50), nullable=False)  # "feature", "attack", "reaction"

    # Requirements
    min_level = Column(Integer, default=1)
    required_template_type = Column(String(100))  # Specific to certain creatures

    # Mechanics
    mechanics = Column(JSON, default=dict)  # Dice, DCs, ranges, etc.

    created_at = Column(DateTime, default=datetime.utcnow)

class CompanionEquipment(Base):
    """Equipment that companions can wear/use"""
    __tablename__ = 'companion_equipment'

    id = Column(Integer, primary_key=True)
    companion_id = Column(Integer, ForeignKey('animal_companions.id'), nullable=False)

    item_name = Column(String(100), nullable=False)
    item_type = Column(String(50), nullable=False)  # "armor", "accessory", "tool"
    is_equipped = Column(Boolean, default=False)

    # Stats modifications
    ac_bonus = Column(Integer, default=0)
    stat_bonuses = Column(JSON, default=dict)

    description = Column(Text)

    # Timestamps
    acquired_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    companion = relationship("AnimalCompanion")

# Beast Master specific progression rules
BEAST_MASTER_PROGRESSION = {
    1: {
        "hp_bonus": 0,
        "ac_bonus": 0,
        "attack_bonus": 0,
        "damage_bonus": 0,
        "abilities": []
    },
    3: {  # When Beast Master is gained
        "hp_bonus": 0,
        "ac_bonus": 0,
        "attack_bonus": 0,
        "damage_bonus": 0,
        "abilities": ["Ranger's Companion"]
    },
    7: {
        "hp_bonus": 5,
        "ac_bonus": 1,
        "attack_bonus": 1,
        "damage_bonus": 1,
        "abilities": ["Exceptional Training"]
    },
    11: {
        "hp_bonus": 10,
        "ac_bonus": 1,
        "attack_bonus": 2,
        "damage_bonus": 2,
        "abilities": ["Bestial Fury"]
    },
    15: {
        "hp_bonus": 15,
        "ac_bonus": 2,
        "attack_bonus": 3,
        "damage_bonus": 3,
        "abilities": ["Share Spells"]
    }
}

# Companion Templates Data
COMPANION_TEMPLATES_DATA = [
    {
        "name": "Wolf",
        "creature_type": "beast",
        "size": "Medium",
        "challenge_rating": "1/4",
        "armor_class": 13,
        "hit_points": 11,
        "hit_dice": "2d8+2",
        "strength": 12,
        "dexterity": 15,
        "constitution": 12,
        "intelligence": 3,
        "wisdom": 12,
        "charisma": 6,
        "speed_land": 40,
        "skills": {"perception": 3, "stealth": 4},
        "passive_perception": 13,
        "special_abilities": [
            {
                "name": "Keen Hearing and Smell",
                "description": "The wolf has advantage on Wisdom (Perception) checks that rely on hearing or smell."
            },
            {
                "name": "Pack Tactics",
                "description": "The wolf has advantage on an attack roll against a creature if at least one of the wolf's allies is within 5 feet of the creature and the ally isn't incapacitated."
            }
        ],
        "attacks": [
            {
                "name": "Bite",
                "attack_bonus": 4,
                "damage": "2d4+2",
                "damage_type": "piercing",
                "range": "5 ft.",
                "special": "Target must make a DC 11 Strength saving throw or be knocked prone"
            }
        ],
        "is_beast_master_eligible": True,
        "environment": "Forest, Mountains",
        "description": "A fierce pack hunter with keen senses and tactical intelligence."
    },
    {
        "name": "Panther",
        "creature_type": "beast",
        "size": "Medium",
        "challenge_rating": "1/4",
        "armor_class": 12,
        "hit_points": 13,
        "hit_dice": "3d8",
        "strength": 14,
        "dexterity": 15,
        "constitution": 10,
        "intelligence": 3,
        "wisdom": 14,
        "charisma": 7,
        "speed_land": 50,
        "speed_climb": 40,
        "skills": {"perception": 4, "stealth": 6},
        "passive_perception": 14,
        "special_abilities": [
            {
                "name": "Keen Smell",
                "description": "The panther has advantage on Wisdom (Perception) checks that rely on smell."
            },
            {
                "name": "Pounce",
                "description": "If the panther moves at least 20 feet straight toward a creature and then hits it with a claw attack on the same turn, that target must succeed on a DC 12 Strength saving throw or be knocked prone. If the target is prone, the panther can make one bite attack against it as a bonus action."
            }
        ],
        "attacks": [
            {
                "name": "Bite",
                "attack_bonus": 4,
                "damage": "1d6+2",
                "damage_type": "piercing",
                "range": "5 ft."
            },
            {
                "name": "Claw",
                "attack_bonus": 4,
                "damage": "1d4+2",
                "damage_type": "slashing",
                "range": "5 ft."
            }
        ],
        "is_beast_master_eligible": True,
        "environment": "Forest, Jungle",
        "description": "A stealthy and agile predator capable of swift strikes and climbing."
    },
    {
        "name": "Blood Hawk",
        "creature_type": "beast",
        "size": "Small",
        "challenge_rating": "1/8",
        "armor_class": 12,
        "hit_points": 7,
        "hit_dice": "2d6",
        "strength": 6,
        "dexterity": 14,
        "constitution": 10,
        "intelligence": 3,
        "wisdom": 14,
        "charisma": 5,
        "speed_land": 10,
        "speed_fly": 60,
        "skills": {"perception": 4},
        "passive_perception": 14,
        "special_abilities": [
            {
                "name": "Keen Sight",
                "description": "The hawk has advantage on Wisdom (Perception) checks that rely on sight."
            },
            {
                "name": "Pack Tactics",
                "description": "The hawk has advantage on an attack roll against a creature if at least one of the hawk's allies is within 5 feet of the creature and the ally isn't incapacitated."
            }
        ],
        "attacks": [
            {
                "name": "Beak",
                "attack_bonus": 4,
                "damage": "1d4+2",
                "damage_type": "piercing",
                "range": "5 ft."
            }
        ],
        "is_beast_master_eligible": True,
        "environment": "Mountains, Hills",
        "description": "A fierce aerial predator with excellent vision and pack hunting instincts."
    },
    {
        "name": "Mastiff",
        "creature_type": "beast",
        "size": "Medium",
        "challenge_rating": "1/8",
        "armor_class": 12,
        "hit_points": 5,
        "hit_dice": "1d8+1",
        "strength": 13,
        "dexterity": 14,
        "constitution": 12,
        "intelligence": 3,
        "wisdom": 12,
        "charisma": 7,
        "speed_land": 40,
        "skills": {"perception": 3},
        "passive_perception": 13,
        "special_abilities": [
            {
                "name": "Keen Hearing and Smell",
                "description": "The mastiff has advantage on Wisdom (Perception) checks that rely on hearing or smell."
            }
        ],
        "attacks": [
            {
                "name": "Bite",
                "attack_bonus": 3,
                "damage": "1d6+1",
                "damage_type": "piercing",
                "range": "5 ft.",
                "special": "Target must make a DC 11 Strength saving throw or be knocked prone"
            }
        ],
        "is_beast_master_eligible": True,
        "environment": "Urban, Rural",
        "description": "A loyal and trainable hunting dog with strong protective instincts."
    },
    {
        "name": "Eagle",
        "creature_type": "beast",
        "size": "Small",
        "challenge_rating": "0",
        "armor_class": 12,
        "hit_points": 3,
        "hit_dice": "1d6",
        "strength": 6,
        "dexterity": 15,
        "constitution": 10,
        "intelligence": 2,
        "wisdom": 14,
        "charisma": 7,
        "speed_land": 10,
        "speed_fly": 60,
        "skills": {"perception": 4},
        "passive_perception": 14,
        "special_abilities": [
            {
                "name": "Keen Sight",
                "description": "The eagle has advantage on Wisdom (Perception) checks that rely on sight."
            }
        ],
        "attacks": [
            {
                "name": "Talons",
                "attack_bonus": 4,
                "damage": "1d4+2",
                "damage_type": "slashing",
                "range": "5 ft."
            }
        ],
        "is_beast_master_eligible": True,
        "is_familiar_eligible": True,
        "environment": "Mountains, Coasts",
        "description": "A majestic bird of prey with exceptional eyesight and soaring abilities."
    },
    {
        "name": "Owl",
        "creature_type": "beast",
        "size": "Tiny",
        "challenge_rating": "0",
        "armor_class": 11,
        "hit_points": 1,
        "hit_dice": "1d4-1",
        "strength": 3,
        "dexterity": 13,
        "constitution": 8,
        "intelligence": 2,
        "wisdom": 12,
        "charisma": 7,
        "speed_land": 5,
        "speed_fly": 60,
        "skills": {"perception": 3, "stealth": 3},
        "darkvision": 120,
        "passive_perception": 13,
        "special_abilities": [
            {
                "name": "Flyby",
                "description": "The owl doesn't provoke opportunity attacks when it flies out of an enemy's reach."
            },
            {
                "name": "Keen Hearing and Sight",
                "description": "The owl has advantage on Wisdom (Perception) checks that rely on hearing or sight."
            }
        ],
        "attacks": [
            {
                "name": "Talons",
                "attack_bonus": 3,
                "damage": "1",
                "damage_type": "slashing",
                "range": "5 ft."
            }
        ],
        "is_beast_master_eligible": True,
        "is_familiar_eligible": True,
        "environment": "Forest, Urban",
        "description": "A wise nocturnal hunter with silent flight and exceptional night vision."
    }
    # Additional templates would continue here...
]