# src/character_creation_api.py
"""
Enhanced Character Creation API with comprehensive D&D 5e support
Provides detailed endpoints for race variants, class options, feats, and validation
"""

from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from typing import Dict, List, Optional, Any, Union
from .detailed_character_creator import DetailedCharacterCreator, RacialTrait, AbilityScoreIncrease
from .database import get_db_session
from .character_manager import character_manager

router = APIRouter()
creator = DetailedCharacterCreator()

# Enhanced request models
class AbilityScores(BaseModel):
    strength: int
    dexterity: int
    constitution: int
    intelligence: int
    wisdom: int
    charisma: int

class CharacterCreationStep1(BaseModel):
    """Step 1: Basic character info"""
    name: str
    campaign_id: int

class CharacterCreationStep2(BaseModel):
    """Step 2: Race selection with variant"""
    race: str
    variant: str
    custom_ability_choices: Optional[Dict[str, int]] = None  # For variant human/custom lineage

class CharacterCreationStep3(BaseModel):
    """Step 3: Class selection (subclass chosen later based on class)"""
    class_name: str
    subclass: Optional[str] = None  # Only for classes that choose at level 1

class CharacterCreationStep4(BaseModel):
    """Step 4: Ability scores (various methods)"""
    method: str  # "standard_array", "point_buy", "roll", "manual"
    base_scores: AbilityScores
    point_buy_remaining: Optional[int] = None
    rolled_stats: Optional[List[List[int]]] = None  # For roll method

class CharacterCreationStep5(BaseModel):
    """Step 5: Skills, background, and additional choices"""
    background: str
    skill_choices: List[str]
    language_choices: Optional[List[str]] = None
    tool_proficiencies: Optional[List[str]] = None

class CharacterCreationStep6(BaseModel):
    """Step 6: Feats and final customization"""
    feats: List[str] = []
    additional_ability_increases: Optional[Dict[str, int]] = None
    equipment_choices: Optional[Dict[str, str]] = None

class CompleteCharacterCreation(BaseModel):
    """Complete character creation with all steps"""
    step1: CharacterCreationStep1
    step2: CharacterCreationStep2
    step3: CharacterCreationStep3
    step4: CharacterCreationStep4
    step5: CharacterCreationStep5
    step6: CharacterCreationStep6

class CharacterCreationProgress(BaseModel):
    """Track progress through character creation steps"""
    step1: Optional[CharacterCreationStep1] = None
    step2: Optional[CharacterCreationStep2] = None
    step3: Optional[CharacterCreationStep3] = None
    step4: Optional[CharacterCreationStep4] = None
    step5: Optional[CharacterCreationStep5] = None
    step6: Optional[CharacterCreationStep6] = None
    current_step: int = 1

# API Endpoints

@router.get("/api/character-creation/races")
async def get_race_options():
    """Get all available races and their variants"""
    race_data = {}

    for race_name, race_info in creator.races.items():
        race_data[race_name] = {
            "base_speed": race_info["base_speed"],
            "size": race_info["size"],
            "languages": race_info["languages"],
            "traits": [{"name": trait.name, "description": trait.description}
                      for trait in race_info.get("traits", [])],
            "variants": {}
        }

        if "variants" in race_info:
            for variant_name, variant in race_info["variants"].items():
                race_data[race_name]["variants"][variant_name] = {
                    "ability_increases": [
                        {"ability": inc.ability, "amount": inc.amount}
                        for inc in variant.ability_increases
                    ],
                    "traits": [{"name": trait.name, "description": trait.description}
                              for trait in variant.traits],
                    "speed": variant.speed,
                    "size": variant.size,
                    "extra_language": variant.extra_language,
                    "extra_skill": variant.extra_skill,
                    "proficiencies": variant.proficiencies or []
                }

    return {"races": race_data}

@router.get("/api/character-creation/classes")
async def get_class_options():
    """Get all available classes and their subclasses"""
    class_data = {}

    for class_name, class_info in creator.classes.items():
        # Determine subclass selection level
        subclass_level = 3  # Default for most classes
        if "subclasses" in class_info:
            first_subclass = next(iter(class_info["subclasses"].values()))
            subclass_level = first_subclass.get("level_gained", 3)

        class_data[class_name] = {
            "hit_die": class_info["hit_die"],
            "primary_abilities": class_info["primary_abilities"],
            "saving_throws": class_info["saving_throws"],
            "armor_proficiencies": class_info["armor_proficiencies"],
            "weapon_proficiencies": class_info["weapon_proficiencies"],
            "skill_choices": class_info["skill_choices"],
            "skill_list": class_info["skill_list"],
            "starting_equipment": class_info.get("starting_equipment", {}),
            "spellcasting": class_info.get("spellcasting"),
            "subclass_level": subclass_level,
            "chooses_subclass_at_creation": subclass_level == 1,
            "subclasses": {}
        }

        if "subclasses" in class_info:
            for subclass_name, subclass in class_info["subclasses"].items():
                class_data[class_name]["subclasses"][subclass_name] = {
                    "level_gained": subclass["level_gained"],
                    "features": subclass["features"],
                    "spellcasting": subclass.get("spellcasting")
                }

    return {"classes": class_data}

