# src/animal_companion_manager.py
"""
animal companion manager
handles creating and managing animal companions for beast master rangers
"""

import json
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import and_, or_, select

from .animal_companion_models import (
    CompanionTemplate, AnimalCompanion, CompanionProgression,
    CompanionAbility, CompanionEquipment, BEAST_MASTER_PROGRESSION,
    COMPANION_TEMPLATES_DATA
)

class AnimalCompanionManager:
    def __init__(self, db_session: AsyncSession):
        self.session = db_session

    async def initialize_companion_templates(self):
        """setup companion templates in the database"""
        try:
            # check if templates exist
            result = await self.session.execute(select(CompanionTemplate))
            existing_templates = result.scalars().all()
            if len(existing_templates) > 0:
                return {"success": True, "message": "Templates already initialized"}

            # insert template data
            for template_data in COMPANION_TEMPLATES_DATA:
                template = CompanionTemplate(**template_data)
                self.session.add(template)

            await self.session.commit()
            return {"success": True, "message": f"Initialized {len(COMPANION_TEMPLATES_DATA)} companion templates"}

        except Exception as e:
            await self.session.rollback()
            return {"success": False, "error": str(e)}

    async def get_available_companions(self, companion_type: str = "beast_master") -> List[Dict[str, Any]]:
        """get list of companion templates you can use"""
        try:
            query = select(CompanionTemplate)

            if companion_type == "beast_master":
                query = query.where(CompanionTemplate.is_beast_master_eligible == True)
            elif companion_type == "familiar":
                query = query.where(CompanionTemplate.is_familiar_eligible == True)
            elif companion_type == "mount":
                query = query.where(CompanionTemplate.is_mount_eligible == True)

            result = await self.session.execute(query)
            templates = result.scalars().all()

            return [
                {
                    "id": template.id,
                    "name": template.name,
                    "size": template.size,
                    "challenge_rating": template.challenge_rating,
                    "armor_class": template.armor_class,
                    "hit_points": template.hit_points,
                    "speed": {
                        "land": template.speed_land,
                        "fly": template.speed_fly,
                        "swim": template.speed_swim,
                        "climb": template.speed_climb,
                        "burrow": template.speed_burrow
                    },
                    "abilities": {
                        "str": template.strength,
                        "dex": template.dexterity,
                        "con": template.constitution,
                        "int": template.intelligence,
                        "wis": template.wisdom,
                        "cha": template.charisma
                    },
                    "skills": template.skills,
                    "special_abilities": template.special_abilities,
                    "attacks": template.attacks,
                    "environment": template.environment,
                    "description": template.description
                }
                for template in templates
            ]

        except Exception as e:
            return {"error": str(e)}

    async def create_companion(self, character_id: int, template_id: int, campaign_id: int,
                        name: str, **kwargs) -> Dict[str, Any]:
        """make a new animal companion for a character"""
        try:
            # get the template
            result = await self.session.execute(
                select(CompanionTemplate).where(CompanionTemplate.id == template_id)
            )
            template = result.scalar_one_or_none()

            if not template:
                return {"success": False, "error": "Template not found"}

            # check if already has companion
            result = await self.session.execute(
                select(AnimalCompanion).where(
                    and_(
                        AnimalCompanion.character_id == character_id,
                        AnimalCompanion.is_dead == False
                    )
                )
            )
            existing_companion = result.scalar_one_or_none()

            if existing_companion:
                return {"success": False, "error": "Character already has an active companion"}

            # create the companion
            companion = AnimalCompanion(
                character_id=character_id,
                template_id=template_id,
                campaign_id=campaign_id,
                name=name,
                current_hp=template.hit_points,
                max_hp=template.hit_points,
                companion_level=1,
                personality_traits=kwargs.get("personality_traits", ""),
                backstory=kwargs.get("backstory", ""),
                notes=kwargs.get("notes", "")
            )

            self.session.add(companion)
            await self.session.commit()

            return {
                "success": True,
                "companion": await self.get_companion_full_stats(companion.id)
            }

        except Exception as e:
            await self.session.rollback()
            return {"success": False, "error": str(e)}

    async def get_companion_full_stats(self, companion_id: int) -> Dict[str, Any]:
        """get full companion stats with all bonuses applied"""
        try:
            result = await self.session.execute(
                select(AnimalCompanion).where(AnimalCompanion.id == companion_id)
            )
            companion = result.scalar_one_or_none()

            if not companion:
                return {"error": "Companion not found"}

            # get template data
            await self.session.refresh(companion, ['template'])
            template = companion.template

            # calculate level bonuses
            level_bonuses = self.calculate_level_bonuses(companion.companion_level)

            # base stats plus level bonuses
            stats = {
                "id": companion.id,
                "name": companion.name,
                "template_name": template.name,
                "size": template.size,
                "creature_type": template.creature_type,
                "challenge_rating": template.challenge_rating,
                "level": companion.companion_level,

                # combat stats
                "armor_class": template.armor_class + level_bonuses["ac_bonus"],
                "current_hp": companion.current_hp,
                "max_hp": companion.max_hp + level_bonuses["hp_bonus"],
                "hit_dice": template.hit_dice,

                # ability scores
                "abilities": {
                    "strength": template.strength,
                    "dexterity": template.dexterity,
                    "constitution": template.constitution,
                    "intelligence": template.intelligence,
                    "wisdom": template.wisdom,
                    "charisma": template.charisma
                },

                # movement stuff
                "speed": {
                    "land": template.speed_land,
                    "fly": template.speed_fly,
                    "swim": template.speed_swim,
                    "climb": template.speed_climb,
                    "burrow": template.speed_burrow
                },

                # skills and senses
                "skills": template.skills,
                "darkvision": template.darkvision,
                "blindsight": template.blindsight,
                "passive_perception": template.passive_perception,

                # special abilities
                "special_abilities": template.special_abilities,

                # attacks with bonuses
                "attacks": self.calculate_attack_bonuses(template.attacks, level_bonuses),

                # status info
                "is_unconscious": companion.is_unconscious,
                "is_dead": companion.is_dead,
                "relationship_level": companion.relationship_level,

                # flavor text
                "personality_traits": companion.personality_traits,
                "backstory": companion.backstory,
                "notes": companion.notes,
                "environment": template.environment,
                "description": template.description,

                # progression data
                "experience_points": companion.experience_points,
                "level_bonuses": level_bonuses
            }

            return stats

        except Exception as e:
            return {"error": str(e)}

    def calculate_level_bonuses(self, companion_level: int) -> Dict[str, Any]:
        """figure out bonuses based on companion level (beast master progression)"""
        bonuses = {
            "hp_bonus": 0,
            "ac_bonus": 0,
            "attack_bonus": 0,
            "damage_bonus": 0,
            "abilities": []
        }

        # calculate level bonuses
        for level, level_data in BEAST_MASTER_PROGRESSION.items():
            if companion_level >= level:
                bonuses["hp_bonus"] = level_data["hp_bonus"]
                bonuses["ac_bonus"] = level_data["ac_bonus"]
                bonuses["attack_bonus"] = level_data["attack_bonus"]
                bonuses["damage_bonus"] = level_data["damage_bonus"]
                bonuses["abilities"].extend(level_data["abilities"])

        return bonuses

    def calculate_attack_bonuses(self, attacks: List[Dict], level_bonuses: Dict) -> List[Dict]:
        """add level bonuses to attacks"""
        if not attacks:
            return []

        modified_attacks = []
        for attack in attacks:
            modified_attack = attack.copy()
            modified_attack["attack_bonus"] += level_bonuses["attack_bonus"]

            # add damage bonus if needed
            if level_bonuses["damage_bonus"] > 0:
                modified_attack["damage"] += f"+{level_bonuses['damage_bonus']}"

            modified_attacks.append(modified_attack)

        return modified_attacks

    async def level_up_companion(self, companion_id: int, ranger_level: int) -> Dict[str, Any]:
        """level up a companion based on ranger's level"""
        try:
            result = await self.session.execute(
                select(AnimalCompanion).where(AnimalCompanion.id == companion_id)
            )
            companion = result.scalar_one_or_none()

            if not companion:
                return {"success": False, "error": "Companion not found"}

            # calculate companion level
            new_level = self.calculate_companion_level(ranger_level)

            if new_level <= companion.companion_level:
                return {"success": False, "error": "Companion already at appropriate level"}

            # apply level bonuses
            old_bonuses = self.calculate_level_bonuses(companion.companion_level)
            new_bonuses = self.calculate_level_bonuses(new_level)

            # increase hp
            hp_gain = new_bonuses["hp_bonus"] - old_bonuses["hp_bonus"]
            companion.max_hp += hp_gain
            companion.current_hp += hp_gain  # full heal on level up

            # set new level
            old_level = companion.companion_level
            companion.companion_level = new_level

            # track progression
            progression = CompanionProgression(
                companion_id=companion.id,
                level=new_level,
                hp_gained=hp_gain,
                improvements_gained=[
                    f"AC bonus: +{new_bonuses['ac_bonus']}",
                    f"Attack bonus: +{new_bonuses['attack_bonus']}",
                    f"Damage bonus: +{new_bonuses['damage_bonus']}"
                ]
            )
            self.session.add(progression)

            await self.session.commit()

            return {
                "success": True,
                "old_level": old_level,
                "new_level": new_level,
                "hp_gained": hp_gain,
                "bonuses": new_bonuses,
                "companion": await self.get_companion_full_stats(companion.id)
            }

        except Exception as e:
            await self.session.rollback()
            return {"success": False, "error": str(e)}

    def calculate_companion_level(self, ranger_level: int) -> int:
        """figure out companion level based on ranger level"""
        # companions get abilities at certain levels
        if ranger_level >= 15:
            return 4  # Share Spells
        elif ranger_level >= 11:
            return 3  # Bestial Fury
        elif ranger_level >= 7:
            return 2  # Exceptional Training
        elif ranger_level >= 3:
            return 1  # Basic companion
        else:
            return 0  # No companion yet

    async def heal_companion(self, companion_id: int, healing_amount: int) -> Dict[str, Any]:
        """heal up a companion"""
        try:
            result = await self.session.execute(
                select(AnimalCompanion).where(AnimalCompanion.id == companion_id)
            )
            companion = result.scalar_one_or_none()

            if not companion:
                return {"success": False, "error": "Companion not found"}

            if companion.is_dead:
                return {"success": False, "error": "Cannot heal a dead companion"}

            # calculate max hp
            level_bonuses = self.calculate_level_bonuses(companion.companion_level)
            max_hp = companion.max_hp + level_bonuses["hp_bonus"]

            old_hp = companion.current_hp
            companion.current_hp = min(max_hp, companion.current_hp + healing_amount)

            # revive if healed above 0
            if companion.current_hp > 0:
                companion.is_unconscious = False

            await self.session.commit()

            return {
                "success": True,
                "old_hp": old_hp,
                "new_hp": companion.current_hp,
                "max_hp": max_hp,
                "healing_applied": companion.current_hp - old_hp
            }

        except Exception as e:
            await self.session.rollback()
            return {"success": False, "error": str(e)}

    async def damage_companion(self, companion_id: int, damage_amount: int) -> Dict[str, Any]:
        """hurt a companion"""
        try:
            result = await self.session.execute(
                select(AnimalCompanion).where(AnimalCompanion.id == companion_id)
            )
            companion = result.scalar_one_or_none()

            if not companion:
                return {"success": False, "error": "Companion not found"}

            if companion.is_dead:
                return {"success": False, "error": "Companion is already dead"}

            old_hp = companion.current_hp
            companion.current_hp = max(0, companion.current_hp - damage_amount)

            # check if unconscious or dead
            if companion.current_hp == 0:
                companion.is_unconscious = True
                # animals die at 0 hp (no death saves)
                companion.is_dead = True

            await self.session.commit()

            return {
                "success": True,
                "old_hp": old_hp,
                "new_hp": companion.current_hp,
                "damage_taken": damage_amount,
                "is_unconscious": companion.is_unconscious,
                "is_dead": companion.is_dead
            }

        except Exception as e:
            await self.session.rollback()
            return {"success": False, "error": str(e)}

    async def get_character_companions(self, character_id: int, include_dead: bool = False) -> List[Dict[str, Any]]:
        """get all companions for a character"""
        try:
            query = select(AnimalCompanion).where(
                AnimalCompanion.character_id == character_id
            )

            if not include_dead:
                query = query.where(AnimalCompanion.is_dead == False)

            result = await self.session.execute(query)
            companions = result.scalars().all()

            companion_stats = []
            for companion in companions:
                stats = await self.get_companion_full_stats(companion.id)
                companion_stats.append(stats)

            return companion_stats

        except Exception as e:
            return {"error": str(e)}

    async def dismiss_companion(self, companion_id: int) -> Dict[str, Any]:
        """dismiss/release a companion (soft delete)"""
        try:
            result = await self.session.execute(
                select(AnimalCompanion).where(AnimalCompanion.id == companion_id)
            )
            companion = result.scalar_one_or_none()

            if not companion:
                return {"success": False, "error": "Companion not found"}

            # mark dismissed but keep record
            companion.is_dead = True
            companion.notes = f"Dismissed on {datetime.utcnow().strftime('%Y-%m-%d')}\n{companion.notes}"

            await self.session.commit()

            return {"success": True, "message": f"{companion.name} has been dismissed"}

        except Exception as e:
            await self.session.rollback()
            return {"success": False, "error": str(e)}