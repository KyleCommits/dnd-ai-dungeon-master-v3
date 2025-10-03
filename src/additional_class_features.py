# Additional D&D 5e class features for level progression
# This file contains the remaining classes to add to level_progression.py

ADDITIONAL_CLASS_FEATURES = {
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
            ClassFeature("Monastic Tradition", 3, "Choose your monastic tradition", "Monk"),
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
            ClassFeature("Lay on Hands", 1, "Heal wounds and cure diseases", "Paladin")
        ],
        2: [
            ClassFeature("Fighting Style", 2, "Choose a fighting style", "Paladin"),
            ClassFeature("Spellcasting", 2, "Cast paladin spells", "Paladin"),
            ClassFeature("Divine Smite", 2, "Expend spell slots for extra radiant damage", "Paladin")
        ],
        3: [
            ClassFeature("Divine Health", 3, "Immunity to disease", "Paladin"),
            ClassFeature("Sacred Oath", 3, "Choose your sacred oath", "Paladin")
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
            ClassFeature("Favored Enemy", 1, "Choose favored enemy types", "Ranger"),
            ClassFeature("Natural Explorer", 1, "Choose favored terrain", "Ranger")
        ],
        2: [
            ClassFeature("Fighting Style", 2, "Choose a fighting style", "Ranger"),
            ClassFeature("Spellcasting", 2, "Cast ranger spells", "Ranger")
        ],
        3: [
            ClassFeature("Ranger Archetype", 3, "Choose your ranger archetype", "Ranger"),
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
            ClassFeature("Spellcasting", 1, "Cast sorcerer spells", "Sorcerer"),
            ClassFeature("Sorcerous Origin", 1, "Choose your sorcerous origin", "Sorcerer")
        ],
        2: [ClassFeature("Font of Magic", 2, "Convert spell slots to sorcery points and vice versa", "Sorcerer")],
        3: [ClassFeature("Metamagic", 3, "Modify spells with sorcery points", "Sorcerer")],
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
            ClassFeature("Otherworldly Patron", 1, "Choose your otherworldly patron", "Warlock"),
            ClassFeature("Pact Magic", 1, "Cast warlock spells with pact slots", "Warlock")
        ],
        2: [ClassFeature("Eldritch Invocations", 2, "Learn eldritch invocations", "Warlock")],
        3: [ClassFeature("Pact Boon", 3, "Choose your pact boon", "Warlock")],
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
        3: [ClassFeature("Artificer Specialist", 3, "Choose your artificer specialist", "Artificer")],
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

# Add the missing ASI levels for the new classes
ADDITIONAL_ASI_LEVELS = {
    "Monk": [4, 8, 12, 16, 19],
    "Paladin": [4, 8, 12, 16, 19],
    "Ranger": [4, 8, 12, 16, 19],
    "Sorcerer": [4, 8, 12, 16, 19],
    "Warlock": [4, 8, 12, 16, 19],
    "Artificer": [4, 8, 12, 16, 19]
}