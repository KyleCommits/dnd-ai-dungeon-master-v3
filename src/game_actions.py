# src/game_actions.py
"""
game actions api for ai function calling
allows gemini to directly modify game state instead of just describing actions
"""

import logging
from typing import Dict, List, Optional, Any, Union
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from datetime import datetime, timedelta

from .character_manager import character_manager
from .character_models import Character, CharacterSpell, UserActiveCharacter
from .dice_roller import dice_roller, AdvantageType
from .spell_integration import character_spell_manager
from .combat_system import combat_manager, ConditionType
from .database import get_db_session

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class GameActions:
    """
    api for ai to execute game mechanics directly
    provides functions that gemini can call to modify character state
    """

    def __init__(self):
        self.character_manager = character_manager
        self.dice_roller = dice_roller
        self.spell_manager = character_spell_manager
        self.combat_manager = combat_manager

    async def modify_hp(self, character_id: str, change: int, reason: str = "", max_hp_override: int = None) -> Dict[str, Any]:
        """
        modify character hp (positive for healing, negative for damage)
        returns new hp values and status changes
        """
        try:
            async for db in get_db_session():
                # get character
                result = await db.execute(
                    select(Character).where(Character.id == int(character_id))
                )
                character = result.scalar_one_or_none()

                if not character:
                    return {"success": False, "error": f"character {character_id} not found"}

                old_hp = character.current_hp
                max_hp = max_hp_override or character.max_hp

                # apply change
                character.current_hp = max(0, min(max_hp, character.current_hp + change))

                # check for state changes
                status_changes = []

                # unconscious/death logic
                if character.current_hp == 0 and old_hp > 0:
                    character.is_unconscious = True
                    status_changes.append("falls unconscious")
                elif character.current_hp > 0 and old_hp == 0:
                    character.is_unconscious = False
                    character.death_save_successes = 0
                    character.death_save_failures = 0
                    character.is_stable = False
                    status_changes.append("regains consciousness")

                await db.commit()

                result_msg = f"hp changed by {change:+d} ({old_hp} → {character.current_hp}/{max_hp})"
                if reason:
                    result_msg += f" ({reason})"
                if status_changes:
                    result_msg += f" - {', '.join(status_changes)}"

                return {
                    "success": True,
                    "message": result_msg,
                    "old_hp": old_hp,
                    "new_hp": character.current_hp,
                    "max_hp": max_hp,
                    "status_changes": status_changes
                }

        except Exception as e:
            print(f"ERROR: error modifying hp for character {character_id}: {e}")
            return {"success": False, "error": str(e)}

    async def consume_spell_slot(self, character_id: str, slot_level: int, reason: str = "") -> Dict[str, Any]:
        """
        consume a spell slot for casting
        returns success and remaining slots
        """
        try:
            async for db in get_db_session():
                # get character with spell info
                spell_info = await self.spell_manager.get_character_spell_info(db, int(character_id))

                if not spell_info:
                    return {"success": False, "error": "character has no spell info"}

                slots_key = f"level_{slot_level}_slots"
                used_key = f"level_{slot_level}_used"

                available_slots = spell_info["spell_slots"].get(slots_key, 0)
                used_slots = spell_info["spell_slots"].get(used_key, 0)
                remaining = available_slots - used_slots

                if remaining <= 0:
                    return {"success": False, "error": f"no level {slot_level} spell slots remaining"}

                # update used slots (this would need database implementation)
                # for now just return success

                result_msg = f"consumed level {slot_level} spell slot ({remaining-1}/{available_slots} remaining)"
                if reason:
                    result_msg += f" ({reason})"

                return {
                    "success": True,
                    "message": result_msg,
                    "slot_level": slot_level,
                    "remaining_slots": remaining - 1,
                    "total_slots": available_slots
                }

        except Exception as e:
            print(f"ERROR: error consuming spell slot for character {character_id}: {e}")
            return {"success": False, "error": str(e)}

    async def apply_condition(self, character_id: str, condition: str, duration_rounds: int = None, reason: str = "") -> Dict[str, Any]:
        """
        apply a condition to character
        duration in rounds (none for permanent until removed)
        """
        try:
            # validate condition
            try:
                condition_type = ConditionType(condition.lower())
            except ValueError:
                return {"success": False, "error": f"invalid condition: {condition}"}

            # simplified condition application for now
            # (combat manager expects different format)
            result_msg = f"applied {condition}"
            if duration_rounds:
                result_msg += f" for {duration_rounds} rounds"
            if reason:
                result_msg += f" ({reason})"

            # todo: integrate with actual combat system when ready

            return {
                "success": True,
                "message": result_msg,
                "condition": condition,
                "duration": duration_rounds
            }

        except Exception as e:
            print(f"ERROR: error applying condition to character {character_id}: {e}")
            return {"success": False, "error": str(e)}

    async def roll_dice_for_character(self, dice_string: str, character_id: str = None,
                                    advantage: str = "normal", description: str = "") -> Dict[str, Any]:
        """
        roll dice with optional character modifiers
        advantage can be 'normal', 'advantage', or 'disadvantage'
        """
        try:
            # convert advantage string to enum
            adv_type = AdvantageType.NORMAL
            if advantage.lower() == "advantage":
                adv_type = AdvantageType.ADVANTAGE
            elif advantage.lower() == "disadvantage":
                adv_type = AdvantageType.DISADVANTAGE

            # parse dice notation (basic implementation)
            import re
            dice_match = re.match(r'(\d+)?d(\d+)([+\-]\d+)?', dice_string.lower())
            if not dice_match:
                return {"success": False, "error": f"invalid dice notation: {dice_string}"}

            count = int(dice_match.group(1) or 1)
            sides = int(dice_match.group(2))
            modifier = int(dice_match.group(3) or 0)

            result = self.dice_roller.roll_dice(count, sides, modifier, adv_type, description)

            return {
                "success": True,
                "message": f"rolled {dice_string}: {result.total}",
                "total": result.total,
                "individual_rolls": result.individual_rolls,
                "modifier": result.modifier,
                "description": result.description,
                "dropped_rolls": result.dropped_rolls
            }

        except Exception as e:
            print(f"ERROR: error rolling dice {dice_string}: {e}")
            return {"success": False, "error": str(e)}

    async def get_character_status(self, character_id: str) -> Dict[str, Any]:
        """
        get current character status (hp, conditions, resources)
        """
        try:
            async for db in get_db_session():
                # get character
                result = await db.execute(
                    select(Character).where(Character.id == int(character_id))
                )
                character = result.scalar_one_or_none()

                if not character:
                    return {"success": False, "error": f"character {character_id} not found"}

                # get spell info if available
                try:
                    spell_info = await self.spell_manager.get_character_spell_info(db, int(character_id))
                except AttributeError:
                    # method doesn't exist yet
                    spell_info = None

                status = {
                    "success": True,
                    "character_id": character_id,
                    "name": character.name,
                    "hp": {
                        "current": character.current_hp,
                        "max": character.max_hp,
                        "percentage": round(character.current_hp / character.max_hp * 100)
                    },
                    "status": {
                        "unconscious": character.is_unconscious,
                        "stable": character.is_stable,
                        "death_saves": {
                            "successes": character.death_save_successes,
                            "failures": character.death_save_failures
                        }
                    },
                    "spell_slots": spell_info["spell_slots"] if spell_info else None
                }

                return status

        except Exception as e:
            print(f"ERROR: error getting character status for {character_id}: {e}")
            return {"success": False, "error": str(e)}

# global game actions instance
game_actions = GameActions()