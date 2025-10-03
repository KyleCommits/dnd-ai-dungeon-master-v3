# src/character_calculator.py
from typing import Dict, List, Any, Optional
from .character_models import Character, CharacterAbility, CharacterSkill, CharacterEquipment

class CharacterCalculator:
    """Handles complex character stat calculations."""

    def __init__(self):
        # D&D 5e class hit dice
        self.class_hit_dice = {
            'barbarian': 12,
            'fighter': 10,
            'paladin': 10,
            'ranger': 10,
            'bard': 8,
            'cleric': 8,
            'druid': 8,
            'monk': 8,
            'rogue': 8,
            'warlock': 8,
            'sorcerer': 6,
            'wizard': 6
        }

        # Class primary abilities for multiclassing
        self.class_primary_abilities = {
            'barbarian': ['strength'],
            'bard': ['charisma'],
            'cleric': ['wisdom'],
            'druid': ['wisdom'],
            'fighter': ['strength', 'dexterity'],
            'monk': ['dexterity', 'wisdom'],
            'paladin': ['strength', 'charisma'],
            'ranger': ['dexterity', 'wisdom'],
            'rogue': ['dexterity'],
            'sorcerer': ['charisma'],
            'warlock': ['charisma'],
            'wizard': ['intelligence']
        }

        # Spellcasting abilities by class
        self.spellcasting_abilities = {
            'bard': 'charisma',
            'cleric': 'wisdom',
            'druid': 'wisdom',
            'paladin': 'charisma',
            'ranger': 'wisdom',
            'sorcerer': 'charisma',
            'warlock': 'charisma',
            'wizard': 'intelligence',
            'eldritch_knight': 'intelligence',  # Fighter subclass
            'arcane_trickster': 'intelligence'  # Rogue subclass
        }

    def calculate_ability_modifier(self, score: int) -> int:
        """Calculate D&D 5e ability modifier."""
        return (score - 10) // 2

    def calculate_proficiency_bonus(self, level: int) -> int:
        """Calculate proficiency bonus by level."""
        return 2 + ((level - 1) // 4)

    def calculate_max_hp(self, character: Character, constitution_modifier: int) -> int:
        """Calculate maximum hit points."""
        class_name = character.class_name.lower()
        hit_die = self.class_hit_dice.get(class_name, 8)

        # First level: max hit die + con mod
        # Additional levels: average of hit die + con mod
        if character.level == 1:
            return hit_die + constitution_modifier
        else:
            first_level_hp = hit_die + constitution_modifier
            additional_levels = character.level - 1
            average_per_level = (hit_die // 2) + 1 + constitution_modifier
            return first_level_hp + (additional_levels * average_per_level)

    def calculate_armor_class(self, character: Character, abilities: CharacterAbility,
                            equipment: List[CharacterEquipment]) -> int:
        """Calculate armor class based on equipment and abilities."""
        base_ac = 10
        dex_modifier = self.calculate_ability_modifier(abilities.dexterity)

        # Find armor
        armor = None
        shield = None

        for item in equipment:
            if not item.equipped:
                continue

            item_name = item.item_name.lower()

            # Armor types
            if 'chain mail' in item_name or 'plate' in item_name:
                armor = {'ac': 18 if 'plate' in item_name else 16, 'type': 'heavy'}
            elif 'chain shirt' in item_name or 'scale mail' in item_name:
                armor = {'ac': 13 + min(dex_modifier, 2), 'type': 'medium'}
            elif 'leather' in item_name or 'studded' in item_name:
                armor = {'ac': 11 + dex_modifier if 'leather' in item_name else 12 + dex_modifier, 'type': 'light'}
            elif 'shield' in item_name:
                shield = {'ac': 2}

        if armor:
            ac = armor['ac']
        else:
            # Unarmored: 10 + Dex modifier
            ac = 10 + dex_modifier

        if shield:
            ac += shield['ac']

        return ac

    def calculate_spell_save_dc(self, character: Character, abilities: CharacterAbility) -> int:
        """Calculate spell save DC."""
        class_name = character.class_name.lower()
        spellcasting_ability = self.spellcasting_abilities.get(class_name)

        if not spellcasting_ability:
            return 8  # No spellcasting

        ability_score = getattr(abilities, spellcasting_ability)
        ability_modifier = self.calculate_ability_modifier(ability_score)
        proficiency_bonus = self.calculate_proficiency_bonus(character.level)

        return 8 + proficiency_bonus + ability_modifier

    def calculate_spell_attack_bonus(self, character: Character, abilities: CharacterAbility) -> int:
        """Calculate spell attack bonus."""
        class_name = character.class_name.lower()
        spellcasting_ability = self.spellcasting_abilities.get(class_name)

        if not spellcasting_ability:
            return 0

        ability_score = getattr(abilities, spellcasting_ability)
        ability_modifier = self.calculate_ability_modifier(ability_score)
        proficiency_bonus = self.calculate_proficiency_bonus(character.level)

        return proficiency_bonus + ability_modifier

    def get_spell_slots_by_level(self, character_level: int, class_name: str) -> Dict[int, int]:
        """Get spell slots by spell level for a class."""
        spell_slots = {
            1: {1: 2},
            2: {1: 3},
            3: {1: 4, 2: 2},
            4: {1: 4, 2: 3},
            5: {1: 4, 2: 3, 3: 2},
            6: {1: 4, 2: 3, 3: 3},
            7: {1: 4, 2: 3, 3: 3, 4: 1},
            8: {1: 4, 2: 3, 3: 3, 4: 2},
            9: {1: 4, 2: 3, 3: 3, 4: 3, 5: 1},
            10: {1: 4, 2: 3, 3: 3, 4: 3, 5: 2},
            11: {1: 4, 2: 3, 3: 3, 4: 3, 5: 2, 6: 1},
            12: {1: 4, 2: 3, 3: 3, 4: 3, 5: 2, 6: 1},
            13: {1: 4, 2: 3, 3: 3, 4: 3, 5: 2, 6: 1, 7: 1},
            14: {1: 4, 2: 3, 3: 3, 4: 3, 5: 2, 6: 1, 7: 1},
            15: {1: 4, 2: 3, 3: 3, 4: 3, 5: 2, 6: 1, 7: 1, 8: 1},
            16: {1: 4, 2: 3, 3: 3, 4: 3, 5: 2, 6: 1, 7: 1, 8: 1},
            17: {1: 4, 2: 3, 3: 3, 4: 3, 5: 2, 6: 1, 7: 1, 8: 1, 9: 1},
            18: {1: 4, 2: 3, 3: 3, 4: 3, 5: 3, 6: 1, 7: 1, 8: 1, 9: 1},
            19: {1: 4, 2: 3, 3: 3, 4: 3, 5: 3, 6: 2, 7: 1, 8: 1, 9: 1},
            20: {1: 4, 2: 3, 3: 3, 4: 3, 5: 3, 6: 2, 7: 2, 8: 1, 9: 1}
        }

        # Half-casters (Paladin, Ranger) get spells later and fewer slots
        if class_name.lower() in ['paladin', 'ranger']:
            if character_level < 2:
                return {}

            effective_level = (character_level + 1) // 2
            return spell_slots.get(effective_level, {})

        # Third-casters (Eldritch Knight, Arcane Trickster)
        elif class_name.lower() in ['eldritch_knight', 'arcane_trickster']:
            if character_level < 3:
                return {}

            effective_level = (character_level + 2) // 3
            return spell_slots.get(effective_level, {})

        # Full casters
        return spell_slots.get(character_level, {})

    def calculate_carrying_capacity(self, strength_score: int) -> Dict[str, int]:
        """Calculate carrying capacity limits."""
        base_capacity = strength_score * 15

        return {
            'carrying_capacity': base_capacity,
            'push_drag_lift': base_capacity * 2,
            'encumbered_at': base_capacity * 5,  # Variant encumbrance
            'heavily_encumbered_at': base_capacity * 10
        }

    def calculate_passive_perception(self, character: Character, abilities: CharacterAbility,
                                   skills: List[CharacterSkill]) -> int:
        """Calculate passive Perception score."""
        wisdom_modifier = self.calculate_ability_modifier(abilities.wisdom)
        proficiency_bonus = self.calculate_proficiency_bonus(character.level)

        # Check if proficient in Perception
        perception_skill = next((s for s in skills if s.skill_name == 'perception'), None)
        if perception_skill and perception_skill.proficient:
            bonus = proficiency_bonus
            if perception_skill.expertise:
                bonus *= 2
            return 10 + wisdom_modifier + bonus

        return 10 + wisdom_modifier

    def get_class_features_by_level(self, class_name: str, level: int) -> List[Dict[str, Any]]:
        """Get class features available at a given level."""
        # This would be a massive data structure with all class features
        # For now, returning a simplified version
        features = []

        if class_name.lower() == 'fighter':
            if level >= 1:
                features.append({
                    'name': 'Fighting Style',
                    'description': 'Choose a fighting style',
                    'level': 1
                })
                features.append({
                    'name': 'Second Wind',
                    'description': 'Regain hit points as a bonus action',
                    'level': 1
                })
            if level >= 2:
                features.append({
                    'name': 'Action Surge',
                    'description': 'Take an additional action on your turn',
                    'level': 2
                })

        return features

# Global calculator instance
character_calculator = CharacterCalculator()