@router.get("/api/character-creation/feats")
async def get_feat_options():
    """Get all available feats with prerequisites"""
    return {"feats": creator.feats}

@router.get("/api/character-creation/backgrounds")
async def get_background_options():
    """Get available backgrounds with skills and features"""
    backgrounds = {
        # Player's Handbook Backgrounds
        "Acolyte": {
            "skills": ["Insight", "Religion"],
            "languages": 2,
            "tools": [],
            "equipment": ["Holy symbol", "Prayer book", "Incense", "Vestments"],
            "feature": "Shelter of the Faithful"
        },
        "Charlatan": {
            "skills": ["Deception", "Sleight of Hand"],
            "languages": 0,
            "tools": ["Disguise kit", "Forgery kit"],
            "equipment": ["Weighted dice", "Deck of marked cards", "Signet ring"],
            "feature": "False Identity"
        },
        "Criminal": {
            "skills": ["Deception", "Stealth"],
            "languages": 0,
            "tools": ["Thieves' tools", "Gaming set"],
            "equipment": ["Crowbar", "Dark clothes", "Belt pouch"],
            "feature": "Criminal Contact"
        },
        "Entertainer": {
            "skills": ["Acrobatics", "Performance"],
            "languages": 0,
            "tools": ["Disguise kit", "Musical instrument"],
            "equipment": ["Musical instrument", "Love letter", "Costume"],
            "feature": "By Popular Demand"
        },
        "Folk Hero": {
            "skills": ["Animal Handling", "Survival"],
            "languages": 0,
            "tools": ["Artisan's tools", "Vehicles (land)"],
            "equipment": ["Artisan's tools", "Shovel", "Set of clothes"],
            "feature": "Rustic Hospitality"
        },
        "Guild Artisan": {
            "skills": ["Insight", "Persuasion"],
            "languages": 1,
            "tools": ["Artisan's tools"],
            "equipment": ["Artisan's tools", "Letter of introduction", "Traveler's clothes"],
            "feature": "Guild Membership"
        },
        "Hermit": {
            "skills": ["Medicine", "Religion"],
            "languages": 1,
            "tools": ["Herbalism kit"],
            "equipment": ["Herbalism kit", "Scroll case", "Winter blanket"],
            "feature": "Discovery"
        },
        "Noble": {
            "skills": ["History", "Persuasion"],
            "languages": 1,
            "tools": ["Gaming set"],
            "equipment": ["Signet ring", "Scroll of pedigree", "Fine clothes"],
            "feature": "Position of Privilege"
        },
        "Outlander": {
            "skills": ["Athletics", "Survival"],
            "languages": 1,
            "tools": ["Musical instrument"],
            "equipment": ["Staff", "Hunting trap", "Traveler's clothes"],
            "feature": "Wanderer"
        },
        "Sage": {
            "skills": ["Arcana", "History"],
            "languages": 2,
            "tools": [],
            "equipment": ["Ink", "Quill", "Small knife", "Letter"],
            "feature": "Researcher"
        },
        "Sailor": {
            "skills": ["Athletics", "Perception"],
            "languages": 0,
            "tools": ["Navigator's tools", "Vehicles (water)"],
            "equipment": ["Belaying pin", "Silk rope", "Lucky charm"],
            "feature": "Ship's Passage"
        },
        "Soldier": {
            "skills": ["Athletics", "Intimidation"],
            "languages": 0,
            "tools": ["Gaming set", "Vehicles (land)"],
            "equipment": ["Insignia of rank", "Deck of cards", "Clothes"],
            "feature": "Military Rank"
        },
        "Urchin": {
            "skills": ["Sleight of Hand", "Stealth"],
            "languages": 0,
            "tools": ["Disguise kit", "Thieves' tools"],
            "equipment": ["Small knife", "Map of city", "Pet mouse"],
            "feature": "City Secrets"
        },

        # Sword Coast Adventurer's Guide
        "City Watch": {
            "skills": ["Athletics", "Insight"],
            "languages": 2,
            "tools": [],
            "equipment": ["Uniform", "Horn", "Manacles"],
            "feature": "Watcher's Eye"
        },
        "Clan Crafter": {
            "skills": ["History", "Insight"],
            "languages": 1,
            "tools": ["Artisan's tools"],
            "equipment": ["Artisan's tools", "Maker's mark chisel", "Traveler's clothes"],
            "feature": "Respect of the Stout Folk"
        },
        "Cloistered Scholar": {
            "skills": ["History", "Religion"],
            "languages": 2,
            "tools": [],
            "equipment": ["Writing kit", "Borrowed book", "Scholar's robes"],
            "feature": "Library Access"
        },
        "Courtier": {
            "skills": ["Insight", "Persuasion"],
            "languages": 2,
            "tools": [],
            "equipment": ["Fine clothes", "Signet ring", "Scroll of pedigree"],
            "feature": "Court Functionary"
        },
        "Faction Agent": {
            "skills": ["Insight", "Persuasion"],
            "languages": 2,
            "tools": [],
            "equipment": ["Badge", "Copy of seminal faction text", "Common clothes"],
            "feature": "Safe Haven"
        },
        "Far Traveler": {
            "skills": ["Insight", "Perception"],
            "languages": 1,
            "tools": ["Gaming set", "Musical instrument"],
            "equipment": ["Traveler's clothes", "Gaming set", "Poorly wrought maps"],
            "feature": "All Eyes on You"
        },
        "Inheritor": {
            "skills": ["Survival", "Arcana"],
            "languages": 1,
            "tools": ["Gaming set", "Musical instrument"],
            "equipment": ["Inheritance", "Traveler's clothes", "Belt pouch"],
            "feature": "Inheritance"
        },
        "Investigator": {
            "skills": ["Insight", "Investigation"],
            "languages": 2,
            "tools": [],
            "equipment": ["Uniform", "Horn", "Manacles"],
            "feature": "Official Inquiry"
        },
        "Knight of the Order": {
            "skills": ["Arcana", "Religion"],
            "languages": 1,
            "tools": ["Gaming set", "Musical instrument"],
            "equipment": ["Traveler's clothes", "Signet", "Banner"],
            "feature": "Knightly Regard"
        },
        "Mercenary Veteran": {
            "skills": ["Athletics", "Persuasion"],
            "languages": 1,
            "tools": ["Gaming set", "Vehicles (land)"],
            "equipment": ["Uniform", "Insignia of rank", "Deck of cards"],
            "feature": "Mercenary Life"
        },
        "Urban Bounty Hunter": {
            "skills": ["Deception", "Insight", "Persuasion", "Stealth"],
            "languages": 0,
            "tools": ["Thieves' tools", "Gaming set", "Musical instrument"],
            "equipment": ["Clothes", "Belt pouch"],
            "feature": "Ear to the Ground"
        },
        "Uthgardt Tribe Member": {
            "skills": ["Athletics", "Survival"],
            "languages": 1,
            "tools": ["Artisan's tools", "Musical instrument"],
            "equipment": ["Hunting spear", "Traveler's clothes", "Belt pouch"],
            "feature": "Uthgardt Heritage"
        },
        "Waterdhavian Noble": {
            "skills": ["History", "Persuasion"],
            "languages": 1,
            "tools": ["Gaming set", "Musical instrument"],
            "equipment": ["Fine clothes", "Signet ring", "Scroll of pedigree"],
            "feature": "Kept in Style"
        },

        # Curse of Strahd
        "Haunted One": {
            "skills": ["Arcana", "Investigation", "Religion", "Survival"],
            "languages": 1,
            "tools": [],
            "equipment": ["Monster hunter's pack", "Gothic trinket", "Belt pouch"],
            "feature": "Heart of Darkness"
        },

        # Storm King's Thunder
        "Storm Herald": {
            "skills": ["Athletics", "Survival"],
            "languages": 1,
            "tools": ["Artisan's tools"],
            "equipment": ["Horn", "Traveler's clothes", "Belt pouch"],
            "feature": "Storm's Blessing"
        },

        # Tomb of Annihilation
        "Anthropologist": {
            "skills": ["Insight", "Religion"],
            "languages": 2,
            "tools": [],
            "equipment": ["Leather-bound diary", "Ink", "Quill"],
            "feature": "Adept Linguist"
        },
        "Archaeologist": {
            "skills": ["History", "Survival"],
            "languages": 1,
            "tools": ["Cartographer's tools", "Navigator's tools"],
            "equipment": ["Wooden case", "Map case", "Traveler's clothes"],
            "feature": "Dust Digger"
        },

        # Waterdeep: Dragon Heist
        "Grinner": {
            "skills": ["Deception", "Performance"],
            "languages": 0,
            "tools": ["Disguise kit", "Musical instrument"],
            "equipment": ["Musical instrument", "Love letter", "Costume"],
            "feature": "Ballad of the Grinning Fool"
        },
        "Harpers Agent": {
            "skills": ["Investigation", "Insight"],
            "languages": 2,
            "tools": [],
            "equipment": ["Badge", "Copy of faction text", "Common clothes"],
            "feature": "Harper Pin"
        },
        "Lords' Alliance Agent": {
            "skills": ["Investigation", "Persuasion"],
            "languages": 2,
            "tools": [],
            "equipment": ["Badge", "Copy of faction text", "Common clothes"],
            "feature": "Alliance Contacts"
        },
        "Zhentarim Agent": {
            "skills": ["Deception", "Intimidation"],
            "languages": 1,
            "tools": ["Thieves' tools"],
            "equipment": ["Badge", "Copy of faction text", "Common clothes"],
            "feature": "Black Network Connections"
        },

        # Ghosts of Saltmarsh
        "Fisher": {
            "skills": ["History", "Survival"],
            "languages": 1,
            "tools": ["Fishing tackle", "Vehicles (water)"],
            "equipment": ["Fishing tackle", "Net", "Traveler's clothes"],
            "feature": "Harvest the Water"
        },
        "Marine": {
            "skills": ["Athletics", "Survival"],
            "languages": 1,
            "tools": ["Vehicles (land)", "Vehicles (water)"],
            "equipment": ["Insignia of rank", "Deck of cards", "Clothes"],
            "feature": "Steady"
        },
        "Shipwright": {
            "skills": ["History", "Perception"],
            "languages": 1,
            "tools": ["Carpenter's tools", "Vehicles (water)"],
            "equipment": ["Carpenter's tools", "Traveler's clothes", "Belt pouch"],
            "feature": "I'll Patch It!"
        },
        "Smuggler": {
            "skills": ["Athletics", "Deception"],
            "languages": 0,
            "tools": ["Vehicles (water)"],
            "equipment": ["Fancy leather vest", "Belt pouch"],
            "feature": "Down Low"
        },

        # Baldur's Gate: Descent into Avernus
        "Flaming Fist": {
            "skills": ["Athletics", "Intimidation"],
            "languages": 1,
            "tools": ["Gaming set"],
            "equipment": ["Uniform", "Horn", "Belt pouch"],
            "feature": "Flaming Fist Membership"
        },
        "Guild Member": {
            "skills": ["Insight", "Persuasion"],
            "languages": 1,
            "tools": ["Artisan's tools"],
            "equipment": ["Artisan's tools", "Letter of introduction", "Traveler's clothes"],
            "feature": "Guild Membership"
        },
        "Lower City": {
            "skills": ["Intimidation", "Sleight of Hand"],
            "languages": 0,
            "tools": ["Thieves' tools"],
            "equipment": ["Common clothes", "Belt pouch"],
            "feature": "Down and Dirty Fighting"
        },
        "Outer City": {
            "skills": ["Animal Handling", "Survival"],
            "languages": 1,
            "tools": ["Artisan's tools"],
            "equipment": ["Artisan's tools", "Traveler's clothes", "Belt pouch"],
            "feature": "Outlander Variant"
        },
        "Patriar": {
            "skills": ["History", "Persuasion"],
            "languages": 1,
            "tools": ["Gaming set"],
            "equipment": ["Fine clothes", "Signet ring", "Scroll of pedigree"],
            "feature": "Patriar Influence"
        },
        "Upper City": {
            "skills": ["History", "Persuasion"],
            "languages": 1,
            "tools": ["Artisan's tools"],
            "equipment": ["Fine clothes", "Signet ring", "Scroll of pedigree"],
            "feature": "Patriar Connection"
        },

        # Icewind Dale: Rime of the Frostmaiden
        "Reghed Nomad": {
            "skills": ["Animal Handling", "Survival"],
            "languages": 1,
            "tools": ["Herbalism kit"],
            "equipment": ["Traveler's clothes", "Belt pouch"],
            "feature": "Nomadic Origins"
        },
        "Ten-Towns Trader": {
            "skills": ["History", "Persuasion"],
            "languages": 1,
            "tools": ["Vehicles (land)"],
            "equipment": ["Traveler's clothes", "Belt pouch"],
            "feature": "Supply and Demand"
        },

        # Candlekeep Mysteries
        "Candlekeep Researcher": {
            "skills": ["History", "Investigation"],
            "languages": 2,
            "tools": [],
            "equipment": ["Writing kit", "Borrowed book", "Scholar's robes"],
            "feature": "Library Access"
        },

        # The Wild Beyond the Witchlight
        "Feylost": {
            "skills": ["Deception", "Survival"],
            "languages": 1,
            "tools": ["Musical instrument"],
            "equipment": ["Musical instrument", "Traveler's clothes", "Feywild trinket"],
            "feature": "Feywild Connection"
        },
        "Witchlight Hand": {
            "skills": ["Performance", "Sleight of Hand"],
            "languages": 1,
            "tools": ["Disguise kit", "Musical instrument"],
            "equipment": ["Costume", "Deck of cards", "Feywild trinket"],
            "feature": "Carnival Fixture"
        },

        # Strixhaven: A Curriculum of Chaos
        "Lorehold Student": {
            "skills": ["History", "Religion"],
            "languages": 2,
            "tools": [],
            "equipment": ["Bottle of black ink", "Quill", "School uniform"],
            "feature": "Lorehold Initiate"
        },
        "Prismari Student": {
            "skills": ["Acrobatics", "Performance"],
            "languages": 1,
            "tools": ["Artisan's tools", "Musical instrument"],
            "equipment": ["Artisan's tools", "School uniform"],
            "feature": "Prismari Initiate"
        },
        "Quandrix Student": {
            "skills": ["Arcana", "Nature"],
            "languages": 2,
            "tools": [],
            "equipment": ["Bottle of black ink", "Quill", "School uniform"],
            "feature": "Quandrix Initiate"
        },
        "Silverquill Student": {
            "skills": ["Intimidation", "Persuasion"],
            "languages": 2,
            "tools": [],
            "equipment": ["Bottle of black ink", "Quill", "School uniform"],
            "feature": "Silverquill Initiate"
        },
        "Witherbloom Student": {
            "skills": ["Arcana", "Nature"],
            "languages": 1,
            "tools": ["Herbalism kit"],
            "equipment": ["Herbalism kit", "School uniform"],
            "feature": "Witherbloom Initiate"
        },

        # Spelljammer: Adventures in Space
        "Astral Drifter": {
            "skills": ["Insight", "Religion"],
            "languages": 2,
            "tools": [],
            "equipment": ["Traveler's clothes", "Belt pouch", "Astral shard"],
            "feature": "Divine Insight"
        },
        "Wildspacer": {
            "skills": ["Athletics", "Survival"],
            "languages": 1,
            "tools": ["Navigator's tools"],
            "equipment": ["Traveler's clothes", "Belt pouch", "Star chart"],
            "feature": "Wildspace Adaptation"
        },

        # Dragonlance: Shadow of the Dragon Queen
        "Knight of Solamnia": {
            "skills": ["Athletics", "Survival"],
            "languages": 2,
            "tools": [],
            "equipment": ["Traveler's clothes", "Belt pouch", "Insignia"],
            "feature": "Squire of Solamnia"
        },
        "Mage of High Sorcery": {
            "skills": ["Arcana", "History"],
            "languages": 2,
            "tools": [],
            "equipment": ["Traveler's clothes", "Belt pouch", "Crystal focus"],
            "feature": "Initiate of High Sorcery"
        }
    }
    return {"backgrounds": backgrounds}

