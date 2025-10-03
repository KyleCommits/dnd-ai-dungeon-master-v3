# src/character_models.py
from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, DateTime, Text, Float
from sqlalchemy.orm import relationship
from datetime import datetime
from .models import Base

class Character(Base):
    __tablename__ = "characters"

    id = Column(Integer, primary_key=True, index=True)
    campaign_id = Column(Integer, ForeignKey("campaigns.id"), nullable=False)
    user_id = Column(String, nullable=False)
    name = Column(String, nullable=False)
    race = Column(String, nullable=False)
    class_name = Column(String, nullable=False)
    level = Column(Integer, default=1)
    background = Column(String, nullable=False)

    # basic stats
    max_hp = Column(Integer, nullable=False)
    current_hp = Column(Integer, nullable=False)
    armor_class = Column(Integer, nullable=False)
    speed = Column(Integer, default=30)
    proficiency_bonus = Column(Integer, default=2)

    # death save stuff
    death_save_successes = Column(Integer, default=0)
    death_save_failures = Column(Integer, default=0)
    is_unconscious = Column(Boolean, default=False)
    is_stable = Column(Boolean, default=False)

    # status info
    is_active = Column(Boolean, default=True)
    is_alive = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # database relationships
    abilities = relationship("CharacterAbility", back_populates="character", cascade="all, delete-orphan")
    skills = relationship("CharacterSkill", back_populates="character", cascade="all, delete-orphan")
    features = relationship("CharacterFeature", back_populates="character", cascade="all, delete-orphan")
    equipment = relationship("CharacterEquipment", back_populates="character", cascade="all, delete-orphan")
    spells = relationship("CharacterSpell", back_populates="character", cascade="all, delete-orphan")
    animal_companions = relationship("AnimalCompanion", back_populates="character", cascade="all, delete-orphan")

class NPC(Base):
    __tablename__ = "npcs"

    id = Column(Integer, primary_key=True, index=True)
    campaign_id = Column(Integer, ForeignKey("campaigns.id"), nullable=False)
    name = Column(String, nullable=False)
    race = Column(String, nullable=False)
    class_name = Column(String, nullable=True)
    level = Column(Integer, default=1)
    npc_type = Column(String, nullable=False)  # 'ally', 'enemy', 'neutral'

    # basic stats
    max_hp = Column(Integer, nullable=False)
    current_hp = Column(Integer, nullable=False)
    armor_class = Column(Integer, nullable=False)
    speed = Column(Integer, default=30)

    # status info
    is_active = Column(Boolean, default=True)
    is_alive = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # database relationships
    abilities = relationship("NPCAbility", back_populates="npc", cascade="all, delete-orphan")
    skills = relationship("NPCSkill", back_populates="npc", cascade="all, delete-orphan")

class CharacterAbility(Base):
    __tablename__ = "character_abilities"

    id = Column(Integer, primary_key=True, index=True)
    character_id = Column(Integer, ForeignKey("characters.id"), nullable=False)

    # ability scores
    strength = Column(Integer, nullable=False)
    dexterity = Column(Integer, nullable=False)
    constitution = Column(Integer, nullable=False)
    intelligence = Column(Integer, nullable=False)
    wisdom = Column(Integer, nullable=False)
    charisma = Column(Integer, nullable=False)

    # save proficiencies
    str_save_prof = Column(Boolean, default=False)
    dex_save_prof = Column(Boolean, default=False)
    con_save_prof = Column(Boolean, default=False)
    int_save_prof = Column(Boolean, default=False)
    wis_save_prof = Column(Boolean, default=False)
    cha_save_prof = Column(Boolean, default=False)

    character = relationship("Character", back_populates="abilities")

class CharacterSkill(Base):
    __tablename__ = "character_skills"

    id = Column(Integer, primary_key=True, index=True)
    character_id = Column(Integer, ForeignKey("characters.id"), nullable=False)
    skill_name = Column(String, nullable=False)
    proficient = Column(Boolean, default=False)
    expertise = Column(Boolean, default=False)

    character = relationship("Character", back_populates="skills")

class CharacterFeature(Base):
    __tablename__ = "character_features"

    id = Column(Integer, primary_key=True, index=True)
    character_id = Column(Integer, ForeignKey("characters.id"), nullable=False)
    feature_name = Column(String, nullable=False)
    source = Column(String, nullable=False)  # 'race', 'class', 'background', 'feat'
    level_gained = Column(Integer, nullable=True)
    description = Column(Text, nullable=True)

    character = relationship("Character", back_populates="features")

