# src/level_progression.py
"""
D&D 5e Level Progression System
Handles leveling up, experience points, and milestone tracking
"""

from dataclasses import dataclass
from typing import Dict, List, Optional, Set, Any, Tuple
from enum import Enum

class ProgressionType(Enum):
    EXPERIENCE = "experience"
    MILESTONE = "milestone"
    SESSION_BASED = "session_based"

@dataclass
class LevelProgression:
    level: int
    experience_required: int
    proficiency_bonus: int
    features: List[str]
    ability_score_improvement: bool = False
    hit_die_increase: int = 1

@dataclass
class ClassFeature:
    name: str
    level: int
    description: str
    class_name: str
    subclass: Optional[str] = None
    choices: Optional[List[str]] = None
    choice_type: Optional[str] = None

@dataclass
class Milestone:
    name: str
    description: str
    target_level: int
    act_number: int
    completed: bool = False

class ExperienceTable:
    """D&D 5e Experience Point progression table"""

    XP_TABLE = {
        1: 0,
        2: 300,
        3: 900,
        4: 2700,
        5: 6500,
        6: 14000,
        7: 23000,
        8: 34000,
        9: 48000,
        10: 64000,
        11: 85000,
        12: 100000,
        13: 120000,
        14: 140000,
        15: 165000,
        16: 195000,
        17: 225000,
        18: 265000,
        19: 305000,
        20: 355000
    }

    PROFICIENCY_BONUS = {
        1: 2, 2: 2, 3: 2, 4: 2, 5: 3, 6: 3, 7: 3, 8: 3, 9: 4, 10: 4,
        11: 4, 12: 4, 13: 5, 14: 5, 15: 5, 16: 5, 17: 6, 18: 6, 19: 6, 20: 6
    }

    @classmethod
    def get_level_from_xp(cls, experience_points: int) -> int:
        """Get character level from experience points"""
        for level in range(20, 0, -1):
            if experience_points >= cls.XP_TABLE[level]:
                return level
        return 1

    @classmethod
    def get_xp_for_level(cls, level: int) -> int:
        """Get XP required for a specific level"""
        return cls.XP_TABLE.get(level, 0)

    @classmethod
    def get_xp_to_next_level(cls, current_xp: int) -> int:
        """Get XP needed to reach next level"""
        current_level = cls.get_level_from_xp(current_xp)
        if current_level >= 20:
            return 0
        next_level_xp = cls.XP_TABLE[current_level + 1]
        return next_level_xp - current_xp