@router.post("/api/character-creation/ability-scores/generate")
async def generate_ability_scores(method: str):
    """Generate ability scores using different methods"""
    if method == "standard_array":
        return {
            "method": "standard_array",
            "scores": [15, 14, 13, 12, 10, 8],
            "description": "Assign these values to your six abilities"
        }

    elif method == "point_buy":
        return {
            "method": "point_buy",
            "base_scores": {"str": 8, "dex": 8, "con": 8, "int": 8, "wis": 8, "cha": 8},
            "points_available": 27,
            "costs": {
                8: 0, 9: 1, 10: 2, 11: 3, 12: 4, 13: 5, 14: 7, 15: 9
            },
            "description": "Spend points to increase abilities from 8 to 15"
        }

    elif method == "roll":
        import random
        rolls = []
        for _ in range(6):
            roll_set = [random.randint(1, 6) for _ in range(4)]
            roll_set.sort(reverse=True)
            total = sum(roll_set[:3])  # Drop lowest
            rolls.append({
                "rolls": roll_set,
                "total": total,
                "dropped": roll_set[3]
            })

        return {
            "method": "roll",
            "results": rolls,
            "totals": [r["total"] for r in rolls],
            "description": "Roll 4d6, drop lowest, for each ability"
        }

    else:
        raise HTTPException(status_code=400, detail="Invalid ability score method")

