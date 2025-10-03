# src/enhanced_character_api.py
"""
Enhanced Character API with all new systems integrated
Provides endpoints for spells, equipment, combat, and progression
"""

from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from typing import Dict, List, Optional, Any, Union
from .database import get_db_session
from .character_manager import character_manager
from .spell_system import spell_manager, SpellSlotManager
from .equipment_system import inventory_manager
from .level_progression import progression_manager
from .combat_system import combat_manager, ConditionType, DamageType, Condition

router = APIRouter()

# Enhanced request models
class SpellCastRequest(BaseModel):
    spell_name: str
    spell_level: int
    target_ids: Optional[List[str]] = None
    upcast: bool = False

class EquipmentChangeRequest(BaseModel):
    item_name: str
    equipped: bool

class LevelUpRequest(BaseModel):
    hit_point_roll: Optional[int] = None
    ability_score_improvements: Optional[Dict[str, int]] = None
    feat_choice: Optional[str] = None
    spell_choices: Optional[List[str]] = None

class CombatActionRequest(BaseModel):
    action_type: str  # "attack", "cast_spell", "use_item", "dash", "dodge", "help", "hide", "ready", "search"
    target_id: Optional[str] = None
    weapon_name: Optional[str] = None
    spell_name: Optional[str] = None
    spell_level: Optional[int] = None

class DamageRequest(BaseModel):
    combatant_id: str
    damage_amount: int
    damage_type: str
    source: str = ""

class ConditionRequest(BaseModel):
    combatant_id: str
    condition_type: str
    duration_rounds: Optional[int] = None
    source: str = ""

# Spell Management Endpoints

@router.get("/api/characters/{character_id}/spells")
async def get_character_spells(character_id: int, db: AsyncSession = Depends(get_db_session)):
    """Get character's known/prepared spells and spell slots"""
    character = await character_manager.get_character_full(db, character_id)
    if not character:
        raise HTTPException(status_code=404, detail="Character not found")

    # Get class spell list
    class_spells = spell_manager.list_manager.get_class_spells(character.class_name, 9)

    # Get spell slots
    slot_manager = SpellSlotManager()
    caster_types = {
        "Bard": "full", "Cleric": "full", "Druid": "full", "Sorcerer": "full", "Wizard": "full",
        "Paladin": "half", "Ranger": "half", "Warlock": "warlock"
    }
    caster_type = caster_types.get(character.class_name, "none")

    if caster_type != "none":
        spell_slots = slot_manager.get_spell_slots(caster_type, character.level)
    else:
        spell_slots = [0] * 9

    # Get known spells from database
    known_spells = []
    for spell_obj in character.spells:
        spell_data = spell_manager.get_spell(spell_obj.spell_name)
        if spell_data:
            known_spells.append({
                "name": spell_data.name,
                "level": spell_data.level,
                "school": spell_data.school.value,
                "casting_time": spell_data.casting_time.value,
                "range": spell_data.range.value,
                "components": spell_data.components,
                "duration": spell_data.duration,
                "description": spell_data.description,
                "prepared": spell_obj.prepared,
                "uses_remaining": spell_obj.uses_today
            })

    return {
        "character_name": character.name,
        "class_name": character.class_name,
        "level": character.level,
        "spellcasting_ability": "Intelligence" if character.class_name == "Wizard" else "Wisdom" if character.class_name in ["Cleric", "Druid"] else "Charisma",
        "spell_slots": {
            f"level_{i+1}": slots for i, slots in enumerate(spell_slots) if slots > 0
        },
        "known_spells": known_spells,
        "available_spells": class_spells[:20]  # Limit for response size
    }

@router.post("/api/characters/{character_id}/cast-spell")
async def cast_spell(character_id: int, request: SpellCastRequest, db: AsyncSession = Depends(get_db_session)):
    """Cast a spell with the character"""
    character = await character_manager.get_character_full(db, character_id)
    if not character:
        raise HTTPException(status_code=404, detail="Character not found")

    spell = spell_manager.get_spell(request.spell_name)
    if not spell:
        raise HTTPException(status_code=404, detail="Spell not found")

    # Check if character knows the spell
    character_spell = next((s for s in character.spells if s.spell_name == request.spell_name), None)
    if not character_spell:
        raise HTTPException(status_code=400, detail="Character doesn't know this spell")

    # Calculate spell effects
    ability_mod = 0  # Would get from character's abilities
    spell_effects = spell_manager.calculate_spell_damage(
        spell, character.level, request.spell_level, ability_mod
    )

    return {
        "spell_cast": spell.name,
        "caster": character.name,
        "spell_level": request.spell_level,
        "effects": spell_effects,
        "targets": request.target_ids or [],
        "success": True
    }