class CharacterEquipment(Base):
    __tablename__ = "character_equipment"

    id = Column(Integer, primary_key=True, index=True)
    character_id = Column(Integer, ForeignKey("characters.id"), nullable=False)
    item_name = Column(String, nullable=False)
    quantity = Column(Integer, default=1)
    equipped = Column(Boolean, default=False)
    attuned = Column(Boolean, default=False)

    character = relationship("Character", back_populates="equipment")

class CharacterSpell(Base):
    __tablename__ = "character_spells"

    id = Column(Integer, primary_key=True, index=True)
    character_id = Column(Integer, ForeignKey("characters.id"), nullable=False)
    spell_name = Column(String, nullable=False)
    spell_level = Column(Integer, nullable=False)
    prepared = Column(Boolean, default=False)
    known = Column(Boolean, default=True)

    character = relationship("Character", back_populates="spells")

class UserActiveCharacter(Base):
    __tablename__ = "user_active_characters"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, nullable=False)
    campaign_id = Column(Integer, ForeignKey("campaigns.id"), nullable=False)
    character_id = Column(Integer, ForeignKey("characters.id"), nullable=False)

    # database relationships
    character = relationship("Character")

class CharacterProgression(Base):
    __tablename__ = "character_progression"

    id = Column(Integer, primary_key=True, index=True)
    character_id = Column(Integer, ForeignKey("characters.id"), nullable=False)
    experience_points = Column(Integer, default=0)
    next_level_xp = Column(Integer, default=300)
    level_up_pending = Column(Boolean, default=False)
    ability_score_improvements_remaining = Column(Integer, default=0)

class CharacterLevelHistory(Base):
    __tablename__ = "character_level_history"

    id = Column(Integer, primary_key=True, index=True)
    character_id = Column(Integer, ForeignKey("characters.id"), nullable=False)
    old_level = Column(Integer, nullable=False)
    new_level = Column(Integer, nullable=False)
    hp_gained = Column(Integer, nullable=False)
    features_gained = Column(Text, nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    session_id = Column(String, nullable=True)

class CharacterDeathSave(Base):
    __tablename__ = "character_death_saves"

    id = Column(Integer, primary_key=True, index=True)
    character_id = Column(Integer, ForeignKey("characters.id"), nullable=False)
    save_number = Column(Integer, nullable=False)  # 1, 2, or 3
    result = Column(Boolean, nullable=False)  # True for success, False for failure
    die_roll = Column(Integer, nullable=False)  # The actual d20 roll
    timestamp = Column(DateTime, default=datetime.utcnow)
    session_id = Column(String, nullable=True)

class CharacterHitDice(Base):
    __tablename__ = "character_hit_dice"

    id = Column(Integer, primary_key=True, index=True)
    character_id = Column(Integer, ForeignKey("characters.id"), nullable=False)
    die_type = Column(Integer, nullable=False)  # 6, 8, 10, 12 for d6, d8, d10, d12
    total = Column(Integer, nullable=False)
    used = Column(Integer, default=0)
    short_rest_recovered = Column(Integer, default=0)

class CampaignMilestone(Base):
    __tablename__ = "campaign_milestones"

    id = Column(Integer, primary_key=True, index=True)
    campaign_id = Column(Integer, ForeignKey("campaigns.id"), nullable=False)
    milestone_name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    target_level = Column(Integer, nullable=False)
    act_number = Column(Integer, nullable=True)
    completed = Column(Boolean, default=False)
    completed_at = Column(DateTime, nullable=True)

class CharacterMilestone(Base):
    __tablename__ = "character_milestones"

    id = Column(Integer, primary_key=True, index=True)
    character_id = Column(Integer, ForeignKey("characters.id"), nullable=False)
    milestone_id = Column(Integer, ForeignKey("campaign_milestones.id"), nullable=False)
    achieved = Column(Boolean, default=False)
    achieved_at = Column(DateTime, nullable=True)
    session_id = Column(String, nullable=True)

# npc models
class NPCAbility(Base):
    __tablename__ = "npc_abilities"

    id = Column(Integer, primary_key=True, index=True)
    npc_id = Column(Integer, ForeignKey("npcs.id"), nullable=False)

    strength = Column(Integer, nullable=False)
    dexterity = Column(Integer, nullable=False)
    constitution = Column(Integer, nullable=False)
    intelligence = Column(Integer, nullable=False)
    wisdom = Column(Integer, nullable=False)
    charisma = Column(Integer, nullable=False)

    npc = relationship("NPC", back_populates="abilities")

class NPCSkill(Base):
    __tablename__ = "npc_skills"

    id = Column(Integer, primary_key=True, index=True)
    npc_id = Column(Integer, ForeignKey("npcs.id"), nullable=False)
    skill_name = Column(String, nullable=False)
    proficient = Column(Boolean, default=False)
    expertise = Column(Boolean, default=False)

    npc = relationship("NPC", back_populates="skills")