@router.post("/api/character-creation/validate-race-choice")
async def validate_race_choice(choice: CharacterCreationStep2):
    """Validate race and variant selection, return available options"""
    if choice.race not in creator.races:
        raise HTTPException(status_code=400, detail=f"Invalid race: {choice.race}")

    race_data = creator.races[choice.race]

    if "variants" in race_data:
        if choice.variant not in race_data["variants"]:
            raise HTTPException(status_code=400, detail=f"Invalid variant: {choice.variant}")

        variant_data = race_data["variants"][choice.variant]

        # Check if this variant requires custom choices
        custom_choices_needed = {}

        # Variant Human gets to choose 2 abilities to increase
        if choice.variant == "Variant Human":
            custom_choices_needed["ability_increases"] = {
                "count": 2,
                "amount": 1,
                "description": "Choose two different abilities to increase by 1"
            }
            custom_choices_needed["feat_choice"] = {
                "count": 1,
                "description": "Choose one feat at 1st level"
            }

        # Custom Lineage gets flexible ability increases
        elif choice.variant == "Custom Lineage":
            custom_choices_needed["ability_increases"] = {
                "options": [
                    {"count": 1, "amount": 2, "description": "Increase one ability by 2"},
                    {"count": 2, "amount": 1, "description": "Increase two abilities by 1"}
                ]
            }
            custom_choices_needed["size_choice"] = ["Small", "Medium"]
            custom_choices_needed["darkvision_or_skill"] = [
                "Darkvision (60 feet)",
                "Extra skill proficiency"
            ]
            custom_choices_needed["feat_choice"] = {
                "count": 1,
                "description": "Choose one feat at 1st level"
            }

        return {
            "valid": True,
            "race_traits": [{"name": trait.name, "description": trait.description}
                           for trait in race_data.get("traits", [])],
            "variant_traits": [{"name": trait.name, "description": trait.description}
                              for trait in variant_data.traits],
            "ability_increases": [{"ability": inc.ability, "amount": inc.amount}
                                 for inc in variant_data.ability_increases],
            "custom_choices_needed": custom_choices_needed
        }

    return {"valid": True, "custom_choices_needed": {}}