# Equipment Management Endpoints

@router.get("/api/characters/{character_id}/equipment")
async def get_character_equipment(character_id: int, db: AsyncSession = Depends(get_db_session)):
    """Get character's equipment and inventory"""
    character = await character_manager.get_character_full(db, character_id)
    if not character:
        raise HTTPException(status_code=404, detail="Character not found")

    equipment_list = []
    for item in character.equipment:
        item_data = inventory_manager.get_item(item.item_name)
        equipment_list.append({
            "name": item.item_name,
            "quantity": item.quantity,
            "equipped": item.equipped,
            "attuned": item.attuned,
            "weight": item_data.weight_lb if item_data else 0,
            "cost": item_data.cost_gp if item_data else 0,
            "type": item_data.item_type.value if item_data else "unknown"
        })

    # Calculate carrying capacity
    str_score = character.abilities[0].strength if character.abilities else 10
    carrying_info = inventory_manager.calculate_carrying_capacity(str_score)

    return {
        "character_name": character.name,
        "equipment": equipment_list,
        "carrying_capacity": carrying_info,
        "total_weight": sum(item["weight"] * item["quantity"] for item in equipment_list)
    }

@router.post("/api/characters/{character_id}/equip-item")
async def equip_item(character_id: int, request: EquipmentChangeRequest, db: AsyncSession = Depends(get_db_session)):
    """Equip or unequip an item"""
    character = await character_manager.get_character_full(db, character_id)
    if not character:
        raise HTTPException(status_code=404, detail="Character not found")

    # Find the item in character's equipment
    for item in character.equipment:
        if item.item_name == request.item_name:
            item.equipped = request.equipped
            await db.commit()

            # Recalculate AC if armor changed
            if request.equipped:
                item_data = inventory_manager.get_item(request.item_name)
                if item_data and hasattr(item_data, 'armor_type'):
                    # Update character's AC
                    dex_mod = character_manager.get_ability_modifier(character.abilities[0].dexterity)
                    new_ac = inventory_manager.calculate_ac({
                        "dex_modifier": dex_mod,
                        "equipped_armor": request.item_name,
                        "has_shield": any(e.item_name == "Shield" and e.equipped for e in character.equipment)
                    })
                    character.armor_class = new_ac
                    await db.commit()

            return {
                "success": True,
                "item_name": request.item_name,
                "equipped": request.equipped,
                "new_ac": character.armor_class
            }

    raise HTTPException(status_code=404, detail="Item not found in character's equipment")

@router.get("/api/characters/{character_id}/weapon-stats")
async def get_weapon_stats(character_id: int, weapon_name: str, db: AsyncSession = Depends(get_db_session)):
    """Get attack and damage stats for a weapon"""
    character = await character_manager.get_character_full(db, character_id)
    if not character:
        raise HTTPException(status_code=404, detail="Character not found")

    character_data = {
        "str_modifier": character_manager.get_ability_modifier(character.abilities[0].strength),
        "dex_modifier": character_manager.get_ability_modifier(character.abilities[0].dexterity),
        "proficiency_bonus": character.proficiency_bonus,
        "weapon_proficiencies": []  # Would need to get from character features
    }

    weapon_stats = inventory_manager.calculate_attack_bonus(character_data, weapon_name)
    return weapon_stats

# Level Progression Endpoints

@router.get("/api/characters/{character_id}/level-up-preview")
async def preview_level_up(character_id: int, db: AsyncSession = Depends(get_db_session)):
    """Preview what happens when character levels up"""
    character = await character_manager.get_character_full(db, character_id)
    if not character:
        raise HTTPException(status_code=404, detail="Character not found")

    character_data = {
        "level": character.level,
        "class_name": character.class_name,
        "constitution_modifier": character_manager.get_ability_modifier(character.abilities[0].constitution)
    }

    level_up_info = progression_manager.calculate_level_up(character_data)
    return level_up_info