class ClassProgression:
    """Manages class-specific progression features"""

    CLASS_FEATURES = {
        "Fighter": {
            1: [
                ClassFeature("Fighting Style", 1, "Choose a fighting style", "Fighter",
                               choices=["Archery (+2 to ranged attacks)", "Defense (+1 AC in armor)", "Dueling (+2 damage with one-handed weapons)",
                                       "Great Weapon Fighting (reroll 1s and 2s on damage)", "Protection (use shield to impose disadvantage)",
                                       "Two-Weapon Fighting (add ability modifier to off-hand damage)", "Blind Fighting (see in darkness within 10 feet)",
                                       "Interception (reduce damage to nearby allies)", "Superior Technique (learn one maneuver)",
                                       "Thrown Weapon Fighting (+2 damage with thrown weapons)", "Unarmed Fighting (improved unarmed strikes)"],
                               choice_type="fighting_style"),
                ClassFeature("Second Wind", 1, "Regain 1d10 + fighter level hit points as bonus action (1/short rest)", "Fighter")
            ],
            2: [ClassFeature("Action Surge", 2, "Take an additional action on your turn (1/short rest)", "Fighter")],
            3: [ClassFeature("Martial Archetype", 3, "Choose your martial archetype", "Fighter",
                               choices=["Champion", "Battle Master", "Eldritch Knight", "Arcane Archer", "Cavalier", "Samurai", "Echo Knight"],
                               choice_type="subclass")],
            4: [ClassFeature("Ability Score Improvement", 4, "Increase ability scores or take feat", "Fighter")],
            5: [ClassFeature("Extra Attack", 5, "Attack twice when taking Attack action", "Fighter")],
            6: [ClassFeature("Ability Score Improvement", 6, "Increase ability scores or take feat", "Fighter")],
            7: [ClassFeature("Martial Archetype Feature", 7, "Gain archetype feature", "Fighter")],
            8: [ClassFeature("Ability Score Improvement", 8, "Increase ability scores or take feat", "Fighter")],
            9: [ClassFeature("Indomitable", 9, "Reroll a failed saving throw (1/long rest)", "Fighter")],
            10: [ClassFeature("Martial Archetype Feature", 10, "Gain archetype feature", "Fighter")],
            11: [ClassFeature("Extra Attack (2)", 11, "Attack three times when taking Attack action", "Fighter")],
            12: [ClassFeature("Ability Score Improvement", 12, "Increase ability scores or take feat", "Fighter")],
            13: [ClassFeature("Indomitable (2 uses)", 13, "Use Indomitable twice per rest", "Fighter")],
            14: [ClassFeature("Ability Score Improvement", 14, "Increase ability scores or take feat", "Fighter")],
            15: [ClassFeature("Martial Archetype Feature", 15, "Gain archetype feature", "Fighter")],
            16: [ClassFeature("Ability Score Improvement", 16, "Increase ability scores or take feat", "Fighter")],
            17: [ClassFeature("Action Surge (2 uses)", 17, "Use Action Surge twice per rest", "Fighter"),
                 ClassFeature("Indomitable (3 uses)", 17, "Use Indomitable three times per rest", "Fighter")],
            18: [ClassFeature("Martial Archetype Feature", 18, "Gain archetype feature", "Fighter")],
            19: [ClassFeature("Ability Score Improvement", 19, "Increase ability scores or take feat", "Fighter")],
            20: [ClassFeature("Extra Attack (3)", 20, "Attack four times when taking Attack action", "Fighter")]
        },

        "Wizard": {
            1: [
                ClassFeature("Spellcasting", 1, "Cast wizard spells. Spell save DC = 8 + prof + Int mod. Spell attack = prof + Int mod. Prepare spells = Int mod + wizard level (min 1)", "Wizard"),
                ClassFeature("Arcane Recovery", 1, "Recover spell slots on short rest. Total slot levels = half wizard level (rounded up)", "Wizard")
            ],
            2: [ClassFeature("Arcane Tradition", 2, "Choose your arcane tradition", "Wizard",
                               choices=["School of Abjuration", "School of Conjuration", "School of Divination", "School of Enchantment",
                                       "School of Evocation", "School of Illusion", "School of Necromancy", "School of Transmutation",
                                       "School of War Magic", "School of Chronurgy Magic"],
                               choice_type="subclass")],
            3: [ClassFeature("Cantrip Formulas", 3, "Replace known cantrips", "Wizard")],
            4: [ClassFeature("Ability Score Improvement", 4, "Increase ability scores or take feat", "Wizard")],
            5: [ClassFeature("Arcane Tradition Feature", 5, "Gain tradition feature", "Wizard")],
            6: [ClassFeature("Arcane Tradition Feature", 6, "Gain tradition feature", "Wizard")],
            8: [ClassFeature("Ability Score Improvement", 8, "Increase ability scores or take feat", "Wizard")],
            10: [ClassFeature("Arcane Tradition Feature", 10, "Gain tradition feature", "Wizard")],
            12: [ClassFeature("Ability Score Improvement", 12, "Increase ability scores or take feat", "Wizard")],
            14: [ClassFeature("Arcane Tradition Feature", 14, "Gain tradition feature", "Wizard")],
            16: [ClassFeature("Ability Score Improvement", 16, "Increase ability scores or take feat", "Wizard")],
            18: [ClassFeature("Spell Mastery", 18, "Cast certain spells without expending slots", "Wizard")],
            19: [ClassFeature("Ability Score Improvement", 19, "Increase ability scores or take feat", "Wizard")],
            20: [ClassFeature("Signature Spells", 20, "Cast two 3rd level spells without expending slots", "Wizard")]
        },

        "Rogue": {
            1: [
                ClassFeature("Expertise", 1, "Double proficiency bonus for chosen skills", "Rogue"),
                ClassFeature("Sneak Attack", 1, "Deal extra damage when conditions are met", "Rogue"),
                ClassFeature("Thieves' Cant", 1, "Secret language of rogues", "Rogue")
            ],
            2: [ClassFeature("Cunning Action", 2, "Dash, Disengage, or Hide as bonus action", "Rogue")],
            3: [ClassFeature("Roguish Archetype", 3, "Choose your roguish archetype", "Rogue",
                               choices=["Thief", "Assassin", "Arcane Trickster", "Mastermind", "Swashbuckler", "Inquisitive", "Scout", "Soulknife", "Phantom"],
                               choice_type="subclass")],
            4: [ClassFeature("Ability Score Improvement", 4, "Increase ability scores or take feat", "Rogue")],
            5: [ClassFeature("Uncanny Dodge", 5, "Halve damage from one attack per turn", "Rogue")],
            6: [ClassFeature("Expertise", 6, "Double proficiency bonus for two more skills", "Rogue")],
            7: [ClassFeature("Evasion", 7, "Take no damage on successful Dex saves", "Rogue")],
            8: [ClassFeature("Ability Score Improvement", 8, "Increase ability scores or take feat", "Rogue")],
            9: [ClassFeature("Roguish Archetype Feature", 9, "Gain archetype feature", "Rogue")],
            10: [ClassFeature("Ability Score Improvement", 10, "Increase ability scores or take feat", "Rogue")],
            11: [ClassFeature("Reliable Talent", 11, "Treat d20 rolls of 9 or lower as 10", "Rogue")],
            12: [ClassFeature("Ability Score Improvement", 12, "Increase ability scores or take feat", "Rogue")],
            13: [ClassFeature("Roguish Archetype Feature", 13, "Gain archetype feature", "Rogue")],
            14: [ClassFeature("Blindsense", 14, "Detect creatures within 10 feet", "Rogue")],
            15: [ClassFeature("Slippery Mind", 15, "Proficiency in Wisdom saving throws", "Rogue")],
            16: [ClassFeature("Ability Score Improvement", 16, "Increase ability scores or take feat", "Rogue")],
            17: [ClassFeature("Roguish Archetype Feature", 17, "Gain archetype feature", "Rogue")],
            18: [ClassFeature("Elusive", 18, "No attack rolls have advantage against you", "Rogue")],
            19: [ClassFeature("Ability Score Improvement", 19, "Increase ability scores or take feat", "Rogue")],
            20: [ClassFeature("Stroke of Luck", 20, "Turn miss into hit or failure into success", "Rogue")]
        },

        "Cleric": {
            1: [
                ClassFeature("Spellcasting", 1, "Cast cleric spells. Spell save DC = 8 + prof + Wis mod. Spell attack = prof + Wis mod. Prepare spells = Wis mod + cleric level (min 1)", "Cleric"),
                ClassFeature("Divine Domain", 1, "Choose your divine domain", "Cleric",
                               choices=["Knowledge Domain", "Life Domain", "Light Domain", "Nature Domain", "Tempest Domain", "Trickery Domain",
                                       "War Domain", "Death Domain", "Forge Domain", "Grave Domain", "Order Domain", "Peace Domain", "Twilight Domain"],
                               choice_type="subclass")
            ],
            2: [
                ClassFeature("Channel Divinity", 2, "Use divine power for domain effects", "Cleric"),
                ClassFeature("Divine Domain Feature", 2, "Gain domain feature", "Cleric")
            ],
            3: [ClassFeature("Destroy Undead (CR 1/2)", 3, "Channel Divinity to destroy undead", "Cleric")],
            4: [ClassFeature("Ability Score Improvement", 4, "Increase ability scores or take feat", "Cleric")],
            5: [ClassFeature("Destroy Undead (CR 1)", 5, "Destroy more powerful undead", "Cleric")],
            6: [
                ClassFeature("Channel Divinity (2/rest)", 6, "Use Channel Divinity twice per rest", "Cleric"),
                ClassFeature("Divine Domain Feature", 6, "Gain domain feature", "Cleric")
            ],
            7: [ClassFeature("Divine Domain Feature", 7, "Gain domain feature", "Cleric")],
            8: [
                ClassFeature("Ability Score Improvement", 8, "Increase ability scores or take feat", "Cleric"),
                ClassFeature("Destroy Undead (CR 2)", 8, "Destroy more powerful undead", "Cleric"),
                ClassFeature("Divine Domain Feature", 8, "Gain domain feature", "Cleric")
            ],
            9: [ClassFeature("Divine Domain Feature", 9, "Gain domain feature", "Cleric")],
            10: [ClassFeature("Divine Intervention", 10, "Call upon your deity for aid", "Cleric")],
            11: [ClassFeature("Destroy Undead (CR 3)", 11, "Destroy more powerful undead", "Cleric")],
            12: [ClassFeature("Ability Score Improvement", 12, "Increase ability scores or take feat", "Cleric")],
            14: [ClassFeature("Destroy Undead (CR 4)", 14, "Destroy more powerful undead", "Cleric")],
            16: [ClassFeature("Ability Score Improvement", 16, "Increase ability scores or take feat", "Cleric")],
            17: [
                ClassFeature("Destroy Undead (CR 5)", 17, "Destroy more powerful undead", "Cleric"),
                ClassFeature("Divine Domain Feature", 17, "Gain domain feature", "Cleric")
            ],
            18: [ClassFeature("Channel Divinity (3/rest)", 18, "Use Channel Divinity three times per rest", "Cleric")],
            19: [ClassFeature("Ability Score Improvement", 19, "Increase ability scores or take feat", "Cleric")],
            20: [ClassFeature("Divine Intervention Improvement", 20, "Divine Intervention automatically succeeds", "Cleric")]
        },

        "Barbarian": {
            1: [
                ClassFeature("Rage", 1, "Enter battle rage for +2 damage, resistance to physical damage (2/long rest)", "Barbarian"),
                ClassFeature("Unarmored Defense", 1, "AC = 10 + Dex modifier + Con modifier", "Barbarian")
            ],
            2: [
                ClassFeature("Reckless Attack", 2, "Attack with advantage but grant advantage to attackers", "Barbarian"),
                ClassFeature("Danger Sense", 2, "Advantage on Dex saves against effects you can see", "Barbarian")
            ],
            3: [ClassFeature("Primal Path", 3, "Choose your primal path", "Barbarian",
                               choices=["Path of the Berserker", "Path of the Totem Warrior", "Path of the Ancestral Guardian", "Path of the Storm Herald",
                                       "Path of the Zealot", "Path of the Beast", "Path of Wild Magic"],
                               choice_type="subclass")],
            4: [ClassFeature("Ability Score Improvement", 4, "Increase ability scores or take feat", "Barbarian")],
            5: [
                ClassFeature("Extra Attack", 5, "Attack twice when taking Attack action", "Barbarian"),
                ClassFeature("Fast Movement", 5, "Speed increases by 10 feet", "Barbarian")
            ],
            6: [ClassFeature("Path Feature", 6, "Gain primal path feature", "Barbarian")],
            7: [ClassFeature("Feral Instinct", 7, "Advantage on initiative rolls", "Barbarian")],
            8: [ClassFeature("Ability Score Improvement", 8, "Increase ability scores or take feat", "Barbarian")],
            9: [ClassFeature("Brutal Critical (1 die)", 9, "Roll one additional weapon damage die on critical hits", "Barbarian")],
            10: [ClassFeature("Path Feature", 10, "Gain primal path feature", "Barbarian")],
            11: [ClassFeature("Relentless Rage", 11, "Keep raging when you would be knocked unconscious", "Barbarian")],
            12: [ClassFeature("Ability Score Improvement", 12, "Increase ability scores or take feat", "Barbarian")],
            13: [ClassFeature("Brutal Critical (2 dice)", 13, "Roll two additional weapon damage dice on critical hits", "Barbarian")],
            14: [ClassFeature("Path Feature", 14, "Gain primal path feature", "Barbarian")],
            15: [ClassFeature("Persistent Rage", 15, "Rage only ends if you fall unconscious or choose to end it", "Barbarian")],
            16: [ClassFeature("Ability Score Improvement", 16, "Increase ability scores or take feat", "Barbarian")],
            17: [ClassFeature("Brutal Critical (3 dice)", 17, "Roll three additional weapon damage dice on critical hits", "Barbarian")],
            18: [ClassFeature("Indomitable Might", 18, "Treat Strength checks less than your Strength score as your Strength score", "Barbarian")],
            19: [ClassFeature("Ability Score Improvement", 19, "Increase ability scores or take feat", "Barbarian")],
            20: [ClassFeature("Primal Champion", 20, "Strength and Constitution scores increase by 4", "Barbarian")]
        },

        "Bard": {
            1: [
                ClassFeature("Spellcasting", 1, "Cast bard spells. Spell save DC = 8 + prof + Cha mod. Spell attack = prof + Cha mod. Know spells = 4 + bard level", "Bard"),
                ClassFeature("Bardic Inspiration", 1, "Inspire allies with bonus action (d6, Cha mod per long rest)", "Bard")
            ],
            2: [
                ClassFeature("Jack of All Trades", 2, "Add half proficiency bonus to non-proficient checks", "Bard"),
                ClassFeature("Song of Rest", 2, "Help party recover hit points during short rest", "Bard")
            ],
            3: [
                ClassFeature("Bard College", 3, "Choose your bard college", "Bard",
                               choices=["College of Lore", "College of Valor", "College of Glamour", "College of Swords", "College of Whispers",
                                       "College of Creation", "College of Eloquence"],
                               choice_type="subclass"),
                ClassFeature("Expertise", 3, "Double proficiency bonus for chosen skills", "Bard")
            ],
            4: [ClassFeature("Ability Score Improvement", 4, "Increase ability scores or take feat", "Bard")],
            5: [
                ClassFeature("Bardic Inspiration (d8)", 5, "Bardic Inspiration die becomes d8", "Bard"),
                ClassFeature("Font of Inspiration", 5, "Regain Bardic Inspiration on short rest", "Bard")
            ],
            6: [
                ClassFeature("Countercharm", 6, "Grant advantage against charm and fear effects", "Bard"),
                ClassFeature("Bard College Feature", 6, "Gain college feature", "Bard")
            ],
            8: [ClassFeature("Ability Score Improvement", 8, "Increase ability scores or take feat", "Bard")],
            10: [
                ClassFeature("Bardic Inspiration (d10)", 10, "Bardic Inspiration die becomes d10", "Bard"),
                ClassFeature("Expertise", 10, "Double proficiency bonus for two more skills", "Bard"),
                ClassFeature("Magical Secrets", 10, "Learn spells from any class", "Bard")
            ],
            12: [ClassFeature("Ability Score Improvement", 12, "Increase ability scores or take feat", "Bard")],
            14: [
                ClassFeature("Magical Secrets", 14, "Learn additional spells from any class", "Bard"),
                ClassFeature("Bard College Feature", 14, "Gain college feature", "Bard")
            ],
            15: [ClassFeature("Bardic Inspiration (d12)", 15, "Bardic Inspiration die becomes d12", "Bard")],
            16: [ClassFeature("Ability Score Improvement", 16, "Increase ability scores or take feat", "Bard")],
            18: [ClassFeature("Magical Secrets", 18, "Learn additional spells from any class", "Bard")],
            19: [ClassFeature("Ability Score Improvement", 19, "Increase ability scores or take feat", "Bard")],
            20: [ClassFeature("Superior Inspiration", 20, "Regain Bardic Inspiration when you roll initiative", "Bard")]
        },

        "Druid": {
            1: [
                ClassFeature("Druidcraft", 1, "Know the druidcraft cantrip", "Druid"),
                ClassFeature("Spellcasting", 1, "Cast druid spells. Spell save DC = 8 + prof + Wis mod. Spell attack = prof + Wis mod. Prepare spells = Wis mod + druid level (min 1)", "Druid")
            ],
            2: [
                ClassFeature("Wild Shape", 2, "Transform into beasts", "Druid"),
                ClassFeature("Druid Circle", 2, "Choose your druid circle", "Druid",
                               choices=["Circle of the Land", "Circle of the Moon", "Circle of Dreams", "Circle of the Shepherd",
                                       "Circle of Spores", "Circle of Stars", "Circle of Wildfire"],
                               choice_type="subclass")
            ],
            4: [
                ClassFeature("Wild Shape Improvement", 4, "Transform into beasts with swimming speed", "Druid"),
                ClassFeature("Ability Score Improvement", 4, "Increase ability scores or take feat", "Druid")
            ],
            6: [ClassFeature("Druid Circle Feature", 6, "Gain circle feature", "Druid")],
            8: [
                ClassFeature("Wild Shape Improvement", 8, "Transform into beasts with flying speed", "Druid"),
                ClassFeature("Ability Score Improvement", 8, "Increase ability scores or take feat", "Druid")
            ],
            10: [ClassFeature("Druid Circle Feature", 10, "Gain circle feature", "Druid")],
            12: [ClassFeature("Ability Score Improvement", 12, "Increase ability scores or take feat", "Druid")],
            14: [ClassFeature("Druid Circle Feature", 14, "Gain circle feature", "Druid")],
            16: [ClassFeature("Ability Score Improvement", 16, "Increase ability scores or take feat", "Druid")],
            18: [
                ClassFeature("Timeless Body", 18, "Age at one-tenth the normal rate", "Druid"),
                ClassFeature("Beast Spells", 18, "Cast spells while in Wild Shape", "Druid")
            ],
            19: [ClassFeature("Ability Score Improvement", 19, "Increase ability scores or take feat", "Druid")],
            20: [ClassFeature("Archdruid", 20, "Use Wild Shape unlimited times and ignore spell components", "Druid")]
        },

        "Monk": {
            1: [
                ClassFeature("Unarmored Defense", 1, "AC = 10 + Dex modifier + Wis modifier", "Monk"),
                ClassFeature("Martial Arts", 1, "Use Dex for unarmed strikes, bonus action unarmed strike", "Monk")
            ],
            2: [
                ClassFeature("Ki", 2, "Harness mystical energy for special abilities", "Monk"),
                ClassFeature("Unarmored Movement", 2, "Speed increases by 10 feet while unarmored", "Monk")
            ],
            3: [
                ClassFeature("Monastic Tradition", 3, "Choose your monastic tradition", "Monk",
                               choices=["Way of the Open Hand", "Way of Shadow", "Way of the Four Elements", "Way of the Drunken Master",
                                       "Way of the Kensei", "Way of the Sun Soul", "Way of Mercy", "Way of the Astral Self"],
                               choice_type="subclass"),
                ClassFeature("Deflect Missiles", 3, "Reduce ranged weapon damage and throw projectiles back", "Monk")
            ],
            4: [
                ClassFeature("Ability Score Improvement", 4, "Increase ability scores or take feat", "Monk"),
                ClassFeature("Slow Fall", 4, "Reduce falling damage", "Monk")
            ],
            5: [
                ClassFeature("Extra Attack", 5, "Attack twice when taking Attack action", "Monk"),
                ClassFeature("Stunning Strike", 5, "Spend ki to stun targets", "Monk")
            ],
            6: [
                ClassFeature("Ki-Empowered Strikes", 6, "Unarmed strikes count as magical", "Monk"),
                ClassFeature("Monastic Tradition Feature", 6, "Gain tradition feature", "Monk")
            ],
            7: [
                ClassFeature("Evasion", 7, "Take no damage on successful Dex saves", "Monk"),
                ClassFeature("Stillness of Mind", 7, "End charm or fear effects on yourself", "Monk")
            ],
            8: [ClassFeature("Ability Score Improvement", 8, "Increase ability scores or take feat", "Monk")],
            9: [ClassFeature("Unarmored Movement Improvement", 9, "Move along vertical surfaces and across liquids", "Monk")],
            10: [ClassFeature("Purity of Body", 10, "Immunity to disease and poison", "Monk")],
            11: [ClassFeature("Monastic Tradition Feature", 11, "Gain tradition feature", "Monk")],
            12: [ClassFeature("Ability Score Improvement", 12, "Increase ability scores or take feat", "Monk")],
            13: [ClassFeature("Tongue of the Sun and Moon", 13, "Understand all spoken languages", "Monk")],
            14: [ClassFeature("Diamond Soul", 14, "Proficiency in all saving throws", "Monk")],
            15: [ClassFeature("Timeless Body", 15, "No longer age and can't be aged magically", "Monk")],
            16: [ClassFeature("Ability Score Improvement", 16, "Increase ability scores or take feat", "Monk")],
            17: [ClassFeature("Monastic Tradition Feature", 17, "Gain tradition feature", "Monk")],
            18: [ClassFeature("Empty Body", 18, "Become invisible and resistant to damage", "Monk")],
            19: [ClassFeature("Ability Score Improvement", 19, "Increase ability scores or take feat", "Monk")],
            20: [ClassFeature("Perfect Self", 20, "Regain ki when you have no ki remaining", "Monk")]
        },

        "Paladin": {
            1: [
                ClassFeature("Divine Sense", 1, "Detect celestials, fiends, and undead", "Paladin"),
                ClassFeature("Lay on Hands", 1, "Heal wounds and cure diseases. Pool of 5 × paladin level hit points", "Paladin")
            ],
            2: [
                ClassFeature("Fighting Style", 2, "Choose a fighting style", "Paladin",
                               choices=["Defense (+1 AC in armor)", "Dueling (+2 damage with one-handed weapons)", "Great Weapon Fighting (reroll 1s and 2s on damage)",
                                       "Protection (use shield to impose disadvantage)", "Blessed Warrior (learn two cantrips)", "Interception (reduce damage to nearby allies)"],
                               choice_type="fighting_style"),
                ClassFeature("Spellcasting", 2, "Cast paladin spells. Spell save DC = 8 + prof + Cha mod. Spell attack = prof + Cha mod. Prepare spells = Cha mod + half paladin level (min 1)", "Paladin"),
                ClassFeature("Divine Smite", 2, "Expend spell slots for +2d8 radiant damage (+1d8 per spell level, +1d8 vs undead/fiends)", "Paladin")
            ],
            3: [
                ClassFeature("Divine Health", 3, "Immunity to disease", "Paladin"),
                ClassFeature("Sacred Oath", 3, "Choose your sacred oath", "Paladin",
                               choices=["Oath of Devotion", "Oath of the Ancients", "Oath of Vengeance", "Oath of Conquest",
                                       "Oath of Redemption", "Oath of Glory", "Oath of the Watchers", "Oath of the Crown"],
                               choice_type="subclass")
            ],
            4: [ClassFeature("Ability Score Improvement", 4, "Increase ability scores or take feat", "Paladin")],
            5: [ClassFeature("Extra Attack", 5, "Attack twice when taking Attack action", "Paladin")],
            6: [ClassFeature("Aura of Protection", 6, "Add Cha modifier to saving throws of nearby allies", "Paladin")],
            7: [ClassFeature("Sacred Oath Feature", 7, "Gain oath feature", "Paladin")],
            8: [ClassFeature("Ability Score Improvement", 8, "Increase ability scores or take feat", "Paladin")],
            9: [ClassFeature("Sacred Oath Feature", 9, "Gain oath feature", "Paladin")],
            10: [ClassFeature("Aura of Courage", 10, "You and nearby allies can't be frightened", "Paladin")],
            11: [ClassFeature("Improved Divine Smite", 11, "All melee weapon attacks deal extra radiant damage", "Paladin")],
            12: [ClassFeature("Ability Score Improvement", 12, "Increase ability scores or take feat", "Paladin")],
            13: [ClassFeature("Sacred Oath Feature", 13, "Gain oath feature", "Paladin")],
            14: [ClassFeature("Cleansing Touch", 14, "End spells on yourself or others", "Paladin")],
            15: [ClassFeature("Sacred Oath Feature", 15, "Gain oath feature", "Paladin")],
            16: [ClassFeature("Ability Score Improvement", 16, "Increase ability scores or take feat", "Paladin")],
            17: [ClassFeature("Sacred Oath Feature", 17, "Gain oath feature", "Paladin")],
            18: [ClassFeature("Aura Improvements", 18, "Aura of Protection and Courage range increases", "Paladin")],
            19: [ClassFeature("Ability Score Improvement", 19, "Increase ability scores or take feat", "Paladin")],
            20: [ClassFeature("Sacred Oath Feature", 20, "Gain oath capstone feature", "Paladin")]
        },

        "Ranger": {
            1: [
                ClassFeature("Favored Enemy", 1, "Choose favored enemy types", "Ranger",
                               choices=["Beasts", "Fey", "Humanoids", "Monstrosities", "Undead", "Aberrations", "Celestials", "Constructs",
                                       "Dragons", "Elementals", "Fiends", "Giants", "Oozes", "Plants", "Two races of humanoid"],
                               choice_type="favored_enemy"),
                ClassFeature("Natural Explorer", 1, "Choose favored terrain", "Ranger",
                               choices=["Arctic", "Coast", "Desert", "Forest", "Grassland", "Mountain", "Swamp", "Underdark"],
                               choice_type="favored_terrain")
            ],
            2: [
                ClassFeature("Fighting Style", 2, "Choose a fighting style", "Ranger",
                               choices=["Archery (+2 to ranged attacks)", "Defense (+1 AC in armor)", "Dueling (+2 damage with one-handed weapons)",
                                       "Two-Weapon Fighting (add ability modifier to off-hand damage)", "Blind Fighting (see in darkness within 10 feet)",
                                       "Druidcraft (learn the druidcraft cantrip)", "Thrown Weapon Fighting (+2 damage with thrown weapons)"],
                               choice_type="fighting_style"),
                ClassFeature("Spellcasting", 2, "Cast ranger spells. Spell save DC = 8 + prof + Wis mod. Spell attack = prof + Wis mod. Prepare spells = Wis mod + half ranger level (min 1)", "Ranger")
            ],
            3: [
                ClassFeature("Ranger Archetype", 3, "Choose your ranger archetype", "Ranger",
                               choices=["Hunter", "Beast Master", "Gloom Stalker", "Horizon Walker", "Monster Slayer", "Fey Wanderer", "Swarmkeeper"],
                               choice_type="subclass"),
                ClassFeature("Primeval Awareness", 3, "Detect certain creature types", "Ranger")
            ],
            4: [ClassFeature("Ability Score Improvement", 4, "Increase ability scores or take feat", "Ranger")],
            5: [ClassFeature("Extra Attack", 5, "Attack twice when taking Attack action", "Ranger")],
            6: [
                ClassFeature("Favored Enemy Improvement", 6, "Choose additional favored enemy", "Ranger"),
                ClassFeature("Natural Explorer Improvement", 6, "Choose additional favored terrain", "Ranger")
            ],
            7: [ClassFeature("Ranger Archetype Feature", 7, "Gain archetype feature", "Ranger")],
            8: [
                ClassFeature("Ability Score Improvement", 8, "Increase ability scores or take feat", "Ranger"),
                ClassFeature("Land's Stride", 8, "Move through difficult terrain without penalty", "Ranger")
            ],
            10: [
                ClassFeature("Natural Explorer Improvement", 10, "Choose additional favored terrain", "Ranger"),
                ClassFeature("Hide in Plain Sight", 10, "Camouflage yourself", "Ranger")
            ],
            11: [ClassFeature("Ranger Archetype Feature", 11, "Gain archetype feature", "Ranger")],
            12: [ClassFeature("Ability Score Improvement", 12, "Increase ability scores or take feat", "Ranger")],
            14: [
                ClassFeature("Favored Enemy Improvement", 14, "Choose additional favored enemy", "Ranger"),
                ClassFeature("Vanish", 14, "Hide as bonus action and can't be tracked", "Ranger")
            ],
            15: [ClassFeature("Ranger Archetype Feature", 15, "Gain archetype feature", "Ranger")],
            16: [ClassFeature("Ability Score Improvement", 16, "Increase ability scores or take feat", "Ranger")],
            18: [ClassFeature("Feral Senses", 18, "Detect creatures without relying on sight", "Ranger")],
            19: [ClassFeature("Ability Score Improvement", 19, "Increase ability scores or take feat", "Ranger")],
            20: [ClassFeature("Foe Slayer", 20, "Add Wis modifier to attack or damage rolls once per turn", "Ranger")]
        },

        "Sorcerer": {
            1: [
                ClassFeature("Spellcasting", 1, "Cast sorcerer spells. Spell save DC = 8 + prof + Cha mod. Spell attack = prof + Cha mod. Know spells = 2 + sorcerer level", "Sorcerer"),
                ClassFeature("Sorcerous Origin", 1, "Choose your sorcerous origin", "Sorcerer",
                               choices=["Draconic Bloodline", "Wild Magic", "Divine Soul", "Shadow Magic", "Storm Sorcery",
                                       "Aberrant Mind", "Clockwork Soul"],
                               choice_type="subclass")
            ],
            2: [ClassFeature("Font of Magic", 2, "Convert spell slots to sorcery points and vice versa", "Sorcerer")],
            3: [ClassFeature("Metamagic", 3, "Choose 2 Metamagic options to modify spells with sorcery points", "Sorcerer",
                               choices=["Careful Spell", "Distant Spell", "Empowered Spell", "Extended Spell", "Heightened Spell",
                                       "Quickened Spell", "Subtle Spell", "Twinned Spell", "Seeking Spell", "Transmuted Spell"],
                               choice_type="metamagic")],
            4: [ClassFeature("Ability Score Improvement", 4, "Increase ability scores or take feat", "Sorcerer")],
            6: [ClassFeature("Sorcerous Origin Feature", 6, "Gain origin feature", "Sorcerer")],
            8: [ClassFeature("Ability Score Improvement", 8, "Increase ability scores or take feat", "Sorcerer")],
            10: [ClassFeature("Metamagic", 10, "Learn additional Metamagic options", "Sorcerer")],
            12: [ClassFeature("Ability Score Improvement", 12, "Increase ability scores or take feat", "Sorcerer")],
            14: [ClassFeature("Sorcerous Origin Feature", 14, "Gain origin feature", "Sorcerer")],
            16: [ClassFeature("Ability Score Improvement", 16, "Increase ability scores or take feat", "Sorcerer")],
            17: [ClassFeature("Metamagic", 17, "Learn additional Metamagic options", "Sorcerer")],
            18: [ClassFeature("Sorcerous Origin Feature", 18, "Gain origin feature", "Sorcerer")],
            19: [ClassFeature("Ability Score Improvement", 19, "Increase ability scores or take feat", "Sorcerer")],
            20: [ClassFeature("Sorcerous Restoration", 20, "Regain sorcery points on short rest", "Sorcerer")]
        },

        "Warlock": {
            1: [
                ClassFeature("Otherworldly Patron", 1, "Choose your otherworldly patron", "Warlock",
                               choices=["The Archfey", "The Fiend", "The Great Old One", "The Celestial", "The Hexblade",
                                       "The Fathomless", "The Genie", "The Undead"],
                               choice_type="subclass"),
                ClassFeature("Pact Magic", 1, "Cast warlock spells. Spell save DC = 8 + prof + Cha mod. Spell attack = prof + Cha mod. Few but powerful pact slots", "Warlock")
            ],
            2: [ClassFeature("Eldritch Invocations", 2, "Learn eldritch invocations", "Warlock")],
            3: [ClassFeature("Pact Boon", 3, "Choose your pact boon", "Warlock",
                               choices=["Pact of the Chain (familiar)", "Pact of the Blade (weapon)", "Pact of the Tome (book of shadows)", "Pact of the Talisman (protective charm)"],
                               choice_type="pact_boon")],
            4: [ClassFeature("Ability Score Improvement", 4, "Increase ability scores or take feat", "Warlock")],
            5: [ClassFeature("Eldritch Invocations", 5, "Learn additional eldritch invocations", "Warlock")],
            6: [ClassFeature("Otherworldly Patron Feature", 6, "Gain patron feature", "Warlock")],
            7: [ClassFeature("Eldritch Invocations", 7, "Learn additional eldritch invocations", "Warlock")],
            8: [ClassFeature("Ability Score Improvement", 8, "Increase ability scores or take feat", "Warlock")],
            9: [ClassFeature("Eldritch Invocations", 9, "Learn additional eldritch invocations", "Warlock")],
            10: [ClassFeature("Otherworldly Patron Feature", 10, "Gain patron feature", "Warlock")],
            11: [ClassFeature("Mystic Arcanum (6th level)", 11, "Learn a 6th-level spell", "Warlock")],
            12: [
                ClassFeature("Ability Score Improvement", 12, "Increase ability scores or take feat", "Warlock"),
                ClassFeature("Eldritch Invocations", 12, "Learn additional eldritch invocations", "Warlock")
            ],
            13: [ClassFeature("Mystic Arcanum (7th level)", 13, "Learn a 7th-level spell", "Warlock")],
            14: [ClassFeature("Otherworldly Patron Feature", 14, "Gain patron feature", "Warlock")],
            15: [
                ClassFeature("Mystic Arcanum (8th level)", 15, "Learn an 8th-level spell", "Warlock"),
                ClassFeature("Eldritch Invocations", 15, "Learn additional eldritch invocations", "Warlock")
            ],
            16: [ClassFeature("Ability Score Improvement", 16, "Increase ability scores or take feat", "Warlock")],
            17: [ClassFeature("Mystic Arcanum (9th level)", 17, "Learn a 9th-level spell", "Warlock")],
            18: [ClassFeature("Eldritch Invocations", 18, "Learn additional eldritch invocations", "Warlock")],
            19: [ClassFeature("Ability Score Improvement", 19, "Increase ability scores or take feat", "Warlock")],
            20: [ClassFeature("Eldritch Master", 20, "Regain all expended spell slots on short rest", "Warlock")]
        },

        "Artificer": {
            1: [
                ClassFeature("Magical Tinkering", 1, "Imbue tiny objects with minor magical properties", "Artificer"),
                ClassFeature("Spellcasting", 1, "Cast artificer spells", "Artificer")
            ],
            2: [
                ClassFeature("Tool Expertise", 2, "Double proficiency bonus for tool checks", "Artificer"),
                ClassFeature("Infuse Item", 2, "Imbue mundane items with magical infusions", "Artificer")
            ],
            3: [ClassFeature("Artificer Specialist", 3, "Choose your artificer specialist", "Artificer",
                               choices=["Alchemist", "Armorer", "Battle Smith", "Artillerist"],
                               choice_type="subclass")],
            4: [ClassFeature("Ability Score Improvement", 4, "Increase ability scores or take feat", "Artificer")],
            5: [ClassFeature("Artificer Specialist Feature", 5, "Gain specialist feature", "Artificer")],
            6: [
                ClassFeature("Tool Expertise", 6, "Gain expertise with more tools", "Artificer"),
                ClassFeature("Infuse Item Improvement", 6, "Learn additional infusions", "Artificer")
            ],
            7: [ClassFeature("Flash of Genius", 7, "Add Int modifier to ability checks or saving throws", "Artificer")],
            8: [ClassFeature("Ability Score Improvement", 8, "Increase ability scores or take feat", "Artificer")],
            9: [ClassFeature("Artificer Specialist Feature", 9, "Gain specialist feature", "Artificer")],
            10: [
                ClassFeature("Magic Item Adept", 10, "Attune to more magic items and craft them faster", "Artificer"),
                ClassFeature("Infuse Item Improvement", 10, "Learn additional infusions", "Artificer")
            ],
            11: [ClassFeature("Spell-Storing Item", 11, "Store spells in items for others to use", "Artificer")],
            12: [ClassFeature("Ability Score Improvement", 12, "Increase ability scores or take feat", "Artificer")],
            14: [
                ClassFeature("Magic Item Savant", 14, "Attune to any magic item regardless of restrictions", "Artificer"),
                ClassFeature("Infuse Item Improvement", 14, "Learn additional infusions", "Artificer")
            ],
            15: [ClassFeature("Artificer Specialist Feature", 15, "Gain specialist feature", "Artificer")],
            16: [ClassFeature("Ability Score Improvement", 16, "Increase ability scores or take feat", "Artificer")],
            18: [
                ClassFeature("Magic Item Master", 18, "Attune to up to six magic items", "Artificer"),
                ClassFeature("Infuse Item Improvement", 18, "Learn additional infusions", "Artificer")
            ],
            19: [ClassFeature("Ability Score Improvement", 19, "Increase ability scores or take feat", "Artificer")],
            20: [ClassFeature("Soul of Artifice", 20, "Gain bonuses based on attuned magic items", "Artificer")]
        }
    }

    ASI_LEVELS = {
        "Fighter": [4, 6, 8, 12, 14, 16, 19],
        "Wizard": [4, 8, 12, 16, 19],
        "Rogue": [4, 8, 10, 12, 16, 19],
        "Cleric": [4, 8, 12, 16, 19],
        "Bard": [4, 8, 12, 16, 19],
        "Barbarian": [4, 8, 12, 16, 19],
        "Druid": [4, 8, 12, 16, 19],
        "Monk": [4, 8, 12, 16, 19],
        "Paladin": [4, 8, 12, 16, 19],
        "Ranger": [4, 8, 12, 16, 19],
        "Sorcerer": [4, 8, 12, 16, 19],
        "Warlock": [4, 8, 12, 16, 19],
        "Artificer": [4, 8, 12, 16, 19]
    }

    def get_features_for_level(self, class_name: str, level: int) -> List[ClassFeature]:
        """Get all features gained at a specific level"""
        class_features = self.CLASS_FEATURES.get(class_name, {})
        return class_features.get(level, [])

    def get_all_features_up_to_level(self, class_name: str, level: int) -> List[ClassFeature]:
        """Get all features from level 1 up to the specified level"""
        all_features = []
        class_features = self.CLASS_FEATURES.get(class_name, {})

        for lvl in range(1, level + 1):
            features = class_features.get(lvl, [])
            all_features.extend(features)

        return all_features

    def has_asi_at_level(self, class_name: str, level: int) -> bool:
        """Check if class gets ASI/feat at this level"""
        asi_levels = self.ASI_LEVELS.get(class_name, [])
        return level in asi_levels