@router.post("/api/character-creation/calculate-final-abilities")
async def calculate_final_abilities(
    base_scores: AbilityScores,
    race_choice: CharacterCreationStep2
):
    """Calculate final ability scores after racial bonuses"""
    base_abilities = {
        "strength": base_scores.strength,
        "dexterity": base_scores.dexterity,
        "constitution": base_scores.constitution,
        "intelligence": base_scores.intelligence,
        "wisdom": base_scores.wisdom,
        "charisma": base_scores.charisma
    }

    # Apply racial bonuses
    final_abilities = creator.apply_racial_bonuses(
        base_abilities, race_choice.race, race_choice.variant
    )

    # Apply custom choices for variant human/custom lineage
    if race_choice.custom_ability_choices:
        for ability, bonus in race_choice.custom_ability_choices.items():
            if ability in final_abilities:
                final_abilities[ability] += bonus

    # Calculate modifiers
    modifiers = creator.calculate_ability_modifiers(final_abilities)

    return {
        "final_abilities": final_abilities,
        "modifiers": modifiers,
        "changes": {
            ability: final_abilities[ability] - base_abilities[ability]
            for ability in final_abilities
        }
    }

@router.post("/api/character-creation/calculate-stats")
async def calculate_character_stats(
    class_name: str,
    level: int,
    constitution_modifier: int,
    dexterity_modifier: int,
    feats: List[str] = [],
    armor_type: str = "none",
    shield: bool = False
):
    """Calculate derived character statistics"""
    # Calculate HP
    tough_feat = "Tough" in feats
    avg_hp, max_hp = creator.calculate_hit_points(
        class_name, level, constitution_modifier, tough_feat
    )

    # Calculate AC
    ac = creator.calculate_armor_class(dexterity_modifier, armor_type, shield)

    # Get proficiency bonus
    prof_bonus = 2 + ((level - 1) // 4)  # Standard D&D progression

    # Get class data
    class_data = creator.classes.get(class_name, {})

    return {
        "hit_points": {
            "average": avg_hp,
            "maximum_possible": max_hp,
            "hit_die": class_data.get("hit_die", 8)
        },
        "armor_class": ac,
        "proficiency_bonus": prof_bonus,
        "speed": 30,  # Would be modified by race
        "saving_throws": class_data.get("saving_throws", []),
        "skill_proficiencies": class_data.get("skill_list", [])
    }

@router.post("/api/character-creation/validate-class-choice")
async def validate_class_choice(class_name: str, level: int = 1):
    """Validate class selection and return subclass requirements"""
    if class_name not in creator.classes:
        raise HTTPException(status_code=400, detail=f"Invalid class: {class_name}")

    class_data = creator.classes[class_name]

    # Determine subclass selection requirements
    subclass_level = 3  # Default
    if "subclasses" in class_data:
        first_subclass = next(iter(class_data["subclasses"].values()))
        subclass_level = first_subclass.get("level_gained", 3)

    requires_subclass_now = (level >= subclass_level)
    available_subclasses = list(class_data.get("subclasses", {}).keys()) if requires_subclass_now else []

    return {
        "valid": True,
        "class_name": class_name,
        "subclass_level": subclass_level,
        "requires_subclass_at_creation": subclass_level == 1,
        "requires_subclass_now": requires_subclass_now,
        "available_subclasses": available_subclasses,
        "hit_die": class_data["hit_die"],
        "primary_abilities": class_data["primary_abilities"],
        "saving_throws": class_data["saving_throws"]
    }

@router.post("/api/character-creation/validate-build")
async def validate_character_build(character: CompleteCharacterCreation):
    """Validate complete character build for D&D 5e compliance"""
    errors = []

    # Check if subclass is required and provided
    class_data = creator.classes.get(character.step3.class_name)
    if class_data and "subclasses" in class_data:
        first_subclass = next(iter(class_data["subclasses"].values()))
        subclass_level = first_subclass.get("level_gained", 3)

        if subclass_level == 1 and not character.step3.subclass:
            errors.append(f"{character.step3.class_name} must choose a subclass at 1st level")
        elif subclass_level > 1 and character.step3.subclass:
            errors.append(f"{character.step3.class_name} doesn't choose a subclass until level {subclass_level}")

    # Convert to format expected by validator
    character_data = {
        "race": character.step2.race,
        "variant": character.step2.variant,
        "class_name": character.step3.class_name,
        "subclass": character.step3.subclass,
        "abilities": {
            "strength": character.step4.base_scores.strength,
            "dexterity": character.step4.base_scores.dexterity,
            "constitution": character.step4.base_scores.constitution,
            "intelligence": character.step4.base_scores.intelligence,
            "wisdom": character.step4.base_scores.wisdom,
            "charisma": character.step4.base_scores.charisma
        },
        "background": character.step5.background,
        "skills": character.step5.skill_choices,
        "feats": character.step6.feats
    }

    # Run additional validation
    additional_errors = creator.validate_character_build(character_data)
    errors.extend(additional_errors)

    return {
        "valid": len(errors) == 0,
        "errors": errors,
        "warnings": []  # Could add warnings for suboptimal choices
    }

@router.post("/api/character-creation/finalize")
async def finalize_character_creation(
    character: CompleteCharacterCreation,
    user_id: str = "player1",
    db: AsyncSession = Depends(get_db_session)
):
    """Create the final character in the database"""

    # Validate the build first
    validation = await validate_character_build(character)
    if not validation["valid"]:
        raise HTTPException(status_code=400, detail={
            "message": "Character build is not valid",
            "errors": validation["errors"]
        })

    # Calculate final stats
    base_abilities = {
        "strength": character.step4.base_scores.strength,
        "dexterity": character.step4.base_scores.dexterity,
        "constitution": character.step4.base_scores.constitution,
        "intelligence": character.step4.base_scores.intelligence,
        "wisdom": character.step4.base_scores.wisdom,
        "charisma": character.step4.base_scores.charisma
    }

    # Apply racial bonuses
    final_abilities = creator.apply_racial_bonuses(
        base_abilities, character.step2.race, character.step2.variant
    )

    # Apply custom ability choices if any
    if character.step2.custom_ability_choices:
        for ability, bonus in character.step2.custom_ability_choices.items():
            final_abilities[ability] += bonus

    # Calculate modifiers
    modifiers = creator.calculate_ability_modifiers(final_abilities)

    # Calculate HP and AC
    tough_feat = "Tough" in character.step6.feats
    avg_hp, _ = creator.calculate_hit_points(
        character.step3.class_name, 1, modifiers["constitution"], tough_feat
    )

    ac = creator.calculate_armor_class(modifiers["dexterity"])

    # Get racial traits
    try:
        racial_traits = creator.get_racial_traits(
            character.step2.race, character.step2.variant
        )
    except Exception as e:
        print(f"Error getting racial traits: {e}")
        racial_traits = []

    # Prepare character data for database
    character_data = {
        "campaign_id": character.step1.campaign_id,
        "user_id": user_id,
        "name": character.step1.name,
        "race": f"{character.step2.race} ({character.step2.variant})",
        "class_name": character.step3.class_name,
        "background": character.step5.background,
        "level": 1,
        "abilities": final_abilities,
        "skills": {skill: True for skill in character.step5.skill_choices},
        "saving_throws": {
            st.lower(): True for st in creator.classes[character.step3.class_name]["saving_throws"]
        },
        "max_hp": avg_hp,
        "armor_class": ac,
        "speed": creator.races[character.step2.race]["base_speed"],
        "features": [
            {
                "name": trait.name,
                "source": "race",
                "description": trait.description,
                "level_gained": getattr(trait, 'level_gained', 1)
            } for trait in racial_traits
        ] + [
            {
                "name": feat,
                "source": "feat",
                "description": creator.feats.get(feat, {}).get("benefits", [""])[0],
                "level_gained": 1
            } for feat in character.step6.feats
        ],
        "equipment": []  # Would be populated based on class starting equipment
    }

    # Create character in database
    try:
        new_character = await character_manager.create_character(db, character_data)
        return {
            "success": True,
            "character_id": new_character.id,
            "message": f"Character '{character.step1.name}' created successfully"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create character: {str(e)}")

@router.post("/api/character-creation/get-summary")
async def get_character_creation_summary(progress: CharacterCreationProgress):
    """Get a formatted summary of current character creation progress"""
    summary = {
        "current_step": progress.current_step,
        "completed_steps": [],
        "selections": {}
    }

    # Step 1: Basic Info
    if progress.step1:
        summary["completed_steps"].append(1)
        summary["selections"]["name"] = progress.step1.name
        summary["selections"]["campaign_id"] = progress.step1.campaign_id

    # Step 2: Race and Variant
    if progress.step2:
        summary["completed_steps"].append(2)
        race_data = creator.races.get(progress.step2.race, {})
        variant_data = race_data.get("variants", {}).get(progress.step2.variant, {})

        summary["selections"]["race"] = {
            "race": progress.step2.race,
            "variant": progress.step2.variant,
            "speed": variant_data.speed if hasattr(variant_data, 'speed') else race_data.get("base_speed", 30),
            "size": variant_data.size if hasattr(variant_data, 'size') else race_data.get("size", "Medium"),
            "languages": race_data.get("languages", []),
            "ability_increases": [
                {"ability": inc.ability, "amount": inc.amount}
                for inc in variant_data.ability_increases
            ] if hasattr(variant_data, 'ability_increases') else [],
            "traits": [
                {"name": trait.name, "description": trait.description}
                for trait in race_data.get("traits", [])
            ] + ([
                {"name": trait.name, "description": trait.description}
                for trait in variant_data.traits
            ] if hasattr(variant_data, 'traits') else [])
        }

    # Step 3: Class
    if progress.step3:
        summary["completed_steps"].append(3)
        class_data = creator.classes.get(progress.step3.class_name, {})

        # Determine subclass info
        subclass_level = 3
        if "subclasses" in class_data:
            first_subclass = next(iter(class_data["subclasses"].values()))
            subclass_level = first_subclass.get("level_gained", 3)

        summary["selections"]["class"] = {
            "class_name": progress.step3.class_name,
            "subclass": progress.step3.subclass,
            "hit_die": class_data.get("hit_die", 8),
            "primary_abilities": class_data.get("primary_abilities", []),
            "saving_throws": class_data.get("saving_throws", []),
            "skill_choices": class_data.get("skill_choices", 0),
            "subclass_level": subclass_level,
            "chooses_subclass_now": subclass_level == 1,
            "spellcasting": class_data.get("spellcasting", {})
        }

    # Step 4: Ability Scores
    if progress.step4:
        summary["completed_steps"].append(4)

        # Calculate final abilities with racial bonuses
        base_abilities = {
            "strength": progress.step4.base_scores.strength,
            "dexterity": progress.step4.base_scores.dexterity,
            "constitution": progress.step4.base_scores.constitution,
            "intelligence": progress.step4.base_scores.intelligence,
            "wisdom": progress.step4.base_scores.wisdom,
            "charisma": progress.step4.base_scores.charisma
        }

        final_abilities = base_abilities.copy()
        if progress.step2:
            final_abilities = creator.apply_racial_bonuses(
                base_abilities, progress.step2.race, progress.step2.variant
            )

            # Apply custom choices for variant human/custom lineage
            if progress.step2.custom_ability_choices:
                for ability, bonus in progress.step2.custom_ability_choices.items():
                    final_abilities[ability] += bonus

        # Calculate modifiers
        modifiers = creator.calculate_ability_modifiers(final_abilities)

        summary["selections"]["abilities"] = {
            "method": progress.step4.method,
            "base_scores": base_abilities,
            "final_scores": final_abilities,
            "modifiers": modifiers,
            "racial_bonuses": {
                ability: final_abilities[ability] - base_abilities[ability]
                for ability in final_abilities
            }
        }

    # Step 5: Background and Skills
    if progress.step5:
        summary["completed_steps"].append(5)
        summary["selections"]["background"] = {
            "background": progress.step5.background,
            "skill_choices": progress.step5.skill_choices,
            "languages": progress.step5.language_choices or [],
            "tools": progress.step5.tool_proficiencies or []
        }

    # Step 6: Feats and Final
    if progress.step6:
        summary["completed_steps"].append(6)
        summary["selections"]["final"] = {
            "feats": progress.step6.feats,
            "additional_asi": progress.step6.additional_ability_increases or {},
            "equipment": progress.step6.equipment_choices or {}
        }

    # Calculate derived stats if we have enough info
    if progress.step3 and progress.step4:
        con_mod = summary["selections"]["abilities"]["modifiers"]["constitution"]
        class_data = creator.classes.get(progress.step3.class_name, {})
        hit_die = class_data.get("hit_die", 8)

        # Calculate HP
        avg_hp = hit_die + con_mod
        max_hp = hit_die + con_mod

        # Calculate AC (basic, would need equipment for full calculation)
        dex_mod = summary["selections"]["abilities"]["modifiers"]["dexterity"]
        base_ac = 10 + dex_mod

        summary["derived_stats"] = {
            "hit_points": {"average": avg_hp, "maximum": max_hp},
            "armor_class": base_ac,
            "proficiency_bonus": 2,
            "speed": summary["selections"]["race"]["speed"] if "race" in summary["selections"] else 30
        }

    return summary

# Helper endpoint for getting character creation progress
@router.get("/api/character-creation/options-summary")
async def get_creation_options_summary():
    """Get a summary of all character creation options for frontend"""
    return {
        "races": list(creator.races.keys()),
        "classes": list(creator.classes.keys()),
        "ability_methods": creator.get_ability_score_methods(),
        "feat_count": len(creator.feats),
        "background_options": [
            "Acolyte", "Criminal", "Folk Hero", "Noble", "Sage", "Soldier"
        ]
    }