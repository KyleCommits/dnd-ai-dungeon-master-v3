# src/character_manager.py
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_
from sqlalchemy.orm import selectinload
from typing import Optional, List, Dict, Any
import random
from datetime import datetime

from .character_models import (
    Character, NPC, CharacterAbility, CharacterSkill, CharacterFeature,
    CharacterEquipment, CharacterSpell, UserActiveCharacter,
    CharacterProgression, CharacterDeathSave, CharacterHitDice,
    NPCAbility, NPCSkill
)
from .spell_integration import character_spell_manager

class CharacterManager:
    """Manages all character-related operations for D&D characters and NPCs."""

    def __init__(self):
        # converts ability scores to modifiers
        self.ability_modifier_table = {
            1: -5, 2: -4, 3: -4, 4: -3, 5: -3, 6: -2, 7: -2, 8: -1, 9: -1, 10: 0,
            11: 0, 12: 1, 13: 1, 14: 2, 15: 2, 16: 3, 17: 3, 18: 4, 19: 4, 20: 5,
            21: 5, 22: 6, 23: 6, 24: 7, 25: 7, 26: 8, 27: 8, 28: 9, 29: 9, 30: 10
        }

        # which skill uses which ability
        self.skill_abilities = {
            'acrobatics': 'dexterity',
            'animal_handling': 'wisdom',
            'arcana': 'intelligence',
            'athletics': 'strength',
            'deception': 'charisma',
            'history': 'intelligence',
            'insight': 'wisdom',
            'intimidation': 'charisma',
            'investigation': 'intelligence',
            'medicine': 'wisdom',
            'nature': 'intelligence',
            'perception': 'wisdom',
            'performance': 'charisma',
            'persuasion': 'charisma',
            'religion': 'intelligence',
            'sleight_of_hand': 'dexterity',
            'stealth': 'dexterity',
            'survival': 'wisdom'
        }

        # prof bonus lookup by level
        self.proficiency_by_level = {
            1: 2, 2: 2, 3: 2, 4: 2, 5: 3, 6: 3, 7: 3, 8: 3, 9: 4, 10: 4,
            11: 4, 12: 4, 13: 5, 14: 5, 15: 5, 16: 5, 17: 6, 18: 6, 19: 6, 20: 6
        }

    def get_ability_modifier(self, score: int) -> int:
        """Calculate D&D 5e ability modifier from ability score."""
        return self.ability_modifier_table.get(score, 0)

    def get_proficiency_bonus(self, level: int) -> int:
        """Get proficiency bonus for character level."""
        return self.proficiency_by_level.get(level, 2)

    async def create_character(self, db: AsyncSession, character_data: Dict[str, Any]) -> Character:
        """Create a new player character with full D&D stats."""

        # make the basic character
        character = Character(
            campaign_id=character_data['campaign_id'],
            user_id=character_data['user_id'],
            name=character_data['name'],
            race=character_data['race'],
            class_name=character_data['class_name'],
            level=character_data.get('level', 1),
            background=character_data['background'],
            max_hp=character_data['max_hp'],
            current_hp=character_data['max_hp'],
            armor_class=character_data['armor_class'],
            speed=character_data.get('speed', 30),
            proficiency_bonus=self.get_proficiency_bonus(character_data.get('level', 1))
        )

        db.add(character)
        await db.flush()  # Get character ID

        # add ability scores
        abilities = CharacterAbility(
            character_id=character.id,
            strength=character_data['abilities']['strength'],
            dexterity=character_data['abilities']['dexterity'],
            constitution=character_data['abilities']['constitution'],
            intelligence=character_data['abilities']['intelligence'],
            wisdom=character_data['abilities']['wisdom'],
            charisma=character_data['abilities']['charisma'],
            str_save_prof=character_data['saving_throws'].get('strength', False),
            dex_save_prof=character_data['saving_throws'].get('dexterity', False),
            con_save_prof=character_data['saving_throws'].get('constitution', False),
            int_save_prof=character_data['saving_throws'].get('intelligence', False),
            wis_save_prof=character_data['saving_throws'].get('wisdom', False),
            cha_save_prof=character_data['saving_throws'].get('charisma', False)
        )
        db.add(abilities)

        # setup skill proficiencies
        for skill, is_proficient in character_data['skills'].items():
            skill_obj = CharacterSkill(
                character_id=character.id,
                skill_name=skill,
                proficient=is_proficient,
                expertise=character_data.get('expertise', {}).get(skill, False)
            )
            db.add(skill_obj)

        # add class features
        for feature in character_data.get('features', []):
            feature_obj = CharacterFeature(
                character_id=character.id,
                feature_name=feature['name'],
                source=feature['source'],
                level_gained=feature.get('level_gained', 1),
                description=feature.get('description', '')
            )
            db.add(feature_obj)

        # give them equipment
        for equipment in character_data.get('equipment', []):
            equipment_obj = CharacterEquipment(
                character_id=character.id,
                item_name=equipment['name'],
                quantity=equipment.get('quantity', 1),
                equipped=equipment.get('equipped', False),
                attuned=equipment.get('attuned', False)
            )
            db.add(equipment_obj)

        # setup hit dice
        hit_die = character_data.get('hit_die', 8)  # Default d8
        hit_dice = CharacterHitDice(
            character_id=character.id,
            die_type=hit_die,
            total=character.level,
            used=0
        )
        db.add(hit_dice)

        # track progression stuff
        progression = CharacterProgression(
            character_id=character.id,
            experience_points=0,
            next_level_xp=300,  # Level 2 threshold
            level_up_pending=False
        )
        db.add(progression)

        await db.commit()

        # setup spells if they can cast
        try:
            await character_spell_manager.initialize_character_spells(db, character)
        except Exception as e:
            print(f"WARNING: Failed to initialize spells for {character.name}: {e}")

        return character

    async def get_character_full(self, db: AsyncSession, character_id: int) -> Optional[Character]:
        """Get character with all related data loaded."""
        query = select(Character).options(
            selectinload(Character.abilities),
            selectinload(Character.skills),
            selectinload(Character.features),
            selectinload(Character.equipment),
            selectinload(Character.spells)
        ).where(Character.id == character_id)

        result = await db.execute(query)
        return result.scalar_one_or_none()

    async def get_user_characters(self, db: AsyncSession, user_id: str, campaign_id: int) -> List[Character]:
        """Get all characters for a user in a specific campaign."""
        query = select(Character).where(
            and_(
                Character.user_id == user_id,
                Character.campaign_id == campaign_id,
                Character.is_active == True
            )
        )
        result = await db.execute(query)
        return result.scalars().all()

    async def get_active_character(self, db: AsyncSession, user_id: str, campaign_id: int) -> Optional[Character]:
        """Get the user's currently active character."""
        query = select(Character).join(UserActiveCharacter).where(
            and_(
                UserActiveCharacter.user_id == user_id,
                UserActiveCharacter.campaign_id == campaign_id
            )
        ).options(
            selectinload(Character.abilities),
            selectinload(Character.skills)
        )

        result = await db.execute(query)
        return result.scalar_one_or_none()

    async def set_active_character(self, db: AsyncSession, user_id: str, campaign_id: int, character_id: int):
        """Set a character as the user's active character."""
        # remove old active character
        query = select(UserActiveCharacter).where(
            and_(
                UserActiveCharacter.user_id == user_id,
                UserActiveCharacter.campaign_id == campaign_id
            )
        )
        result = await db.execute(query)
        existing = result.scalar_one_or_none()

        if existing:
            await db.delete(existing)

        # set new active character
        active_char = UserActiveCharacter(
            user_id=user_id,
            campaign_id=campaign_id,
            character_id=character_id
        )
        db.add(active_char)
        await db.commit()

    async def calculate_skill_modifier(self, character: Character, skill_name: str) -> int:
        """Calculate total modifier for a skill check."""
        # get the modifier
        ability_name = self.skill_abilities[skill_name]
        ability_score = getattr(character.abilities[0], ability_name)
        ability_mod = self.get_ability_modifier(ability_score)

        # see if they're good at it
        skill = next((s for s in character.skills if s.skill_name == skill_name), None)
        if skill and skill.proficient:
            prof_bonus = character.proficiency_bonus
            if skill.expertise:
                prof_bonus *= 2
            return ability_mod + prof_bonus

        return ability_mod

    async def calculate_saving_throw_modifier(self, character: Character, ability: str) -> int:
        """Calculate saving throw modifier."""
        ability_score = getattr(character.abilities[0], ability)
        ability_mod = self.get_ability_modifier(ability_score)

        # check if proficient in save
        save_prof_attr = f"{ability[:3]}_save_prof"
        is_proficient = getattr(character.abilities[0], save_prof_attr)

        if is_proficient:
            return ability_mod + character.proficiency_bonus
        return ability_mod

    async def roll_death_save(self, db: AsyncSession, character_id: int, session_id: str) -> Dict[str, Any]:
        """Roll a death saving throw."""
        character = await self.get_character_full(db, character_id)
        if not character or not character.is_unconscious:
            return {"error": "Character is not unconscious"}

        # roll the die
        roll = random.randint(1, 20)
        success = roll >= 10

        # nat 20 gets you back up
        if roll == 20:
            character.current_hp = 1
            character.is_unconscious = False
            character.death_save_successes = 0
            character.death_save_failures = 0
            await db.commit()
            return {
                "roll": roll,
                "result": "natural_20",
                "message": f"Natural 20! {character.name} regains consciousness with 1 HP!"
            }

        # nat 1 is real bad
        if roll == 1:
            character.death_save_failures += 2
        elif success:
            character.death_save_successes += 1
        else:
            character.death_save_failures += 1

        # save the death save result
        death_save = CharacterDeathSave(
            character_id=character_id,
            save_number=character.death_save_successes + character.death_save_failures,
            result=success,
            die_roll=roll,
            session_id=session_id
        )
        db.add(death_save)

        # see if dead or stable
        if character.death_save_failures >= 3:
            character.is_alive = False
            await db.commit()
            return {
                "roll": roll,
                "result": "death",
                "message": f"{character.name} has died."
            }
        elif character.death_save_successes >= 3:
            character.is_stable = True
            character.is_unconscious = False
            await db.commit()
            return {
                "roll": roll,
                "result": "stable",
                "message": f"{character.name} is stabilized but unconscious."
            }

        await db.commit()
        return {
            "roll": roll,
            "result": "continue",
            "successes": character.death_save_successes,
            "failures": character.death_save_failures
        }

    async def heal_character(self, db: AsyncSession, character_id: int, hp_amount: int):
        """Heal a character and reset death saves if brought above 0 HP."""
        character = await self.get_character_full(db, character_id)
        if not character:
            return

        old_hp = character.current_hp
        character.current_hp = min(character.current_hp + hp_amount, character.max_hp)

        # if healed reset death saves
        if old_hp <= 0 and character.current_hp > 0:
            character.is_unconscious = False
            character.is_stable = False
            character.death_save_successes = 0
            character.death_save_failures = 0

        await db.commit()

    async def create_npc(self, db: AsyncSession, npc_data: Dict[str, Any]) -> NPC:
        """Create a new NPC."""
        npc = NPC(
            campaign_id=npc_data['campaign_id'],
            name=npc_data['name'],
            race=npc_data['race'],
            class_name=npc_data.get('class_name'),
            level=npc_data.get('level', 1),
            npc_type=npc_data['npc_type'],
            max_hp=npc_data['max_hp'],
            current_hp=npc_data['max_hp'],
            armor_class=npc_data['armor_class'],
            speed=npc_data.get('speed', 30)
        )

        db.add(npc)
        await db.flush()

        # setup npc stats
        abilities = NPCAbility(
            npc_id=npc.id,
            strength=npc_data['abilities']['strength'],
            dexterity=npc_data['abilities']['dexterity'],
            constitution=npc_data['abilities']['constitution'],
            intelligence=npc_data['abilities']['intelligence'],
            wisdom=npc_data['abilities']['wisdom'],
            charisma=npc_data['abilities']['charisma']
        )
        db.add(abilities)

        await db.commit()
        return npc

    async def get_character_spells(self, db: AsyncSession, character_id: int) -> Dict[str, Any]:
        """Get all spell information for a character"""
        try:
            print(f"DEBUG: CharacterManager.get_character_spells called for character {character_id}")
            result = await character_spell_manager.get_character_spells(db, character_id)
            print(f"DEBUG: Character spell manager returned: {result is not None}")
            return result
        except Exception as e:
            print(f"ERROR in CharacterManager.get_character_spells: {type(e).__name__}: {str(e)}")
            import traceback
            traceback.print_exc()
            raise

    async def cast_spell(self, db: AsyncSession, character_id: int, spell_name: str, slot_level: int) -> Dict[str, Any]:
        """Cast a spell for a character"""
        return await character_spell_manager.cast_spell(db, character_id, spell_name, slot_level)

    async def learn_spell(self, db: AsyncSession, character_id: int, spell_name: str) -> Dict[str, Any]:
        """Learn a new spell for a character"""
        return await character_spell_manager.learn_spell(db, character_id, spell_name)

# the main character manager
character_manager = CharacterManager()