@router.post("/api/characters/{character_id}/level-up")
async def level_up_character(character_id: int, request: LevelUpRequest, db: AsyncSession = Depends(get_db_session)):
    """Level up the character"""
    character = await character_manager.get_character_full(db, character_id)
    if not character:
        raise HTTPException(status_code=404, detail="Character not found")

    # Increase level
    character.level += 1

    # Add hit points
    if request.hit_point_roll:
        hp_gain = request.hit_point_roll + character_manager.get_ability_modifier(character.abilities[0].constitution)
    else:
        # Use average
        hit_die_map = {"Barbarian": 12, "Fighter": 10, "Wizard": 6, "Rogue": 8}
        hit_die = hit_die_map.get(character.class_name, 8)
        hp_gain = (hit_die // 2) + 1 + character_manager.get_ability_modifier(character.abilities[0].constitution)

    character.max_hp += max(1, hp_gain)
    character.current_hp += max(1, hp_gain)

    # Update proficiency bonus
    character.proficiency_bonus = character_manager.get_proficiency_bonus(character.level)

    # Apply ability score improvements
    if request.ability_score_improvements:
        abilities = character.abilities[0]
        for ability, increase in request.ability_score_improvements.items():
            current_score = getattr(abilities, ability.lower())
            setattr(abilities, ability.lower(), min(20, current_score + increase))

    await db.commit()

    return {
        "success": True,
        "new_level": character.level,
        "hp_gained": hp_gain,
        "new_max_hp": character.max_hp,
        "new_proficiency_bonus": character.proficiency_bonus
    }

@router.post("/api/characters/{character_id}/award-xp")
async def award_experience(character_id: int, xp_amount: int, db: AsyncSession = Depends(get_db_session)):
    """Award experience points to character"""
    character = await character_manager.get_character_full(db, character_id)
    if not character:
        raise HTTPException(status_code=404, detail="Character not found")

    # Get current progression data
    progression_data = character.progression[0] if character.progression else None
    if not progression_data:
        raise HTTPException(status_code=400, detail="Character progression data not found")

    character_data = {
        "experience_points": progression_data.experience_points,
        "level": character.level,
        "class_name": character.class_name,
        "constitution_modifier": character_manager.get_ability_modifier(character.abilities[0].constitution)
    }

    xp_result = progression_manager.award_experience(character_data, xp_amount)

    # Update database
    progression_data.experience_points = xp_result["new_total_xp"]
    if xp_result["level_up"]:
        progression_data.level_up_pending = True

    await db.commit()

    return xp_result

# Combat Management Endpoints

@router.post("/api/campaigns/{campaign_id}/combat/start")
async def start_combat(campaign_id: int, encounter_name: str):
    """Start a new combat encounter"""
    encounter = combat_manager.create_encounter(str(campaign_id), encounter_name)
    encounter.start_combat()

    return {
        "encounter_id": encounter.id,
        "encounter_name": encounter.name,
        "status": "Combat started",
        "round": encounter.current_round,
        "turn": encounter.current_turn
    }

@router.post("/api/combat/{encounter_id}/add-character")
async def add_character_to_combat(encounter_id: str, character_id: int, db: AsyncSession = Depends(get_db_session)):
    """Add a character to combat"""
    character = await character_manager.get_character_full(db, character_id)
    if not character:
        raise HTTPException(status_code=404, detail="Character not found")

    character_data = {
        "id": character.id,
        "name": character.name,
        "max_hp": character.max_hp,
        "current_hp": character.current_hp,
        "armor_class": character.armor_class,
        "dexterity_modifier": character_manager.get_ability_modifier(character.abilities[0].dexterity)
    }

    combatant = combat_manager.add_character_to_combat(encounter_id, character_data)
    if not combatant:
        raise HTTPException(status_code=404, detail="Combat encounter not found")

    return {
        "success": True,
        "combatant_name": combatant.name,
        "initiative": combatant.initiative
    }

@router.post("/api/combat/{encounter_id}/damage")
async def apply_damage(encounter_id: str, request: DamageRequest):
    """Apply damage to a combatant"""
    try:
        damage_type = DamageType(request.damage_type)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid damage type")

    result = combat_manager.apply_damage_to_combatant(
        encounter_id, request.combatant_id, request.damage_amount, damage_type, request.source
    )

    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])

    return result