class MilestoneManager:
    """Manages story-based milestone progression"""

    def __init__(self):
        self.milestones = {}

    def create_campaign_milestones(self, campaign_id: int, campaign_data: Dict[str, Any]) -> List[Milestone]:
        """Create milestones based on campaign structure"""
        milestones = []

        # Extract acts from campaign data
        acts = campaign_data.get("acts", [])

        for i, act in enumerate(acts, 1):
            # Major milestone at end of each act
            milestone = Milestone(
                name=f"Complete {act.get('title', f'Act {i}')}",
                description=f"Finish the main storyline of {act.get('title', f'Act {i}')}",
                target_level=min(i * 4, 20),  # Level 4, 8, 12, 16, 20
                act_number=i
            )
            milestones.append(milestone)

            # Minor milestones within acts
            if i < len(acts):  # Don't add minor milestones for final act
                minor_milestone = Milestone(
                    name=f"Major Discovery in {act.get('title', f'Act {i}')}",
                    description=f"Make significant progress in {act.get('title', f'Act {i}')}",
                    target_level=min(i * 4 - 2, 18),  # Level 2, 6, 10, 14, 18
                    act_number=i
                )
                milestones.append(minor_milestone)

        self.milestones[campaign_id] = milestones
        return milestones

    def get_next_milestone(self, campaign_id: int, current_level: int) -> Optional[Milestone]:
        """Get the next milestone for a campaign"""
        campaign_milestones = self.milestones.get(campaign_id, [])

        for milestone in campaign_milestones:
            if not milestone.completed and milestone.target_level > current_level:
                return milestone

        return None

    def complete_milestone(self, campaign_id: int, milestone_name: str) -> bool:
        """Mark a milestone as completed"""
        campaign_milestones = self.milestones.get(campaign_id, [])

        for milestone in campaign_milestones:
            if milestone.name == milestone_name:
                milestone.completed = True
                return True

        return False

