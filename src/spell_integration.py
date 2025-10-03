# src/spell_integration.py
"""
Spell Integration Module
Connects the enhanced spell system with character management and game systems
"""

from typing import List, Dict, Optional, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from .enhanced_spell_system import enhanced_spell_manager, EnhancedSpell
from .character_models import Character, CharacterSpell
from .spell_system import SpellSlotManager

class CharacterSpellManager:
    """Manages spells for individual characters"""

    def __init__(self):
        self.enhanced_manager = enhanced_spell_manager
        self.slot_manager = SpellSlotManager()

        # what kind of caster each class is
        self.caster_types = {
            "Wizard": "full",
            "Sorcerer": "full",
            "Cleric": "full",
            "Druid": "full",
            "Bard": "full",
            "Warlock": "warlock",
            "Paladin": "half",
            "Ranger": "half",
            "Eldritch Knight": "third",
            "Arcane Trickster": "third"
        }

        # which stat each class uses for spells
        self.spellcasting_abilities = {
            "Wizard": "intelligence",
            "Sorcerer": "charisma",
            "Cleric": "wisdom",
            "Druid": "wisdom",
            "Bard": "charisma",
            "Warlock": "charisma",
            "Paladin": "charisma",
            "Ranger": "wisdom",
            "Eldritch Knight": "intelligence",
            "Arcane Trickster": "intelligence"
        }

    async def initialize_character_spells(self, db: AsyncSession, character: Character):
        """Initialize spell list for a new character based on their class"""

        # see if they can cast spells
        caster_type = self.caster_types.get(character.class_name)
        if not caster_type:
            return  # Non-spellcaster

        # get spells for their class
        available_spells = self.enhanced_manager.get_class_spells(character.class_name)

        # give them cantrips
        cantrips = [spell for spell in available_spells if spell.level == 0]

        # add starting spells
        known_spells = self._get_initial_spells(character.class_name, character.level, available_spells)

        # save it all
        for spell in known_spells:
            character_spell = CharacterSpell(
                character_id=character.id,
                spell_name=spell.name,
                spell_level=spell.level,
                prepared=self._is_auto_prepared(character.class_name, spell),
                known=True
            )
            db.add(character_spell)

        await db.commit()

    def _get_initial_spells(self, class_name: str, level: int, available_spells: List[EnhancedSpell]) -> List[EnhancedSpell]:
        """Get initial spells for a character based on class and level"""

        # grab cantrips
        cantrips = [s for s in available_spells if s.level == 0]
        cantrip_count = self._get_cantrips_known(class_name, level)
        selected_cantrips = cantrips[:cantrip_count]

        # get level 1 spells
        first_level_spells = [s for s in available_spells if s.level == 1]
        spell_count = self._get_spells_known(class_name, level)
        selected_spells = first_level_spells[:spell_count]

        return selected_cantrips + selected_spells

    def _get_cantrips_known(self, class_name: str, level: int) -> int:
        """Get number of cantrips known by class and level"""
        cantrip_progression = {
            "Wizard": {1: 3, 4: 4, 10: 5},
            "Sorcerer": {1: 4, 4: 5, 10: 6},
            "Cleric": {1: 3, 4: 4, 10: 5},
            "Druid": {1: 2, 4: 3, 10: 4},
            "Bard": {1: 2, 4: 3, 10: 4},
            "Warlock": {1: 2, 4: 3, 10: 4}
        }

        progression = cantrip_progression.get(class_name, {})
        cantrips = 0
        for threshold_level in sorted(progression.keys()):
            if level >= threshold_level:
                cantrips = progression[threshold_level]
        return cantrips

    def _get_spells_known(self, class_name: str, level: int) -> int:
        """Get number of spells known by class and level (for known casters)"""
        if class_name in ["Cleric", "Druid", "Paladin", "Ranger"]:
            # prepared casters know everything
            return 20  # Return high number to get many spells

        # known casters are more limited
        spells_known = {
            "Sorcerer": {1: 2, 2: 3, 3: 4, 4: 5, 5: 6, 6: 7, 7: 8, 8: 9, 9: 10},
            "Bard": {1: 4, 2: 5, 3: 6, 4: 7, 5: 8, 6: 9, 7: 10, 8: 11, 9: 12},
            "Warlock": {1: 2, 2: 3, 3: 4, 4: 5, 5: 6, 6: 7, 7: 8, 8: 9, 9: 10}
        }

        progression = spells_known.get(class_name, {1: 2})
        spells = 0
        for threshold_level in sorted(progression.keys()):
            if level >= threshold_level:
                spells = progression[threshold_level]
        return spells

    def _is_auto_prepared(self, class_name: str, spell: EnhancedSpell) -> bool:
        """Check if spell is automatically prepared"""
        if spell.level == 0:  # Cantrips are always prepared
            return True

        # sorcerers and warlocks dont prepare
        if class_name in ["Sorcerer", "Warlock", "Bard"]:
            return True

        return False

    async def get_character_spells(self, db: AsyncSession, character_id: int) -> Dict[str, Any]:
        """Get all spell information for a character"""
        try:
            print(f"DEBUG: CharacterSpellManager.get_character_spells called for character {character_id}")

            # get character info
            from sqlalchemy.orm import selectinload
            character_query = select(Character).options(selectinload(Character.abilities)).where(Character.id == character_id)
            result = await db.execute(character_query)
            character = result.scalar_one_or_none()
            print(f"DEBUG: Found character: {character.name if character else 'None'}")
            if character:
                print(f"DEBUG: Character has {len(character.abilities)} ability records")

            if not character:
                print(f"DEBUG: Character {character_id} not found")
                return {}

            # fetch their spells
            spell_query = select(CharacterSpell).where(CharacterSpell.character_id == character_id)
            result = await db.execute(spell_query)
            character_spells = result.scalars().all()
            print(f"DEBUG: Found {len(character_spells)} character spells in database")

            # make sure they can cast
            caster_type = self.caster_types.get(character.class_name)
            print(f"DEBUG: Character class {character.class_name}, caster type: {caster_type}")

            if not caster_type:
                print(f"DEBUG: {character.class_name} is not a spellcaster")
                return {
                    "character_id": character_id,
                    "character_name": character.name,
                    "class_name": character.class_name,
                    "level": character.level,
                    "is_spellcaster": False,
                    "spell_slots": [],
                    "spells_by_level": {},
                    "total_spells": 0
                }

            # sort by spell level
            spells_by_level = {}
            for char_spell in character_spells:
                level = char_spell.spell_level
                if level not in spells_by_level:
                    spells_by_level[level] = []

                # get full spell info
                enhanced_spell = self.enhanced_manager.get_spell(char_spell.spell_name)
                if enhanced_spell:
                    spell_info = {
                        "spell": enhanced_spell,
                        "is_prepared": char_spell.prepared,
                        "is_known": char_spell.known,
                        "times_cast_today": 0  # Not stored in DB, would need separate tracking
                    }
                    spells_by_level[level].append(spell_info)

            # check spell slots
            caster_type = self.caster_types.get(character.class_name, "none")
            spell_slots = self.slot_manager.get_spell_slots(caster_type, character.level)

            # figure out spell modifier
            spellcasting_ability = self.spellcasting_abilities.get(character.class_name)
            spellcasting_modifier = 0
            if spellcasting_ability and character.abilities:
                # abilities is a list, get the first one
                ability_record = character.abilities[0] if character.abilities else None
                if ability_record:
                    ability_score = getattr(ability_record, spellcasting_ability, 10)
                    spellcasting_modifier = (ability_score - 10) // 2
                    print(f"DEBUG: {spellcasting_ability} score: {ability_score}, modifier: {spellcasting_modifier}")

            spell_save_dc = 8 + character.proficiency_bonus + spellcasting_modifier
            spell_attack_bonus = character.proficiency_bonus + spellcasting_modifier

            print(f"DEBUG: Returning spell data with {len(spells_by_level)} spell levels")
            return {
                "character_id": character_id,
                "character_name": character.name,
                "class_name": character.class_name,
                "level": character.level,
                "is_spellcaster": True,
                "caster_type": caster_type,
                "spellcasting_ability": spellcasting_ability,
                "spellcasting_modifier": spellcasting_modifier,
                "spell_save_dc": spell_save_dc,
                "spell_attack_bonus": spell_attack_bonus,
                "spell_slots": spell_slots,
                "spells_by_level": spells_by_level,
                "total_spells": len(character_spells)
            }

        except Exception as e:
            print(f"ERROR in CharacterSpellManager.get_character_spells: {type(e).__name__}: {str(e)}")
            import traceback
            traceback.print_exc()
            raise

    async def cast_spell(self, db: AsyncSession, character_id: int, spell_name: str, slot_level: int) -> Dict[str, Any]:
        """Cast a spell, consuming spell slot and tracking usage"""

        # Get character spell
        spell_query = select(CharacterSpell).where(
            and_(CharacterSpell.character_id == character_id,
                 CharacterSpell.spell_name == spell_name)
        )
        result = await db.execute(spell_query)
        character_spell = result.scalar_one_or_none()

        if not character_spell:
            return {"success": False, "error": "Spell not known"}

        if not character_spell.prepared:
            return {"success": False, "error": "Spell not prepared"}

        # Get enhanced spell details
        enhanced_spell = self.enhanced_manager.get_spell(spell_name)
        if not enhanced_spell:
            return {"success": False, "error": "Spell not found in database"}

        # Check spell slot level
        if slot_level < enhanced_spell.level:
            return {"success": False, "error": f"Cannot cast level {enhanced_spell.level} spell with level {slot_level} slot"}

        # TODO: Check if character has available spell slots
        # This would require tracking current spell slots in character data

        # For now, just proceed with casting (spell slot tracking would need to be implemented)
        await db.commit()

        # Calculate damage/healing if applicable
        spell_result = self._calculate_spell_effects(enhanced_spell, slot_level)

        return {
            "success": True,
            "spell": enhanced_spell,
            "slot_level_used": slot_level,
            "times_cast_today": 1,  # Would need proper tracking
            "spell_effects": spell_result
        }

    def _calculate_spell_effects(self, spell: EnhancedSpell, slot_level: int) -> Dict[str, Any]:
        """Calculate spell effects including damage/healing with upcasting"""
        effects = {}

        # Handle damage
        if spell.damage:
            base_damage = spell.damage.damage_at_slot_level.get(str(spell.level), "")
            upcast_damage = spell.damage.damage_at_slot_level.get(str(slot_level), base_damage)

            # Fallback for common cantrips that should have standard damage
            if not upcast_damage and spell.level == 0:
                cantrip_damage = {
                    "Acid Splash": "1d6",
                    "Fire Bolt": "1d10",
                    "Ray of Frost": "1d8",
                    "Sacred Flame": "1d8",
                    "Toll the Dead": "1d8",
                    "Eldritch Blast": "1d10",
                    "Chill Touch": "1d8"
                }
                upcast_damage = cantrip_damage.get(spell.name, "")

            effects["damage"] = {
                "dice": upcast_damage,
                "type": spell.damage.damage_type,
                "save_for_half": spell.saving_throw is not None
            }

        # Handle healing
        if spell.heal_at_slot_level:
            base_healing = spell.heal_at_slot_level.get(str(spell.level), "")
            upcast_healing = spell.heal_at_slot_level.get(str(slot_level), base_healing)

            effects["healing"] = {
                "dice": upcast_healing
            }

        # Handle saving throw
        if spell.saving_throw:
            effects["saving_throw"] = {
                "ability": spell.saving_throw.ability,
                "success_type": spell.saving_throw.success_type
            }

        # Handle area of effect
        if spell.area_of_effect:
            effects["area_of_effect"] = {
                "type": spell.area_of_effect.type,
                "size": spell.area_of_effect.size
            }

        return effects

    async def learn_spell(self, db: AsyncSession, character_id: int, spell_name: str) -> Dict[str, Any]:
        """Learn a new spell (for classes that learn spells)"""

        # Get spell details
        enhanced_spell = self.enhanced_manager.get_spell(spell_name)
        if not enhanced_spell:
            return {"success": False, "error": "Spell not found"}

        # Check if already known
        existing_query = select(CharacterSpell).where(
            and_(CharacterSpell.character_id == character_id,
                 CharacterSpell.spell_name == spell_name)
        )
        result = await db.execute(existing_query)
        existing = result.scalar_one_or_none()

        if existing:
            return {"success": False, "error": "Spell already known"}

        # Get character to check class compatibility
        character_query = select(Character).where(Character.id == character_id)
        result = await db.execute(character_query)
        character = result.scalar_one_or_none()

        if not character:
            return {"success": False, "error": "Character not found"}

        # Check if spell is available to character's class
        class_spells = self.enhanced_manager.get_class_spells(character.class_name)
        available_spell_names = [s.name for s in class_spells]

        if spell_name not in available_spell_names:
            return {"success": False, "error": f"Spell not available to {character.class_name}"}

        # Add spell
        character_spell = CharacterSpell(
            character_id=character_id,
            spell_name=spell_name,
            spell_level=enhanced_spell.level,
            prepared=self._is_auto_prepared(character.class_name, enhanced_spell),
            known=True
        )

        db.add(character_spell)
        await db.commit()

        return {"success": True, "spell": enhanced_spell}

    async def prepare_spell(self, db: AsyncSession, character_id: int, spell_name: str, prepare: bool = True) -> Dict[str, Any]:
        """Prepare or unprepare a spell for a character."""
        try:
            # Get character
            character_query = select(Character).where(Character.id == character_id)
            result = await db.execute(character_query)
            character = result.scalar_one_or_none()

            if not character:
                return {"success": False, "error": "Character not found"}

            # Check if character can prepare spells
            if character.class_name in ["Sorcerer", "Warlock", "Bard"]:
                return {"success": False, "error": f"{character.class_name}s don't prepare spells - they are always prepared"}

            # Get the character spell
            spell_query = select(CharacterSpell).where(
                and_(CharacterSpell.character_id == character_id, CharacterSpell.spell_name == spell_name)
            )
            result = await db.execute(spell_query)
            character_spell = result.scalar_one_or_none()

            if not character_spell:
                return {"success": False, "error": "Spell not known by character"}

            if character_spell.spell_level == 0:  # Cantrips
                return {"success": False, "error": "Cantrips are always prepared"}

            # Check spell preparation limits
            if prepare:
                prepared_count = await self._get_prepared_spell_count(db, character_id, character_spell.spell_level)
                max_prepared = self._get_max_prepared_spells(character.class_name, character.level, character_spell.spell_level)

                if prepared_count >= max_prepared:
                    return {"success": False, "error": f"Cannot prepare more level {character_spell.spell_level} spells"}

            # Update preparation status
            character_spell.prepared = prepare
            await db.commit()

            return {"success": True, "prepared": prepare}

        except Exception as e:
            print(f"ERROR in prepare_spell: {str(e)}")
            return {"success": False, "error": str(e)}

    async def character_rest(self, db: AsyncSession, character_id: int, rest_type: str = "long") -> Dict[str, Any]:
        """Handle character rest with spell slot and HP recovery."""
        try:
            # Get character
            character_query = select(Character).where(Character.id == character_id)
            result = await db.execute(character_query)
            character = result.scalar_one_or_none()

            if not character:
                return {"success": False, "error": "Character not found"}

            recovery_info = []

            # HP Recovery
            if rest_type == "short":
                # Short rest: can spend hit dice for HP recovery
                recovery_info.append("Short rest completed - can spend hit dice for HP recovery")
            else:  # long rest
                # Long rest: full HP recovery
                hp_recovered = character.max_hp - character.current_hp
                character.current_hp = character.max_hp
                if hp_recovered > 0:
                    recovery_info.append(f"Recovered {hp_recovered} HP (full health)")

            # Spell Slot Recovery
            caster_type = self.caster_types.get(character.class_name)
            if caster_type:
                if rest_type == "short" and character.class_name == "Warlock":
                    # Warlocks recover spell slots on short rest
                    recovery_info.append("Warlock spell slots recovered")
                elif rest_type == "long":
                    # All casters recover spell slots on long rest
                    recovery_info.append("All spell slots recovered")

                # Note: Actual spell slot tracking would be implemented in the spell slot system

            await db.commit()

            return {
                "success": True,
                "rest_type": rest_type,
                "recovery": recovery_info,
                "message": f"{rest_type.title()} rest completed"
            }

        except Exception as e:
            print(f"ERROR in character_rest: {str(e)}")
            return {"success": False, "error": str(e)}

    async def _get_prepared_spell_count(self, db: AsyncSession, character_id: int, spell_level: int) -> int:
        """Get count of prepared spells at a specific level."""
        from sqlalchemy.func import count
        query = select(count()).where(
            and_(
                CharacterSpell.character_id == character_id,
                CharacterSpell.spell_level == spell_level,
                CharacterSpell.prepared == True
            )
        )
        result = await db.execute(query)
        return result.scalar() or 0

    def _get_max_prepared_spells(self, class_name: str, character_level: int, spell_level: int) -> int:
        """Get maximum number of spells that can be prepared at a specific level."""
        # Simplified - in a full implementation this would be more complex
        # Base it on character level and class

        if class_name in ["Wizard", "Cleric", "Druid"]:
            # Prepared casters can prepare spells = level + ability modifier
            # For simplicity, assume +3 ability modifier
            return max(1, character_level + 3)
        elif class_name == "Paladin":
            return max(1, (character_level // 2) + 3)  # Half caster

        return 99  # Default high number for other classes

# Global character spell manager
character_spell_manager = CharacterSpellManager()