@router.post("/api/combat/{encounter_id}/heal")
async def apply_healing(encounter_id: str, combatant_id: str, healing_amount: int):
    """Heal a combatant"""
    result = combat_manager.heal_combatant(encounter_id, combatant_id, healing_amount)

    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])

    return result

@router.post("/api/combat/{encounter_id}/condition")
async def apply_condition(encounter_id: str, request: ConditionRequest):
    """Apply a condition to a combatant"""
    try:
        condition_type = ConditionType(request.condition_type)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid condition type")

    condition = Condition(
        condition_type=condition_type,
        duration_rounds=request.duration_rounds,
        source=request.source
    )

    result = combat_manager.apply_condition(encounter_id, request.combatant_id, condition)

    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])

    return result

@router.delete("/api/combat/{encounter_id}/condition")
async def remove_condition(encounter_id: str, combatant_id: str, condition_type: str):
    """Remove a condition from a combatant"""
    try:
        condition_enum = ConditionType(condition_type)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid condition type")

    result = combat_manager.remove_condition(encounter_id, combatant_id, condition_enum)

    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])

    return result

@router.get("/api/combat/{encounter_id}/status")
async def get_combat_status(encounter_id: str):
    """Get current combat status"""
    result = combat_manager.get_combat_status(encounter_id)

    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])

    return result

@router.post("/api/combat/{encounter_id}/next-turn")
async def next_turn(encounter_id: str):
    """Advance to the next turn in combat"""
    encounter = combat_manager.get_encounter(encounter_id)
    if not encounter:
        raise HTTPException(status_code=404, detail="Encounter not found")

    encounter.next_turn()
    current_combatant = encounter.get_current_combatant()

    return {
        "success": True,
        "round": encounter.current_round,
        "turn": encounter.current_turn,
        "current_combatant": current_combatant.name if current_combatant else None
    }

# Utility Endpoints

@router.get("/api/spells/search")
async def search_spells(level: Optional[int] = None, school: Optional[str] = None, class_name: Optional[str] = None):
    """Search for spells by criteria"""
    search_params = {}
    if level is not None:
        search_params["level"] = level
    if school:
        from .spell_system import SpellSchool
        try:
            search_params["school"] = SpellSchool(school.upper())
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid spell school")
    if class_name:
        search_params["class_name"] = class_name

    spells = spell_manager.search_spells(**search_params)

    return {
        "spells": [
            {
                "name": spell.name,
                "level": spell.level,
                "school": spell.school.value,
                "casting_time": spell.casting_time.value,
                "range": spell.range.value,
                "duration": spell.duration,
                "description": spell.description
            } for spell in spells
        ]
    }

@router.get("/api/equipment/search")
async def search_equipment(item_type: Optional[str] = None, name: Optional[str] = None):
    """Search for equipment"""
    from .equipment_system import WeaponDatabase, ArmorDatabase, MagicItemDatabase

    results = []

    # Search weapons
    for weapon in WeaponDatabase.WEAPONS.values():
        if (not item_type or item_type.lower() == "weapon") and (not name or name.lower() in weapon.name.lower()):
            results.append({
                "name": weapon.name,
                "type": "weapon",
                "cost": weapon.cost_gp,
                "weight": weapon.weight_lb,
                "damage": weapon.damage.dice,
                "damage_type": weapon.damage.damage_type,
                "properties": weapon.properties
            })

    # Search armor
    for armor in ArmorDatabase.ARMOR.values():
        if (not item_type or item_type.lower() == "armor") and (not name or name.lower() in armor.name.lower()):
            results.append({
                "name": armor.name,
                "type": "armor",
                "cost": armor.cost_gp,
                "weight": armor.weight_lb,
                "ac": getattr(armor, 'base_ac', None),
                "armor_type": getattr(armor, 'armor_type', None).value if hasattr(armor, 'armor_type') else None
            })

    return {"equipment": results}

@router.get("/api/conditions")
async def get_conditions():
    """Get list of all D&D conditions"""
    from .combat_system import ConditionLibrary

    conditions = []
    for condition_type, info in ConditionLibrary.CONDITIONS.items():
        conditions.append({
            "type": condition_type.value,
            "name": info["name"],
            "description": info["description"],
            "effects": info["effects"]
        })

    return {"conditions": conditions}