# src/equipment_system.py
"""
Comprehensive D&D 5e Equipment and Inventory System
Handles weapons, armor, magic items, and inventory management
"""

from dataclasses import dataclass
from typing import Dict, List, Optional, Set, Any, Union
from enum import Enum

class ItemType(Enum):
    WEAPON = "weapon"
    ARMOR = "armor"
    SHIELD = "shield"
    TOOL = "tool"
    ADVENTURING_GEAR = "adventuring_gear"
    MAGIC_ITEM = "magic_item"
    CONSUMABLE = "consumable"
    TREASURE = "treasure"

class WeaponType(Enum):
    SIMPLE_MELEE = "simple_melee"
    SIMPLE_RANGED = "simple_ranged"
    MARTIAL_MELEE = "martial_melee"
    MARTIAL_RANGED = "martial_ranged"

class ArmorType(Enum):
    LIGHT = "light"
    MEDIUM = "medium"
    HEAVY = "heavy"

class Rarity(Enum):
    COMMON = "common"
    UNCOMMON = "uncommon"
    RARE = "rare"
    VERY_RARE = "very_rare"
    LEGENDARY = "legendary"
    ARTIFACT = "artifact"

@dataclass
class WeaponProperty:
    name: str
    description: str

@dataclass
class DamageInfo:
    dice: str
    damage_type: str
    versatile_dice: Optional[str] = None

@dataclass
class Item:
    name: str
    item_type: ItemType
    cost_gp: float
    weight_lb: float
    description: str
    rarity: Rarity = Rarity.COMMON
    requires_attunement: bool = False
    magic: bool = False

@dataclass
class Weapon(Item):
    weapon_type: WeaponType = WeaponType.SIMPLE_MELEE
    damage: DamageInfo = None
    properties: List[str] = None
    range_normal: Optional[int] = None
    range_long: Optional[int] = None
    ammunition_type: Optional[str] = None

    def __post_init__(self):
        if self.properties is None:
            self.properties = []

@dataclass
class Armor(Item):
    armor_type: ArmorType = ArmorType.LIGHT
    base_ac: int = 10
    max_dex_bonus: Optional[int] = None
    strength_requirement: Optional[int] = None
    stealth_disadvantage: bool = False

@dataclass
class MagicItem(Item):
    base_item: Optional[str] = None
    enhancement_bonus: Optional[int] = None
    special_properties: Optional[List[str]] = None
    charges: Optional[int] = None
    recharge_rate: Optional[str] = None

