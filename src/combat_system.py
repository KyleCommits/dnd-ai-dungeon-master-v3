# src/combat_system.py
"""
D&D 5e Combat and Condition Tracking System
Handles initiative, combat rounds, conditions, and status effects
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Any, Union
from enum import Enum
import time
from datetime import datetime, timedelta

class CombatantType(Enum):
    PLAYER = "player"
    NPC = "npc"
    MONSTER = "monster"

class ConditionType(Enum):
    BLINDED = "blinded"
    CHARMED = "charmed"
    DEAFENED = "deafened"
    FRIGHTENED = "frightened"
    GRAPPLED = "grappled"
    INCAPACITATED = "incapacitated"
    INVISIBLE = "invisible"
    PARALYZED = "paralyzed"
    PETRIFIED = "petrified"
    POISONED = "poisoned"
    PRONE = "prone"
    RESTRAINED = "restrained"
    STUNNED = "stunned"
    UNCONSCIOUS = "unconscious"
    EXHAUSTION = "exhaustion"

class DamageType(Enum):
    ACID = "acid"
    BLUDGEONING = "bludgeoning"
    COLD = "cold"
    FIRE = "fire"
    FORCE = "force"
    LIGHTNING = "lightning"
    NECROTIC = "necrotic"
    PIERCING = "piercing"
    POISON = "poison"
    PSYCHIC = "psychic"
    RADIANT = "radiant"
    SLASHING = "slashing"
    THUNDER = "thunder"

@dataclass
class Condition:
    condition_type: ConditionType
    duration_rounds: Optional[int] = None  # None for indefinite
    source: str = ""
    level: int = 1  # For conditions like exhaustion
    save_dc: Optional[int] = None
    save_ability: Optional[str] = None
    save_at_end_of_turn: bool = False

@dataclass
class DamageInstance:
    amount: int
    damage_type: DamageType
    source: str = ""
    critical: bool = False

@dataclass
class Combatant:
    id: str
    name: str
    combatant_type: CombatantType
    max_hp: int
    current_hp: int
    temp_hp: int = 0
    ac: int = 10
    initiative: int = 0
    initiative_modifier: int = 0
    conditions: List[Condition] = field(default_factory=list)
    concentration_spell: Optional[str] = None
    death_saves_success: int = 0
    death_saves_failure: int = 0
    is_unconscious: bool = False
    is_stable: bool = False

    def add_condition(self, condition: Condition):
        """Add a condition to the combatant"""
        # remove same condition type (they dont stack)
        self.conditions = [c for c in self.conditions if c.condition_type != condition.condition_type]
        self.conditions.append(condition)

    def remove_condition(self, condition_type: ConditionType):
        """Remove a condition from the combatant"""
        self.conditions = [c for c in self.conditions if c.condition_type != condition_type]

    def has_condition(self, condition_type: ConditionType) -> bool:
        """Check if combatant has a specific condition"""
        return any(c.condition_type == condition_type for c in self.conditions)

    def take_damage(self, damage: DamageInstance) -> Dict[str, Any]:
        """Apply damage to combatant"""
        damage_taken = damage.amount

        # use temp hp first
        if self.temp_hp > 0:
            if damage_taken <= self.temp_hp:
                self.temp_hp -= damage_taken
                damage_taken = 0
            else:
                damage_taken -= self.temp_hp
                self.temp_hp = 0

        # apply leftover damage to real hp
        self.current_hp -= damage_taken

        # see if they fall unconscious
        was_unconscious = self.is_unconscious
        if self.current_hp <= 0:
            self.current_hp = 0
            self.is_unconscious = True
            self.add_condition(Condition(ConditionType.UNCONSCIOUS))

            # roll concentration check
            if self.concentration_spell:
                concentration_result = self.make_concentration_save(damage.amount)
                if not concentration_result["success"]:
                    self.lose_concentration()

        return {
            "damage_dealt": damage.amount,
            "damage_after_temp": damage_taken,
            "new_hp": self.current_hp,
            "new_temp_hp": self.temp_hp,
            "became_unconscious": not was_unconscious and self.is_unconscious,
            "concentration_lost": self.concentration_spell is None and damage.amount > 0
        }

    def heal(self, amount: int) -> Dict[str, Any]:
        """Heal the combatant"""
        old_hp = self.current_hp
        was_unconscious = self.is_unconscious

        self.current_hp = min(self.current_hp + amount, self.max_hp)

        # see if they wake up
        if was_unconscious and self.current_hp > 0:
            self.is_unconscious = False
            self.is_stable = False
            self.death_saves_success = 0
            self.death_saves_failure = 0
            self.remove_condition(ConditionType.UNCONSCIOUS)

        return {
            "healing_amount": amount,
            "hp_gained": self.current_hp - old_hp,
            "new_hp": self.current_hp,
            "revived": was_unconscious and not self.is_unconscious
        }

    def make_concentration_save(self, damage_amount: int) -> Dict[str, Any]:
        """Make a concentration saving throw"""
        if not self.concentration_spell:
            return {"required": False}

        dc = max(10, damage_amount // 2)
        # would need real character stats for this
        con_modifier = 0  # Placeholder
        proficiency_bonus = 2  # Placeholder

        # roll d20 + con mod + prof
        import random
        roll = random.randint(1, 20)
        total = roll + con_modifier + proficiency_bonus

        success = total >= dc

        if not success:
            self.lose_concentration()

        return {
            "required": True,
            "dc": dc,
            "roll": roll,
            "total": total,
            "success": success,
            "spell_lost": self.concentration_spell if not success else None
        }

    def lose_concentration(self):
        """Lose concentration on current spell"""
        lost_spell = self.concentration_spell
        self.concentration_spell = None
        return lost_spell

@dataclass
class CombatEncounter:
    id: str
    name: str
    combatants: List[Combatant] = field(default_factory=list)
    current_round: int = 1
    current_turn: int = 0
    is_active: bool = False
    started_at: Optional[datetime] = None
    initiative_order: List[str] = field(default_factory=list)

    def add_combatant(self, combatant: Combatant):
        """Add a combatant to the encounter"""
        self.combatants.append(combatant)

    def remove_combatant(self, combatant_id: str):
        """Remove a combatant from the encounter"""
        self.combatants = [c for c in self.combatants if c.id != combatant_id]
        if combatant_id in self.initiative_order:
            self.initiative_order.remove(combatant_id)

    def get_combatant(self, combatant_id: str) -> Optional[Combatant]:
        """Get a combatant by ID"""
        return next((c for c in self.combatants if c.id == combatant_id), None)

    def roll_initiative(self):
        """Roll initiative for all combatants and sort"""
        import random

        for combatant in self.combatants:
            roll = random.randint(1, 20) + combatant.initiative_modifier
            combatant.initiative = roll

        # sort by initiative highest first
        sorted_combatants = sorted(self.combatants, key=lambda c: c.initiative, reverse=True)
        self.initiative_order = [c.id for c in sorted_combatants]

    def start_combat(self):
        """Start the combat encounter"""
        self.roll_initiative()
        self.is_active = True
        self.started_at = datetime.now()
        self.current_round = 1
        self.current_turn = 0

    def end_combat(self):
        """End the combat encounter"""
        self.is_active = False

    def next_turn(self):
        """Advance to the next turn"""
        self.current_turn += 1
        if self.current_turn >= len(self.initiative_order):
            self.current_turn = 0
            self.current_round += 1
            self.process_end_of_round()

    def get_current_combatant(self) -> Optional[Combatant]:
        """Get the combatant whose turn it is"""
        if not self.initiative_order or self.current_turn >= len(self.initiative_order):
            return None
        current_id = self.initiative_order[self.current_turn]
        return self.get_combatant(current_id)

    def process_end_of_round(self):
        """Process end-of-round effects for all combatants"""
        for combatant in self.combatants:
            # reduce condition timers
            conditions_to_remove = []
            for condition in combatant.conditions:
                if condition.duration_rounds is not None:
                    condition.duration_rounds -= 1
                    if condition.duration_rounds <= 0:
                        conditions_to_remove.append(condition.condition_type)

            # remove expired conditions
            for condition_type in conditions_to_remove:
                combatant.remove_condition(condition_type)

class CombatManager:
    """Manages combat encounters and provides combat utilities"""

    def __init__(self):
        self.active_encounters: Dict[str, CombatEncounter] = {}

    def create_encounter(self, campaign_id: str, encounter_name: str) -> CombatEncounter:
        """Create a new combat encounter"""
        encounter_id = f"{campaign_id}_{encounter_name}_{int(time.time())}"
        encounter = CombatEncounter(id=encounter_id, name=encounter_name)
        self.active_encounters[encounter_id] = encounter
        return encounter

    def get_encounter(self, encounter_id: str) -> Optional[CombatEncounter]:
        """Get an encounter by ID"""
        return self.active_encounters.get(encounter_id)

    def add_character_to_combat(self, encounter_id: str, character_data: Dict[str, Any]) -> Optional[Combatant]:
        """Add a character to combat"""
        encounter = self.get_encounter(encounter_id)
        if not encounter:
            return None

        combatant = Combatant(
            id=f"char_{character_data['id']}",
            name=character_data['name'],
            combatant_type=CombatantType.PLAYER,
            max_hp=character_data['max_hp'],
            current_hp=character_data['current_hp'],
            ac=character_data['armor_class'],
            initiative_modifier=character_data.get('dexterity_modifier', 0)
        )

        encounter.add_combatant(combatant)
        return combatant

    def add_monster_to_combat(self, encounter_id: str, monster_data: Dict[str, Any]) -> Optional[Combatant]:
        """Add a monster to combat"""
        encounter = self.get_encounter(encounter_id)
        if not encounter:
            return None

        combatant = Combatant(
            id=f"monster_{monster_data['name']}_{int(time.time())}",
            name=monster_data['name'],
            combatant_type=CombatantType.MONSTER,
            max_hp=monster_data['hp'],
            current_hp=monster_data['hp'],
            ac=monster_data['ac'],
            initiative_modifier=monster_data.get('dexterity_modifier', 0)
        )

        encounter.add_combatant(combatant)
        return combatant

    def apply_damage_to_combatant(self, encounter_id: str, combatant_id: str,
                                damage_amount: int, damage_type: DamageType,
                                source: str = "") -> Dict[str, Any]:
        """Apply damage to a specific combatant"""
        encounter = self.get_encounter(encounter_id)
        if not encounter:
            return {"error": "Encounter not found"}

        combatant = encounter.get_combatant(combatant_id)
        if not combatant:
            return {"error": "Combatant not found"}

        damage = DamageInstance(amount=damage_amount, damage_type=damage_type, source=source)
        result = combatant.take_damage(damage)

        return {
            "combatant_name": combatant.name,
            "damage_result": result,
            "current_hp": combatant.current_hp,
            "max_hp": combatant.max_hp,
            "is_unconscious": combatant.is_unconscious
        }

    def heal_combatant(self, encounter_id: str, combatant_id: str, healing_amount: int) -> Dict[str, Any]:
        """Heal a specific combatant"""
        encounter = self.get_encounter(encounter_id)
        if not encounter:
            return {"error": "Encounter not found"}

        combatant = encounter.get_combatant(combatant_id)
        if not combatant:
            return {"error": "Combatant not found"}

        result = combatant.heal(healing_amount)

        return {
            "combatant_name": combatant.name,
            "healing_result": result,
            "current_hp": combatant.current_hp,
            "max_hp": combatant.max_hp
        }

    def apply_condition(self, encounter_id: str, combatant_id: str, condition: Condition) -> Dict[str, Any]:
        """Apply a condition to a combatant"""
        encounter = self.get_encounter(encounter_id)
        if not encounter:
            return {"error": "Encounter not found"}

        combatant = encounter.get_combatant(combatant_id)
        if not combatant:
            return {"error": "Combatant not found"}

        combatant.add_condition(condition)

        return {
            "combatant_name": combatant.name,
            "condition_applied": condition.condition_type.value,
            "duration": condition.duration_rounds,
            "current_conditions": [c.condition_type.value for c in combatant.conditions]
        }

    def remove_condition(self, encounter_id: str, combatant_id: str, condition_type: ConditionType) -> Dict[str, Any]:
        """Remove a condition from a combatant"""
        encounter = self.get_encounter(encounter_id)
        if not encounter:
            return {"error": "Encounter not found"}

        combatant = encounter.get_combatant(combatant_id)
        if not combatant:
            return {"error": "Combatant not found"}

        had_condition = combatant.has_condition(condition_type)
        combatant.remove_condition(condition_type)

        return {
            "combatant_name": combatant.name,
            "condition_removed": condition_type.value,
            "was_present": had_condition,
            "current_conditions": [c.condition_type.value for c in combatant.conditions]
        }

    def get_combat_status(self, encounter_id: str) -> Dict[str, Any]:
        """Get current combat status"""
        encounter = self.get_encounter(encounter_id)
        if not encounter:
            return {"error": "Encounter not found"}

        current_combatant = encounter.get_current_combatant()

        combatant_status = []
        for combatant in encounter.combatants:
            status = {
                "id": combatant.id,
                "name": combatant.name,
                "type": combatant.combatant_type.value,
                "hp": f"{combatant.current_hp}/{combatant.max_hp}",
                "temp_hp": combatant.temp_hp,
                "ac": combatant.ac,
                "initiative": combatant.initiative,
                "conditions": [c.condition_type.value for c in combatant.conditions],
                "is_unconscious": combatant.is_unconscious,
                "concentration_spell": combatant.concentration_spell,
                "is_current_turn": combatant.id == (current_combatant.id if current_combatant else None)
            }
            combatant_status.append(status)

        return {
            "encounter_name": encounter.name,
            "is_active": encounter.is_active,
            "current_round": encounter.current_round,
            "current_turn": encounter.current_turn,
            "current_combatant": current_combatant.name if current_combatant else None,
            "combatants": combatant_status,
            "initiative_order": [encounter.get_combatant(cid).name for cid in encounter.initiative_order]
        }

class ConditionLibrary:
    """Library of D&D 5e conditions and their effects"""

    CONDITIONS = {
        ConditionType.BLINDED: {
            "name": "Blinded",
            "description": "A blinded creature can't see and automatically fails any ability check that requires sight. Attack rolls against the creature have advantage, and the creature's attack rolls have disadvantage.",
            "effects": {
                "attack_disadvantage": True,
                "attacked_with_advantage": True,
                "auto_fail_sight_checks": True
            }
        },

        ConditionType.CHARMED: {
            "name": "Charmed",
            "description": "A charmed creature can't attack the charmer or target the charmer with harmful abilities or magical effects. The charmer has advantage on any ability check to interact socially with the creature.",
            "effects": {
                "cannot_attack_charmer": True,
                "charmer_has_social_advantage": True
            }
        },

        ConditionType.FRIGHTENED: {
            "name": "Frightened",
            "description": "A frightened creature has disadvantage on ability checks and attack rolls while the source of its fear is within line of sight. The creature can't willingly move closer to the source of its fear.",
            "effects": {
                "attack_disadvantage": True,
                "ability_check_disadvantage": True,
                "cannot_approach_source": True
            }
        },

        ConditionType.GRAPPLED: {
            "name": "Grappled",
            "description": "A grappled creature's speed becomes 0, and it can't benefit from any bonus to its speed. The condition ends if the grappler is incapacitated or if an effect removes the grappled creature from the reach of the grappler or grappling effect.",
            "effects": {
                "speed_zero": True,
                "no_speed_bonus": True
            }
        },

        ConditionType.PARALYZED: {
            "name": "Paralyzed",
            "description": "A paralyzed creature is incapacitated and can't move or speak. The creature automatically fails Strength and Dexterity saving throws. Attack rolls against the creature have advantage. Any attack that hits the creature is a critical hit if the attacker is within 5 feet of the creature.",
            "effects": {
                "incapacitated": True,
                "cannot_move": True,
                "cannot_speak": True,
                "auto_fail_str_dex_saves": True,
                "attacked_with_advantage": True,
                "melee_attacks_crit": True
            }
        },

        ConditionType.POISONED: {
            "name": "Poisoned",
            "description": "A poisoned creature has disadvantage on attack rolls and ability checks.",
            "effects": {
                "attack_disadvantage": True,
                "ability_check_disadvantage": True
            }
        },

        ConditionType.PRONE: {
            "name": "Prone",
            "description": "A prone creature's only movement option is to crawl, unless it stands up and thereby ends the condition. The creature has disadvantage on attack rolls. An attack roll against the creature has advantage if the attacker is within 5 feet of the creature. Otherwise, the attack roll has disadvantage.",
            "effects": {
                "can_only_crawl": True,
                "attack_disadvantage": True,
                "melee_attacks_advantage": True,
                "ranged_attacks_disadvantage": True
            }
        },

        ConditionType.RESTRAINED: {
            "name": "Restrained",
            "description": "A restrained creature's speed becomes 0, and it can't benefit from any bonus to its speed. Attack rolls against the creature have advantage, and the creature's attack rolls have disadvantage. The creature has disadvantage on Dexterity saving throws.",
            "effects": {
                "speed_zero": True,
                "no_speed_bonus": True,
                "attack_disadvantage": True,
                "attacked_with_advantage": True,
                "dex_save_disadvantage": True
            }
        },

        ConditionType.STUNNED: {
            "name": "Stunned",
            "description": "A stunned creature is incapacitated, can't move, and can speak only falteringly. The creature automatically fails Strength and Dexterity saving throws. Attack rolls against the creature have advantage.",
            "effects": {
                "incapacitated": True,
                "cannot_move": True,
                "speech_impaired": True,
                "auto_fail_str_dex_saves": True,
                "attacked_with_advantage": True
            }
        },

        ConditionType.UNCONSCIOUS: {
            "name": "Unconscious",
            "description": "An unconscious creature is incapacitated, can't move or speak, and is unaware of its surroundings. The creature drops whatever it's holding and falls prone. The creature automatically fails Strength and Dexterity saving throws. Attack rolls against the creature have advantage. Any attack that hits the creature is a critical hit if the attacker is within 5 feet of the creature.",
            "effects": {
                "incapacitated": True,
                "cannot_move": True,
                "cannot_speak": True,
                "unaware": True,
                "drops_items": True,
                "falls_prone": True,
                "auto_fail_str_dex_saves": True,
                "attacked_with_advantage": True,
                "melee_attacks_crit": True
            }
        }
    }

    @classmethod
    def get_condition_info(cls, condition_type: ConditionType) -> Dict[str, Any]:
        """Get information about a condition"""
        return cls.CONDITIONS.get(condition_type, {})

    @classmethod
    def create_condition(cls, condition_type: ConditionType, duration: Optional[int] = None,
                        source: str = "", **kwargs) -> Condition:
        """Create a condition instance"""
        return Condition(
            condition_type=condition_type,
            duration_rounds=duration,
            source=source,
            **kwargs
        )

# main combat manager
combat_manager = CombatManager()