class LevelProgressionManager:
    """Main class for managing character level progression"""

    def __init__(self):
        self.experience_table = ExperienceTable()
        self.class_progression = ClassProgression()
        self.milestone_manager = MilestoneManager()

    def calculate_level_up(self, character_data: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate what happens when a character levels up"""
        current_level = character_data.get("level", 1)
        new_level = current_level + 1
        class_name = character_data.get("class_name")

        if new_level > 20:
            return {"error": "Maximum level reached"}

        # Get hit die for class
        hit_die_map = {
            "Barbarian": 12,
            "Fighter": 10, "Paladin": 10, "Ranger": 10,
            "Bard": 8, "Cleric": 8, "Druid": 8, "Monk": 8, "Rogue": 8, "Warlock": 8, "Artificer": 8,
            "Sorcerer": 6, "Wizard": 6
        }
        hit_die = hit_die_map.get(class_name, 8)

        # Calculate HP gain (average + Con modifier)
        con_modifier = character_data.get("constitution_modifier", 0)
        avg_hp_gain = (hit_die // 2) + 1 + con_modifier
        max_hp_gain = hit_die + con_modifier

        # Get new features
        new_features = self.class_progression.get_features_for_level(class_name, new_level)

        # Check for ASI/feat
        gets_asi = self.class_progression.has_asi_at_level(class_name, new_level)

        # Get new proficiency bonus
        new_prof_bonus = self.experience_table.PROFICIENCY_BONUS[new_level]

        return {
            "new_level": new_level,
            "hit_die": hit_die,
            "hp_gain_average": max(1, avg_hp_gain),
            "hp_gain_maximum": max(1, max_hp_gain),
            "new_features": [
                {
                    "name": feature.name,
                    "description": feature.description,
                    "choices": feature.choices,
                    "choice_type": feature.choice_type
                } for feature in new_features
            ],
            "ability_score_improvement": gets_asi,
            "proficiency_bonus": new_prof_bonus,
            "spell_slot_changes": self.calculate_spell_slot_changes(class_name, current_level, new_level)
        }

    def calculate_spell_slot_changes(self, class_name: str, old_level: int, new_level: int) -> Dict[str, Any]:
        """Calculate spell slot changes on level up"""
        from .spell_system import SpellSlotManager

        slot_manager = SpellSlotManager()

        # Determine caster type
        caster_types = {
            "Bard": "full", "Cleric": "full", "Druid": "full", "Sorcerer": "full", "Wizard": "full",
            "Paladin": "half", "Ranger": "half",
            "Eldritch Knight": "third", "Arcane Trickster": "third",
            "Warlock": "warlock"
        }

        caster_type = caster_types.get(class_name)
        if not caster_type:
            return {"changes": False}

        old_slots = slot_manager.get_spell_slots(caster_type, old_level)
        new_slots = slot_manager.get_spell_slots(caster_type, new_level)

        changes = []
        for i, (old, new) in enumerate(zip(old_slots, new_slots)):
            if new > old:
                level = i + 1
                change = new - old
                changes.append(f"Gain {change} level {level} spell slot{'s' if change > 1 else ''}")

        return {
            "changes": len(changes) > 0,
            "spell_slot_changes": changes,
            "new_slots": new_slots
        }

    def award_experience(self, character_data: Dict[str, Any], xp_amount: int) -> Dict[str, Any]:
        """Award experience points and check for level up"""
        current_xp = character_data.get("experience_points", 0)
        current_level = character_data.get("level", 1)
        new_xp = current_xp + xp_amount
        new_level = self.experience_table.get_level_from_xp(new_xp)

        result = {
            "xp_gained": xp_amount,
            "new_total_xp": new_xp,
            "level_up": new_level > current_level
        }

        if result["level_up"]:
            result["new_level"] = new_level
            result["level_up_details"] = self.calculate_level_up({
                **character_data,
                "level": new_level - 1
            })

        return result

    def check_milestone_progression(self, campaign_id: int, current_level: int) -> Dict[str, Any]:
        """Check milestone progression for campaign"""
        next_milestone = self.milestone_manager.get_next_milestone(campaign_id, current_level)

        if next_milestone:
            return {
                "has_next_milestone": True,
                "milestone": {
                    "name": next_milestone.name,
                    "description": next_milestone.description,
                    "target_level": next_milestone.target_level,
                    "act_number": next_milestone.act_number
                }
            }

        return {"has_next_milestone": False}

# Global progression manager instance
progression_manager = LevelProgressionManager()