class WeaponDatabase:
    """Database of all D&D 5e weapons"""

    WEAPON_PROPERTIES = {
        "ammunition": WeaponProperty("Ammunition", "Requires ammunition to make ranged attacks"),
        "finesse": WeaponProperty("Finesse", "Can use Dex instead of Str for attack and damage"),
        "heavy": WeaponProperty("Heavy", "Small creatures have disadvantage on attacks"),
        "light": WeaponProperty("Light", "Can be used for two-weapon fighting"),
        "loading": WeaponProperty("Loading", "Can fire only one piece of ammunition per action"),
        "reach": WeaponProperty("Reach", "Adds 5 feet to reach when attacking"),
        "thrown": WeaponProperty("Thrown", "Can be thrown to make ranged attacks"),
        "two_handed": WeaponProperty("Two-Handed", "Requires two hands to use effectively"),
        "versatile": WeaponProperty("Versatile", "Can be used one or two-handed")
    }

    WEAPONS = {
        # Simple Melee Weapons
        "Club": Weapon(
            name="Club",
            item_type=ItemType.WEAPON,
            cost_gp=0.1,
            weight_lb=2,
            description="A simple wooden club",
            weapon_type=WeaponType.SIMPLE_MELEE,
            damage=DamageInfo("1d4", "bludgeoning"),
            properties=["light"]
        ),

        "Dagger": Weapon(
            name="Dagger",
            item_type=ItemType.WEAPON,
            cost_gp=2,
            weight_lb=1,
            description="A sharp, pointed blade",
            weapon_type=WeaponType.SIMPLE_MELEE,
            damage=DamageInfo("1d4", "piercing"),
            properties=["finesse", "light", "thrown"],
            range_normal=20,
            range_long=60
        ),

        "Handaxe": Weapon(
            name="Handaxe",
            item_type=ItemType.WEAPON,
            cost_gp=5,
            weight_lb=2,
            description="A small, balanced axe",
            weapon_type=WeaponType.SIMPLE_MELEE,
            damage=DamageInfo("1d6", "slashing"),
            properties=["light", "thrown"],
            range_normal=20,
            range_long=60
        ),

        "Spear": Weapon(
            name="Spear",
            item_type=ItemType.WEAPON,
            cost_gp=1,
            weight_lb=3,
            description="A long shaft with a pointed head",
            weapon_type=WeaponType.SIMPLE_MELEE,
            damage=DamageInfo("1d6", "piercing", "1d8"),
            properties=["thrown", "versatile"],
            range_normal=20,
            range_long=60
        ),

        # Simple Ranged Weapons
        "Light Crossbow": Weapon(
            name="Light Crossbow",
            item_type=ItemType.WEAPON,
            cost_gp=25,
            weight_lb=5,
            description="A compact crossbow",
            weapon_type=WeaponType.SIMPLE_RANGED,
            damage=DamageInfo("1d8", "piercing"),
            properties=["ammunition", "loading", "two_handed"],
            range_normal=80,
            range_long=320,
            ammunition_type="crossbow bolts"
        ),

        "Shortbow": Weapon(
            name="Shortbow",
            item_type=ItemType.WEAPON,
            cost_gp=25,
            weight_lb=2,
            description="A small, flexible bow",
            weapon_type=WeaponType.SIMPLE_RANGED,
            damage=DamageInfo("1d6", "piercing"),
            properties=["ammunition", "two_handed"],
            range_normal=80,
            range_long=320,
            ammunition_type="arrows"
        ),

        # Martial Melee Weapons
        "Longsword": Weapon(
            name="Longsword",
            item_type=ItemType.WEAPON,
            cost_gp=15,
            weight_lb=3,
            description="A straight, double-edged blade",
            weapon_type=WeaponType.MARTIAL_MELEE,
            damage=DamageInfo("1d8", "slashing", "1d10"),
            properties=["versatile"]
        ),

        "Greatsword": Weapon(
            name="Greatsword",
            item_type=ItemType.WEAPON,
            cost_gp=50,
            weight_lb=6,
            description="A massive two-handed sword",
            weapon_type=WeaponType.MARTIAL_MELEE,
            damage=DamageInfo("2d6", "slashing"),
            properties=["heavy", "two_handed"]
        ),

        "Rapier": Weapon(
            name="Rapier",
            item_type=ItemType.WEAPON,
            cost_gp=25,
            weight_lb=2,
            description="A slender, sharply pointed sword",
            weapon_type=WeaponType.MARTIAL_MELEE,
            damage=DamageInfo("1d8", "piercing"),
            properties=["finesse"]
        ),

        # Martial Ranged Weapons
        "Longbow": Weapon(
            name="Longbow",
            item_type=ItemType.WEAPON,
            cost_gp=50,
            weight_lb=2,
            description="A tall, powerful bow",
            weapon_type=WeaponType.MARTIAL_RANGED,
            damage=DamageInfo("1d8", "piercing"),
            properties=["ammunition", "heavy", "two_handed"],
            range_normal=150,
            range_long=600,
            ammunition_type="arrows"
        ),

        "Heavy Crossbow": Weapon(
            name="Heavy Crossbow",
            item_type=ItemType.WEAPON,
            cost_gp=50,
            weight_lb=18,
            description="A large, powerful crossbow",
            weapon_type=WeaponType.MARTIAL_RANGED,
            damage=DamageInfo("1d10", "piercing"),
            properties=["ammunition", "heavy", "loading", "two_handed"],
            range_normal=100,
            range_long=400,
            ammunition_type="crossbow bolts"
        )
    }

