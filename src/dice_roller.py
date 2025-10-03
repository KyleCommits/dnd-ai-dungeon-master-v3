# src/dice_roller.py
import random
import re
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

class AdvantageType(Enum):
    NORMAL = "normal"
    ADVANTAGE = "advantage"
    DISADVANTAGE = "disadvantage"

@dataclass
class DiceResult:
    total: int
    individual_rolls: List[int]
    dice_notation: str
    modifier: int
    advantage_type: AdvantageType
    description: str
    dropped_rolls: List[int] = None

class DiceRoller:
    def __init__(self):
        # import here to avoid circular imports
        from .character_manager import character_manager
        self.character_manager = character_manager

    def get_ability_modifier(self, ability_score: int) -> int:
        """convert ability score to modifier"""
        return (ability_score - 10) // 2

    def roll_dice(self, dice_count: int, dice_sides: int, modifier: int = 0,
                  advantage: AdvantageType = AdvantageType.NORMAL,
                  description: str = "") -> DiceResult:
        """roll dice with maybe advantage or disadvantage"""

        if advantage == AdvantageType.NORMAL:
            rolls = [random.randint(1, dice_sides) for _ in range(dice_count)]
            total = sum(rolls) + modifier
            dropped = None
        else:
            # adv/disadv means roll twice
            if dice_count == 1 and dice_sides == 20:  # only works for d20s
                roll1 = random.randint(1, dice_sides)
                roll2 = random.randint(1, dice_sides)

                if advantage == AdvantageType.ADVANTAGE:
                    kept_roll = max(roll1, roll2)
                    dropped_roll = min(roll1, roll2)
                else:  # DISADVANTAGE
                    kept_roll = min(roll1, roll2)
                    dropped_roll = max(roll1, roll2)

                rolls = [kept_roll]
                dropped = [dropped_roll]
                total = kept_roll + modifier
            else:
                # other dice types ignore adv/disadv
                rolls = [random.randint(1, dice_sides) for _ in range(dice_count)]
                total = sum(rolls) + modifier
                dropped = None

        dice_notation = f"{dice_count}d{dice_sides}"
        if modifier != 0:
            dice_notation += f"+{modifier}" if modifier > 0 else str(modifier)

        return DiceResult(
            total=total,
            individual_rolls=rolls,
            dice_notation=dice_notation,
            modifier=modifier,
            advantage_type=advantage,
            description=description or dice_notation,
            dropped_rolls=dropped
        )

    async def roll_ability_check(self, character_id: int, ability: str,
                                 advantage: AdvantageType = AdvantageType.NORMAL, db=None) -> DiceResult:
        """roll a basic ability check for a character"""
        from sqlalchemy.ext.asyncio import AsyncSession

        if db is None:
            from .database import get_db_session
            async for session in get_db_session():
                db = session
                break

        character = await self.character_manager.get_character_full(db, character_id)
        if not character:
            raise ValueError(f"Character {character_id} not found")

        # map short to full ability names
        ability_mapping = {
            'str': 'strength',
            'dex': 'dexterity',
            'con': 'constitution',
            'int': 'intelligence',
            'wis': 'wisdom',
            'cha': 'charisma'
        }

        full_ability_name = ability_mapping.get(ability.lower(), ability.lower())
        ability_score = getattr(character.abilities[0], full_ability_name)
        modifier = self.get_ability_modifier(ability_score)

        description = f"{ability.upper()} Check ({character.name})"
        return self.roll_dice(1, 20, modifier, advantage, description)

    async def roll_skill_check(self, character_id: int, skill: str,
                              advantage: AdvantageType = AdvantageType.NORMAL, db=None) -> DiceResult:
        """roll a skill check for a character"""
        from sqlalchemy.ext.asyncio import AsyncSession

        if db is None:
            from .database import get_db_session
            async for session in get_db_session():
                db = session
                break

        character = await self.character_manager.get_character_full(db, character_id)
        if not character:
            raise ValueError(f"Character {character_id} not found")

        modifier = await self.character_manager.calculate_skill_modifier(character, skill)

        # check if proficient for description
        skill_obj = next((s for s in character.skills if s.skill_name == skill), None)
        prof_text = ""
        if skill_obj and skill_obj.proficient:
            prof_text = " (Prof)"
            if skill_obj.expertise:
                prof_text = " (Exp)"

        description = f"{skill.capitalize()} Check ({character.name}){prof_text}"
        return self.roll_dice(1, 20, modifier, advantage, description)

    async def roll_saving_throw(self, character_id: int, ability: str,
                               advantage: AdvantageType = AdvantageType.NORMAL, db=None) -> DiceResult:
        """roll a saving throw for a character"""
        from sqlalchemy.ext.asyncio import AsyncSession

        # turn short names into full ones
        ability_name_map = {
            'str': 'strength',
            'dex': 'dexterity',
            'con': 'constitution',
            'int': 'intelligence',
            'wis': 'wisdom',
            'cha': 'charisma'
        }

        full_ability_name = ability_name_map.get(ability.lower(), ability)

        if db is None:
            from .database import get_db_session
            async for session in get_db_session():
                character = await self.character_manager.get_character_full(session, character_id)
                if not character:
                    raise ValueError(f"Character {character_id} not found")

                modifier = await self.character_manager.calculate_saving_throw_modifier(character, full_ability_name)

                # check proficiency for description
                save_prof_attr = f"{ability[:3]}_save_prof"
                is_proficient = getattr(character.abilities[0], save_prof_attr)
                prof_text = " (Prof)" if is_proficient else ""

                description = f"{ability.upper()} Save ({character.name}){prof_text}"
                return self.roll_dice(1, 20, modifier, advantage, description)
        else:
            character = await self.character_manager.get_character_full(db, character_id)
            if not character:
                raise ValueError(f"Character {character_id} not found")

            modifier = await self.character_manager.calculate_saving_throw_modifier(character, full_ability_name)

            # see if proficient for description
            save_prof_attr = f"{ability[:3]}_save_prof"
            is_proficient = getattr(character.abilities[0], save_prof_attr)
            prof_text = " (Prof)" if is_proficient else ""

            description = f"{ability.upper()} Save ({character.name}){prof_text}"
            return self.roll_dice(1, 20, modifier, advantage, description)

    # old methods for backwards compat
    def roll_ability_check_mock(self, ability: str, advantage: AdvantageType = AdvantageType.NORMAL) -> DiceResult:
        """old method using fake character data"""
        mock_abilities = {"str": 14, "dex": 16, "con": 13, "int": 12, "wis": 15, "cha": 10}
        ability_score = mock_abilities[ability.lower()]
        modifier = self.get_ability_modifier(ability_score)
        description = f"{ability.upper()} Check"
        return self.roll_dice(1, 20, modifier, advantage, description)

    def parse_dice_notation(self, notation: str, modifier: int = 0) -> DiceResult:
        """parse dice notation like '2d6', '1d20+5', etc"""
        # simple dice regex
        match = re.match(r'^(\d+)?d(\d+)([+-]\d+)?$', notation.lower().strip())
        if not match:
            raise ValueError(f"Invalid dice notation: {notation}")

        dice_count = int(match.group(1)) if match.group(1) else 1
        dice_sides = int(match.group(2))
        notation_modifier = int(match.group(3)) if match.group(3) else 0

        total_modifier = modifier + notation_modifier

        return self.roll_dice(dice_count, dice_sides, total_modifier, AdvantageType.NORMAL, notation)

dice_roller = DiceRoller()