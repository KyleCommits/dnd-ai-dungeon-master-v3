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
from .database import async_session_scope
from .equipment_system import inventory_manager, Armor, ItemType

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
            async with async_session_scope() as db:
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

    async def _validate_spell_cast(self, character_id: str, spell_name: str) -> Dict[str, Any]:
        """Reject illegal casts (non-caster, unknown spell, not known/prepared)."""
        name = (spell_name or "").strip()
        if not name:
            return {"success": True}

        try:
            from .enhanced_spell_system import enhanced_spell_manager

            enhanced_spell_manager.initialize()
            spell = enhanced_spell_manager.get_spell(name)
            if not spell:
                return {
                    "success": False,
                    "error": f"spell not found: {name}",
                    "message": f"Cannot cast '{name}' — spell not in local rules DB.",
                }

            async with async_session_scope() as db:
                spell_data = await self.spell_manager.get_character_spells(db, int(character_id))
                if not spell_data:
                    return {"success": False, "error": f"character {character_id} not found"}

                if not spell_data.get("is_spellcaster"):
                    cls = spell_data.get("class_name", "this class")
                    return {
                        "success": False,
                        "error": f"{cls} cannot cast spells",
                        "message": f"{spell_data.get('character_name', 'Character')} ({cls}) cannot cast {spell.name}.",
                    }

                # Prefer character spellbook (known + prepared)
                known_prepared = False
                for level_spells in (spell_data.get("spells_by_level") or {}).values():
                    for entry in level_spells:
                        sp = entry.get("spell")
                        sp_name = getattr(sp, "name", None) or (sp.get("name") if isinstance(sp, dict) else None)
                        if sp_name and sp_name.lower() == spell.name.lower():
                            if entry.get("is_known") or entry.get("is_prepared"):
                                if spell.level == 0 or entry.get("is_prepared"):
                                    known_prepared = True
                                    break
                    if known_prepared:
                        break

                if known_prepared:
                    return {"success": True, "spell_name": spell.name, "spell_level": spell.level}

                # Fallback: on class list (spellbook may be empty for new casters)
                class_spells = enhanced_spell_manager.get_class_spells(
                    spell_data.get("class_name", ""), 9
                )
                on_list = any(s.name.lower() == spell.name.lower() for s in class_spells)
                if not on_list:
                    return {
                        "success": False,
                        "error": f"{spell.name} not available to {spell_data.get('class_name')}",
                        "message": (
                            f"{spell_data.get('character_name', 'Character')} cannot cast "
                            f"{spell.name} (not on class list / not known)."
                        ),
                    }

                # On class list but not prepared for prepared casters
                prepared_casters = {"Cleric", "Druid", "Paladin", "Wizard", "Artificer"}
                cls = spell_data.get("class_name", "")
                if cls in prepared_casters and spell.level > 0:
                    return {
                        "success": False,
                        "error": f"{spell.name} not prepared",
                        "message": f"{spell.name} is not prepared.",
                    }

                return {"success": True, "spell_name": spell.name, "spell_level": spell.level}
        except Exception as e:
            logger.exception("spell cast validation failed")
            return {"success": False, "error": str(e)}

    async def consume_spell_slot(
        self,
        character_id: str,
        slot_level: int,
        reason: str = "",
        spell_name: str = "",
    ) -> Dict[str, Any]:
        """Consume a spell slot for casting; validates spell legality when a name is given."""
        # Only enforce legality when spell_name is provided (AI casting path).
        # Bare slot consume (tests / legacy) without spell_name still works.
        if (spell_name or "").strip():
            legality = await self._validate_spell_cast(character_id, spell_name.strip())
            if not legality.get("success"):
                return legality

        try:
            async with async_session_scope() as db:
                result = await self.spell_manager.consume_spell_slot(db, int(character_id), slot_level)
                if result.get("success") and (spell_name or reason):
                    label = (spell_name or reason).strip()
                    result["message"] = f"{result.get('message', '')} ({label})".strip()
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

            async with async_session_scope() as db:
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
            async with async_session_scope() as db:
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
            async with async_session_scope() as db:
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
            async with async_session_scope() as db:
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
                        if catalog.item_type == ItemType.SHIELD:
                            has_shield = True
                        else:
                            equipped_armor = eq.item_name
                    elif "shield" in eq.item_name.lower():
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
            async with async_session_scope() as db:
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

    async def sync_character_hp_from_combat(
        self, character_id: str, current_hp: int, reason: str = ""
    ) -> Dict[str, Any]:
        """Set character DB HP to match combatant HP after combat damage/heal."""
        try:
            async with async_session_scope() as db:
                result = await db.execute(
                    select(Character).where(Character.id == int(character_id))
                )
                character = result.scalar_one_or_none()
                if not character:
                    return {"success": False, "error": f"character {character_id} not found"}

                old_hp = character.current_hp
                character.current_hp = max(0, min(character.max_hp, int(current_hp)))
                if character.current_hp == 0 and old_hp > 0:
                    character.is_unconscious = True
                elif character.current_hp > 0 and old_hp == 0:
                    character.is_unconscious = False
                    character.death_save_successes = 0
                    character.death_save_failures = 0
                    character.is_stable = False
                await db.commit()
                msg = f"synced HP {old_hp} → {character.current_hp}/{character.max_hp}"
                if reason:
                    msg += f" ({reason})"
                return {
                    "success": True,
                    "message": msg,
                    "old_hp": old_hp,
                    "new_hp": character.current_hp,
                    "max_hp": character.max_hp,
                }
        except Exception as e:
            print(f"ERROR: error syncing HP for character {character_id}: {e}")
            return {"success": False, "error": str(e)}

    async def start_combat_encounter(self, campaign_id: str, encounter_name: str) -> Dict[str, Any]:
        encounter = self.combat_manager.create_encounter(str(campaign_id), encounter_name)
        return {
            "success": True,
            "encounter_id": encounter.id,
            "encounter_name": encounter.name,
            "message": "Encounter created — add combatants then begin_combat",
        }

    async def add_monster_to_encounter(self, encounter_id: str, monster_name: str) -> Dict[str, Any]:
        from .monster_catalog import get_monster

        monster = get_monster(monster_name)
        if not monster:
            return {"success": False, "error": f"Unknown monster: {monster_name}"}
        combatant = self.combat_manager.add_monster_to_combat(encounter_id, monster)
        if not combatant:
            return {"success": False, "error": "Encounter not found"}
        return {
            "success": True,
            "combatant_id": combatant.id,
            "combatant_name": combatant.name,
            "hp": combatant.max_hp,
            "ac": combatant.ac,
            "attack_bonus": combatant.attack_bonus,
            "damage_dice": combatant.damage_dice,
        }

    async def add_character_to_encounter(self, encounter_id: str, character_id: str) -> Dict[str, Any]:
        try:
            async with async_session_scope() as db:
                character = await self.character_manager.get_character_full(db, int(character_id))
                if not character:
                    return {"success": False, "error": f"character {character_id} not found"}
                dex = character.abilities[0].dexterity if character.abilities else 10
                strength = character.abilities[0].strength if character.abilities else 10
                character_data = {
                    "id": character.id,
                    "name": character.name,
                    "max_hp": character.max_hp,
                    "current_hp": character.current_hp,
                    "armor_class": character.armor_class,
                    "dexterity_modifier": self.character_manager.get_ability_modifier(dex),
                    "strength_modifier": self.character_manager.get_ability_modifier(strength),
                    "proficiency_bonus": character.proficiency_bonus,
                }
                combatant = self.combat_manager.add_character_to_combat(encounter_id, character_data)
                if not combatant:
                    return {"success": False, "error": "Encounter not found"}
                return {
                    "success": True,
                    "combatant_id": combatant.id,
                    "combatant_name": combatant.name,
                    "character_id": combatant.character_id,
                    "attack_bonus": combatant.attack_bonus,
                    "damage_dice": combatant.damage_dice,
                }
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def begin_combat(self, encounter_id: str) -> Dict[str, Any]:
        return self.combat_manager.begin_combat(encounter_id)

    async def get_combat_status(self, encounter_id: str) -> Dict[str, Any]:
        status = self.combat_manager.get_combat_status(encounter_id)
        if "error" in status:
            return {"success": False, "error": status["error"]}
        status["success"] = True
        return status

    async def resolve_player_attack(
        self,
        character_id: str,
        target_name: str,
        method: str = "",
        target_kind: str = "",
        campaign_name: str = "",
        location: str = "",
        prior_weapon_options: Optional[list] = None,
    ) -> Dict[str, Any]:
        """
        Full attack resolution for solo play: d20+bonus vs AC, damage, object/creature effect.
        Weapon comes from inventory (chooser); backend rolls for the player.
        """
        from .attack_resolve import ability_mod
        from .scene_objects import scene_object_store
        from .campaign_state_manager import campaign_state_manager
        from .weapon_choose import choose_weapon_from_inventory, normalize_hint

        try:
            async with async_session_scope() as db:
                result = await db.execute(
                    select(Character)
                    .options(
                        selectinload(Character.abilities),
                        selectinload(Character.equipment),
                    )
                    .where(Character.id == int(character_id))
                )
                character = result.scalar_one_or_none()
                if not character:
                    return {"success": False, "error": f"character {character_id} not found"}

                abilities = character.abilities[0] if character.abilities else None
                str_score = getattr(abilities, "strength", 10) if abilities else 10
                dex_score = getattr(abilities, "dexterity", 10) if abilities else 10
                prof = int(getattr(character, "proficiency_bonus", 2) or 2)

                equipment = [
                    (eq.item_name, bool(eq.equipped))
                    for eq in (character.equipment or [])
                    if getattr(eq, "quantity", 1) and int(getattr(eq, "quantity", 1) or 0) > 0
                ]

                hint = method or ""
                numbered = None
                nh = normalize_hint(hint)
                if nh.isdigit():
                    numbered = int(nh)

                choice = choose_weapon_from_inventory(
                    equipment,
                    method_hint=hint,
                    numbered_pick=numbered,
                    prior_options=prior_weapon_options,
                )
                if choice.status != "ok":
                    return {
                        "success": False,
                        "needs_clarify": True,
                        "message": choice.prompt or "Which weapon?",
                        "options": choice.options,
                        "target_name": (target_name or "object").strip(),
                    }

                use_dex = choice.finesse and ability_mod(dex_score) > ability_mod(str_score)
                if choice.ability == "dexterity":
                    use_dex = True
                abl_mod = ability_mod(dex_score if use_dex else str_score)
                # Fighters/martial: assume weapon proficiency for inventory weapons + unarmed
                attack_bonus = abl_mod + prof
                damage_dice = choice.damage_dice or "1d4"
                weapon_label = choice.weapon_name or "unarmed"

                kind = (target_kind or "").strip().lower()
                tname = (target_name or "object").strip()

                # Creature path: match active encounter combatant by name
                if kind != "object":
                    for enc in getattr(self.combat_manager, "active_encounters", {}).values():
                        if not getattr(enc, "is_active", False):
                            continue
                        for c in getattr(enc, "combatants", []) or []:
                            if c.name.lower() == tname.lower() and not getattr(c, "is_player", False):
                                attacker = next(
                                    (
                                        x
                                        for x in enc.combatants
                                        if getattr(x, "character_id", None) == int(character_id)
                                    ),
                                    None,
                                )
                                if attacker:
                                    return await self.resolve_attack(enc.id, attacker.id, c.id)
                                kind = "creature"
                                break

                if kind != "creature":
                    kind = "object"

                atk_roll = self.dice_roller.roll_dice(
                    1, 20, attack_bonus, AdvantageType.NORMAL, "attack"
                )
                attack_total = atk_roll.total

                if kind == "object":
                    state = campaign_state_manager.current_state
                    camp = campaign_name or (state.campaign_name if state else "default")
                    loc = location or (state.location if state else "here")
                    obj = scene_object_store.get_or_create(camp, loc, tname)
                    if obj.destroyed:
                        return {
                            "success": True,
                            "hit": False,
                            "already_destroyed": True,
                            "target_kind": "object",
                            "target_name": obj.name,
                            "weapon": weapon_label,
                            "attack_total": attack_total,
                            "ac": obj.ac,
                            "message": f"The {obj.name} is already destroyed.",
                        }

                    hit = attack_total >= obj.ac
                    damage = 0
                    damage_detail = ""
                    if hit:
                        dmg_match = re.match(r"(\d+)?d(\d+)", damage_dice.lower())
                        count = int(dmg_match.group(1) or 1) if dmg_match else 1
                        sides = int(dmg_match.group(2)) if dmg_match else 4
                        dmg_roll = self.dice_roller.roll_dice(
                            count, sides, abl_mod, AdvantageType.NORMAL, "damage"
                        )
                        damage = max(0, dmg_roll.total)
                        damage_detail = f"{damage_dice}+{abl_mod}"
                        obj.apply_damage(damage)

                    if hit and obj.destroyed:
                        flavor = f"The {obj.name} shatters apart."
                    elif hit:
                        flavor = f"Your {weapon_label} bites into the {obj.name}."
                    else:
                        flavor = f"You swing your {weapon_label} and glance off the {obj.name}."

                    return {
                        "success": True,
                        "hit": hit,
                        "target_kind": "object",
                        "target_name": obj.name,
                        "method": weapon_label,
                        "weapon": weapon_label,
                        "from_inventory": choice.from_inventory,
                        "attack_bonus": attack_bonus,
                        "attack_total": attack_total,
                        "d20": atk_roll.individual_rolls[0] if atk_roll.individual_rolls else None,
                        "ac": obj.ac,
                        "damage": damage if hit else None,
                        "damage_detail": damage_detail if hit else None,
                        "object_hp_remaining": obj.current_hp,
                        "object_max_hp": obj.max_hp,
                        "destroyed": obj.destroyed,
                        "message": flavor,
                    }

                return {"success": False, "error": f"could not resolve target '{tname}'"}
        except Exception as e:
            logger.exception("resolve_player_attack failed")
            return {"success": False, "error": str(e)}

    async def resolve_attack(
        self, encounter_id: str, attacker_id: str, target_id: str
    ) -> Dict[str, Any]:
        result = self.combat_manager.resolve_attack(encounter_id, attacker_id, target_id)
        if not result.get("success"):
            return result
        if result.get("hit") and result.get("character_id") is not None:
            sync = await self.sync_character_hp_from_combat(
                str(result["character_id"]),
                result["target_hp"],
                reason=result.get("message", "combat attack"),
            )
            result["db_sync"] = sync
        return result

    async def next_combat_turn(self, encounter_id: str) -> Dict[str, Any]:
        encounter = self.combat_manager.get_encounter(encounter_id)
        if not encounter:
            return {"success": False, "error": "Encounter not found"}
        if not encounter.is_active:
            return {"success": False, "error": "Combat is not active — call begin_combat first"}
        encounter.next_turn()
        current = encounter.get_current_combatant()
        return {
            "success": True,
            "round": encounter.current_round,
            "turn": encounter.current_turn,
            "current_combatant": current.name if current else None,
            "current_combatant_id": current.id if current else None,
        }

    async def end_combat(self, encounter_id: str) -> Dict[str, Any]:
        return self.combat_manager.end_and_remove_encounter(encounter_id)

    async def lookup_spell(self, spell_name: str) -> Dict[str, Any]:
        """Read-only spell lookup from local spells.db (no invented stats)."""
        try:
            from .enhanced_spell_system import enhanced_spell_manager

            enhanced_spell_manager.initialize()
            spell = enhanced_spell_manager.get_spell(spell_name)
            if not spell:
                return {"success": False, "error": f"spell not found: {spell_name}"}
            return {
                "success": True,
                "name": spell.name,
                "level": spell.level,
                "school": spell.school,
                "casting_time": spell.casting_time,
                "range": spell.range,
                "duration": spell.duration,
                "components": spell.components,
                "concentration": spell.concentration,
                "ritual": spell.ritual,
                "description": spell.description,
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def lookup_monster(self, monster_name: str) -> Dict[str, Any]:
        """Read-only monster lookup from local rules.db / catalog."""
        try:
            from .monster_catalog import get_monster

            monster = get_monster(monster_name)
            if not monster:
                return {"success": False, "error": f"monster not found: {monster_name}"}
            return {"success": True, **monster}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def lookup_item(self, item_name: str) -> Dict[str, Any]:
        """Read-only equipment lookup from local rules.db / catalogs."""
        try:
            from .rules_db import rules_db

            row = rules_db.get_item(item_name)
            if row:
                return {"success": True, **row}
            known = inventory_manager.get_item(item_name)
            if not known:
                return {"success": False, "error": f"item not found: {item_name}"}
            data = {
                "success": True,
                "name": known.name,
                "item_type": getattr(known.item_type, "value", str(known.item_type)),
                "cost": f"{getattr(known, 'cost_gp', '?')} gp",
                "weight": f"{getattr(known, 'weight_lb', '?')} lb.",
                "description": getattr(known, "description", ""),
            }
            if isinstance(known, Armor):
                data["base_ac"] = known.base_ac
                data["armor_category"] = known.armor_type.value
                data["max_dex_bonus"] = known.max_dex_bonus
            return data
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def update_npc_relationship(
        self,
        npc_name: str,
        trust_delta: int = 0,
        note: str = "",
        reason: str = "",
    ) -> Dict[str, Any]:
        """Adjust NPC trust in campaign world state (Postgres-backed)."""
        from .campaign_state_manager import campaign_state_manager

        if not campaign_state_manager.current_state:
            return {"success": False, "error": "no campaign loaded"}
        note_text = note or reason or ""
        ok = await campaign_state_manager.update_npc_relationship(
            npc_name, note_text, int(trust_delta)
        )
        if not ok:
            return {"success": False, "error": "failed to update relationship"}
        key = npc_name.lower().replace(" ", "_")
        npc = campaign_state_manager.current_state.npc_relationships.get(key)
        return {
            "success": True,
            "message": f"{npc_name}: trust {npc.trust_level} ({npc.relationship})",
            "npc_name": npc.name if npc else npc_name,
            "trust_level": npc.trust_level if npc else None,
            "relationship": npc.relationship if npc else None,
        }

    async def update_plot_thread(
        self,
        thread_id: str,
        status: str = None,
        note: str = "",
        name: str = None,
        create_if_missing: bool = False,
    ) -> Dict[str, Any]:
        """Update or create a plot thread in campaign world state."""
        from .campaign_state_manager import campaign_state_manager

        if not campaign_state_manager.current_state:
            return {"success": False, "error": "no campaign loaded"}
        ok = await campaign_state_manager.update_plot_thread(
            thread_id,
            status=status,
            note=note or None,
            name=name,
            create_if_missing=bool(create_if_missing),
        )
        if not ok:
            return {"success": False, "error": f"plot thread not found: {thread_id}"}
        return {
            "success": True,
            "message": f"plot thread '{thread_id}' updated" + (f" -> {status}" if status else ""),
            "thread_id": thread_id,
            "status": status,
        }

    async def set_location(self, location: str, reason: str = "") -> Dict[str, Any]:
        """Set current party location in campaign world state."""
        from .campaign_state_manager import campaign_state_manager

        if not campaign_state_manager.current_state:
            return {"success": False, "error": "no campaign loaded"}
        if not location:
            return {"success": False, "error": "location required"}
        ok = await campaign_state_manager.set_location(location)
        if not ok:
            return {"success": False, "error": "failed to set location"}
        msg = f"location set to {location}"
        if reason:
            msg += f" ({reason})"
        return {"success": True, "message": msg, "location": location}

    async def record_plot_event(self, event: str, location: str = None) -> Dict[str, Any]:
        """Record a player/story action against active plot threads."""
        from .campaign_state_manager import campaign_state_manager

        if not campaign_state_manager.current_state:
            return {"success": False, "error": "no campaign loaded"}
        ok = await campaign_state_manager.update_player_action(event, location=location)
        if not ok:
            return {"success": False, "error": "failed to record event"}
        return {
            "success": True,
            "message": f"recorded: {event}",
            "location": campaign_state_manager.current_state.location,
        }


# global game actions instance
game_actions = GameActions()