class ArmorDatabase:
    """Database of all D&D 5e armor"""

    ARMOR = {
        # Light Armor
        "Leather": Armor(
            name="Leather",
            item_type=ItemType.ARMOR,
            cost_gp=10,
            weight_lb=10,
            description="Soft, flexible leather armor",
            armor_type=ArmorType.LIGHT,
            base_ac=11
        ),

        "Studded Leather": Armor(
            name="Studded Leather",
            item_type=ItemType.ARMOR,
            cost_gp=45,
            weight_lb=13,
            description="Leather armor with metal studs",
            armor_type=ArmorType.LIGHT,
            base_ac=12
        ),

        # Medium Armor
        "Chain Shirt": Armor(
            name="Chain Shirt",
            item_type=ItemType.ARMOR,
            cost_gp=50,
            weight_lb=20,
            description="A shirt of interlocking metal rings",
            armor_type=ArmorType.MEDIUM,
            base_ac=13,
            max_dex_bonus=2
        ),

        "Scale Mail": Armor(
            name="Scale Mail",
            item_type=ItemType.ARMOR,
            cost_gp=50,
            weight_lb=45,
            description="Armor of overlapping metal scales",
            armor_type=ArmorType.MEDIUM,
            base_ac=14,
            max_dex_bonus=2,
            stealth_disadvantage=True
        ),

        "Half Plate": Armor(
            name="Half Plate",
            item_type=ItemType.ARMOR,
            cost_gp=750,
            weight_lb=40,
            description="Plate armor covering the torso",
            armor_type=ArmorType.MEDIUM,
            base_ac=15,
            max_dex_bonus=2,
            stealth_disadvantage=True
        ),

        # Heavy Armor
        "Chain Mail": Armor(
            name="Chain Mail",
            item_type=ItemType.ARMOR,
            cost_gp=75,
            weight_lb=55,
            description="Interlocking metal rings covering the body",
            armor_type=ArmorType.HEAVY,
            base_ac=16,
            strength_requirement=13,
            stealth_disadvantage=True
        ),

        "Splint": Armor(
            name="Splint",
            item_type=ItemType.ARMOR,
            cost_gp=200,
            weight_lb=60,
            description="Metal strips fastened to leather backing",
            armor_type=ArmorType.HEAVY,
            base_ac=17,
            strength_requirement=15,
            stealth_disadvantage=True
        ),

        "Plate": Armor(
            name="Plate",
            item_type=ItemType.ARMOR,
            cost_gp=1500,
            weight_lb=65,
            description="Shaped metal plates covering the entire body",
            armor_type=ArmorType.HEAVY,
            base_ac=18,
            strength_requirement=15,
            stealth_disadvantage=True
        ),

        # Shield
        "Shield": Item(
            name="Shield",
            item_type=ItemType.SHIELD,
            cost_gp=10,
            weight_lb=6,
            description="Provides +2 AC when held"
        )
    }

class MagicItemDatabase:
    """Database of magic items"""

    MAGIC_ITEMS = {
        # Weapons
        "+1 Weapon": MagicItem(
            name="+1 Weapon",
            item_type=ItemType.MAGIC_ITEM,
            cost_gp=0,  # Priceless
            weight_lb=0,  # Varies by base weapon
            rarity=Rarity.UNCOMMON,
            requires_attunement=False,
            magic=True,
            enhancement_bonus=1,
            description="A magic weapon with +1 to attack and damage rolls"
        ),

        "Flame Tongue": MagicItem(
            name="Flame Tongue",
            item_type=ItemType.MAGIC_ITEM,
            cost_gp=0,
            weight_lb=3,
            rarity=Rarity.RARE,
            requires_attunement=True,
            magic=True,
            base_item="Longsword",
            special_properties=["Can ignite for +2d6 fire damage"],
            description="A magic sword that can burst into flames"
        ),

        # Armor
        "+1 Armor": MagicItem(
            name="+1 Armor",
            item_type=ItemType.MAGIC_ITEM,
            cost_gp=0,
            weight_lb=0,
            rarity=Rarity.RARE,
            requires_attunement=False,
            magic=True,
            enhancement_bonus=1,
            description="Magic armor with +1 AC"
        ),

        # Wondrous Items
        "Bag of Holding": MagicItem(
            name="Bag of Holding",
            item_type=ItemType.MAGIC_ITEM,
            cost_gp=0,
            weight_lb=15,
            rarity=Rarity.UNCOMMON,
            requires_attunement=False,
            magic=True,
            special_properties=["Holds 500 pounds in 64 cubic feet"],
            description="A magical bag that holds more than it appears"
        ),

        "Potion of Healing": MagicItem(
            name="Potion of Healing",
            item_type=ItemType.CONSUMABLE,
            cost_gp=50,
            weight_lb=0.5,
            rarity=Rarity.COMMON,
            requires_attunement=False,
            magic=True,
            special_properties=["Heals 2d4+2 hit points"],
            description="A magical potion that restores health"
        )
    }

