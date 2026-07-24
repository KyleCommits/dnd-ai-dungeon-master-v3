# src/game_actions.py
"""
game actions api for ai function calling
allows gemini to directly modify game state instead of just describing actions
"""

import json
import logging
import re
from typing import Dict, Optional, Any

from sqlalchemy import select, and_
from sqlalchemy.orm import selectinload

from .character_manager import character_manager
from .character_models import Character, CharacterEquipment
from .dice_roller import dice_roller, AdvantageType
from .spell_integration import character_spell_manager
from .combat_system import combat_manager, ConditionType
from .database import get_db_session
from .equipment_system import inventory_manager, Armor

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
                result = await db.execute(
                    select(Character).where(Character.id == int(character_id))
                )
                character = result.scalar_one_or_none()

                if not character:
                    return {"success": False, "error": f"character {character_id} not found"}

                old_hp = character.current_hp
                max_hp = max_hp_override or character.max_hp

                character.current_hp = max(0, min(max_hp, character.current_hp + change))

                status_changes = []

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
        """consume a spell slot for casting; persists used slots"""
        try:
            async for db in get_db_session():
                result = await self.spell_manager.consume_spell_slot(db, int(character_id), slot_level)
                if result.get("success") and reason:
                    result["message"] = f"{result.get('message', '')} ({reason})"
                return result
        except Exception as e:
            print(f"ERROR: error consuming spell slot for character {character_id}: {e}")
            return {"success": False, "error": str(e)}

    async def apply_condition(self, character_id: str, condition: str, duration_rounds: int = None, reason: str = "") -> Dict[str, Any]:
        """apply a condition to character and persist on the character row"""
        try:
            try:
                condition_type = ConditionType(condition.lower())
            except ValueError:
                return {"success": False, "error": f"invalid condition: {condition}"}

            async for db in get_db_session():
                result = await db.execute(
                    select(Character).where(Character.id == int(character_id))
                )
                character = result.scalar_one_or_none()
                if not character:
                    return {"success": False, "error": f"character {character_id} not found"}

                try:
                    conditions = json.loads(character.conditions_json or "[]")
                    if not isinstance(conditions, list):
                        conditions = []
                except (json.JSONDecodeError, TypeError):
                    conditions = []

                entry = {"name": condition_type.value, "duration_rounds": duration_rounds}
                conditions = [c for c in conditions if c.get("name") != condition_type.value]
                conditions.append(entry)
                character.conditions_json = json.dumps(conditions)
                await db.commit()

                result_msg = f"applied {condition_type.value}"
                if duration_rounds:
                    result_msg += f" for {duration_rounds} rounds"
                if reason:
                    result_msg += f" ({reason})"

                return {
                    "success": True,
                    "message": result_msg,
                    "condition": condition_type.value,
                    "duration": duration_rounds,
                    "conditions": conditions,
                }
        except Exception as e:
            print(f"ERROR: error applying condition to character {character_id}: {e}")
            return {"success": False, "error": str(e)}

    async def trigger_rest(self, character_id: str, rest_type: str = "long", reason: str = "") -> Dict[str, Any]:
        """Trigger a short or long rest for a character (AI-callable)."""
        try:
            if rest_type not in ("short", "long"):
                return {"success": False, "error": "rest_type must be 'short' or 'long'"}
            async for db in get_db_session():
                result = await self.spell_manager.character_rest(db, int(character_id), rest_type)
                if result.get("success") and reason:
                    result["message"] = f"{result.get('message', '')} ({reason})"
                return result
        except Exception as e:
            print(f"ERROR: error triggering rest for character {character_id}: {e}")
            return {"success": False, "error": str(e)}

    async def update_inventory(
        self, character_id: str, item: str, quantity: int = 1, reason: str = ""
    ) -> Dict[str, Any]:
        """Add or remove inventory items (quantity can be negative)."""
        try:
            async for db in get_db_session():
                result = await db.execute(
                    select(Character).where(Character.id == int(character_id))
                )
                character = result.scalar_one_or_none()
                if not character:
                    return {"success": False, "error": f"character {character_id} not found"}

                eq_result = await db.execute(
                    select(CharacterEquipment).where(
                        and_(
                            CharacterEquipment.character_id == int(character_id),
                            CharacterEquipment.item_name == item,
                        )
                    )
                )
                existing = eq_result.scalar_one_or_none()

                if existing:
                    existing.quantity = max(0, existing.quantity + quantity)
                    if existing.quantity == 0:
                        await db.delete(existing)
                        await db.commit()
                        msg = f"removed {item}"
                    else:
                        await db.commit()
                        msg = f"updated {item} quantity to {existing.quantity}"
                else:
                    if quantity <= 0:
                        return {"success": False, "error": f"{item} not in inventory"}
                    db.add(
                        CharacterEquipment(
                            character_id=int(character_id),
                            item_name=item,
                            quantity=quantity,
                            equipped=False,
                        )
                    )
                    await db.commit()
                    known = inventory_manager.get_item(item)
                    msg = f"added {quantity} x {item}" + ("" if known else " (custom item)")

                if reason:
                    msg += f" ({reason})"
                return {"success": True, "message": msg, "item": item, "quantity_delta": quantity}
        except Exception as e:
            print(f"ERROR: error updating inventory for character {character_id}: {e}")
            return {"success": False, "error": str(e)}

    async def equip_item(self, character_id: str, item: str, equipped: bool = True, reason: str = "") -> Dict[str, Any]:
        """Equip or unequip an inventory item and recalculate AC when relevant."""
        try:
            async for db in get_db_session():
                result = await db.execute(
                    select(Character)
                    .options(selectinload(Character.abilities), selectinload(Character.equipment))
                    .where(Character.id == int(character_id))
                )
                character = result.scalar_one_or_none()
                if not character:
                    return {"success": False, "error": f"character {character_id} not found"}

                target = None
                for eq in character.equipment:
                    if eq.item_name.lower() == item.lower():
                        target = eq
                        break
                if not target:
                    return {"success": False, "error": f"{item} not in inventory"}

                target.equipped = equipped

                dex_mod = 0
                if character.abilities:
                    dex = character.abilities[0].dexterity
                    dex_mod = (dex - 10) // 2

                equipped_armor = None
                has_shield = False
                for eq in character.equipment:
                    if not eq.equipped:
                        continue
                    catalog = inventory_manager.get_item(eq.item_name)
                    if catalog and isinstance(catalog, Armor):
                        equipped_armor = eq.item_name
                    elif eq.item_name.lower() == "shield":
                        has_shield = True

                character.armor_class = inventory_manager.calculate_ac(
                    {
                        "dex_modifier": dex_mod,
                        "equipped_armor": equipped_armor,
                        "has_shield": has_shield,
                    }
                )
                await db.commit()

                action = "equipped" if equipped else "unequipped"
                msg = f"{action} {target.item_name}; AC is now {character.armor_class}"
                if reason:
                    msg += f" ({reason})"
                return {
                    "success": True,
                    "message": msg,
                    "item": target.item_name,
                    "equipped": equipped,
                    "armor_class": character.armor_class,
                }
        except Exception as e:
            print(f"ERROR: error equipping item for character {character_id}: {e}")
            return {"success": False, "error": str(e)}

    async def unequip_item(self, character_id: str, item: str, reason: str = "") -> Dict[str, Any]:
        return await self.equip_item(character_id, item, equipped=False, reason=reason)

    async def roll_dice_for_character(self, dice_string: str, character_id: str = None,
                                    advantage: str = "normal", description: str = "") -> Dict[str, Any]:
        """roll dice with optional character modifiers"""
        try:
            adv_type = AdvantageType.NORMAL
            if advantage.lower() == "advantage":
                adv_type = AdvantageType.ADVANTAGE
            elif advantage.lower() == "disadvantage":
                adv_type = AdvantageType.DISADVANTAGE

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
        """get current character status (hp, conditions, resources)"""
        try:
            async for db in get_db_session():
                result = await db.execute(
                    select(Character).where(Character.id == int(character_id))
                )
                character = result.scalar_one_or_none()

                if not character:
                    return {"success": False, "error": f"character {character_id} not found"}

                try:
                    spell_info = await self.spell_manager.get_character_spell_info(db, int(character_id))
                except AttributeError:
                    spell_info = None

                try:
                    conditions = json.loads(character.conditions_json or "[]")
                    if not isinstance(conditions, list):
                        conditions = []
                except (json.JSONDecodeError, TypeError):
                    conditions = []

                status = {
                    "success": True,
                    "character_id": character_id,
                    "name": character.name,
                    "hp": {
                        "current": character.current_hp,
                        "max": character.max_hp,
                        "percentage": round(character.current_hp / character.max_hp * 100) if character.max_hp else 0
                    },
                    "armor_class": character.armor_class,
                    "conditions": conditions,
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