class InventoryManager:
    """Manages character inventory and equipment"""

    def __init__(self):
        self.weapons = WeaponDatabase.WEAPONS
        self.armor = ArmorDatabase.ARMOR
        self.magic_items = MagicItemDatabase.MAGIC_ITEMS

    def get_item(self, name: str) -> Optional[Union[Weapon, Armor, Item, MagicItem]]:
        """Get any item by name"""
        # Check weapons first
        if name in self.weapons:
            return self.weapons[name]

        # Check armor
        if name in self.armor:
            return self.armor[name]

        # Check magic items
        if name in self.magic_items:
            return self.magic_items[name]

        return None

    def calculate_ac(self, character_data: Dict[str, Any]) -> int:
        """Calculate character's AC based on equipped armor"""
        base_ac = 10
        dex_modifier = character_data.get("dex_modifier", 0)
        equipped_armor = character_data.get("equipped_armor")
        has_shield = character_data.get("has_shield", False)

        if equipped_armor:
            armor = self.get_item(equipped_armor)
            if armor and isinstance(armor, Armor):
                if armor.armor_type == ArmorType.LIGHT:
                    base_ac = armor.base_ac + dex_modifier
                elif armor.armor_type == ArmorType.MEDIUM:
                    max_dex = armor.max_dex_bonus or 2
                    base_ac = armor.base_ac + min(dex_modifier, max_dex)
                elif armor.armor_type == ArmorType.HEAVY:
                    base_ac = armor.base_ac
        else:
            # Unarmored
            base_ac = 10 + dex_modifier

        # Add shield bonus
        if has_shield:
            base_ac += 2

        return base_ac

    def calculate_attack_bonus(self, character_data: Dict[str, Any], weapon_name: str) -> Dict[str, Any]:
        """Calculate attack bonus for a weapon"""
        weapon = self.get_item(weapon_name)
        if not weapon or not isinstance(weapon, Weapon):
            return {"error": "Weapon not found"}

        strength_mod = character_data.get("str_modifier", 0)
        dex_modifier = character_data.get("dex_modifier", 0)
        proficiency_bonus = character_data.get("proficiency_bonus", 2)
        is_proficient = self.is_weapon_proficient(character_data, weapon)

        # Determine ability modifier
        if "finesse" in weapon.properties:
            ability_mod = max(strength_mod, dex_modifier)
        elif weapon.weapon_type in [WeaponType.SIMPLE_RANGED, WeaponType.MARTIAL_RANGED]:
            ability_mod = dex_modifier
        else:
            ability_mod = strength_mod

        # Calculate attack bonus
        attack_bonus = ability_mod
        if is_proficient:
            attack_bonus += proficiency_bonus

        # Calculate damage
        damage_bonus = ability_mod

        return {
            "attack_bonus": attack_bonus,
            "damage_dice": weapon.damage.dice,
            "damage_bonus": damage_bonus,
            "damage_type": weapon.damage.damage_type,
            "versatile_damage": weapon.damage.versatile_dice,
            "properties": weapon.properties,
            "range": f"{weapon.range_normal}/{weapon.range_long}" if weapon.range_normal else "Melee"
        }

    def is_weapon_proficient(self, character_data: Dict[str, Any], weapon: Weapon) -> bool:
        """Check if character is proficient with weapon"""
        weapon_proficiencies = character_data.get("weapon_proficiencies", [])

        # Check specific weapon proficiency
        if weapon.name in weapon_proficiencies:
            return True

        # Check category proficiency
        if weapon.weapon_type == WeaponType.SIMPLE_MELEE and "Simple weapons" in weapon_proficiencies:
            return True
        if weapon.weapon_type == WeaponType.SIMPLE_RANGED and "Simple weapons" in weapon_proficiencies:
            return True
        if weapon.weapon_type == WeaponType.MARTIAL_MELEE and "Martial weapons" in weapon_proficiencies:
            return True
        if weapon.weapon_type == WeaponType.MARTIAL_RANGED and "Martial weapons" in weapon_proficiencies:
            return True

        return False

    def calculate_carrying_capacity(self, strength_score: int) -> Dict[str, int]:
        """Calculate carrying capacity based on Strength"""
        return {
            "carrying_capacity": strength_score * 15,
            "push_drag_lift": strength_score * 30,
            "encumbered_at": strength_score * 5,
            "heavily_encumbered_at": strength_score * 10
        }

    def get_starting_equipment(self, class_name: str, background: str) -> Dict[str, List[str]]:
        """Get starting equipment for class and background"""
        class_equipment = {
            "Fighter": {
                "armor": ["Chain mail", "Shield"],
                "weapons": ["Longsword", "Light crossbow"],
                "gear": ["Dungeoneer's pack", "20 crossbow bolts"]
            },
            "Wizard": {
                "armor": [],
                "weapons": ["Dagger", "Quarterstaff"],
                "gear": ["Spellbook", "Scholar's pack", "Component pouch"]
            },
            "Rogue": {
                "armor": ["Studded leather"],
                "weapons": ["Shortsword", "Shortbow", "Dagger", "Thieves' tools"],
                "gear": ["Burglar's pack", "20 arrows"]
            }
        }

        background_equipment = {
            "Criminal": {
                "gear": ["Crowbar", "Dark clothes", "Belt pouch", "15 gp"]
            },
            "Soldier": {
                "gear": ["Insignia of rank", "Deck of cards", "Common clothes", "10 gp"]
            }
        }

        equipment = class_equipment.get(class_name, {"armor": [], "weapons": [], "gear": []})
        bg_equipment = background_equipment.get(background, {"gear": []})

        return {
            "class_equipment": equipment,
            "background_equipment": bg_equipment
        }

# Global inventory manager instance
inventory_manager = InventoryManager()