# load_spells.py
"""
Utility script to load all D&D 5e spells from the API into the local database.
This is the ONLY supported network path for spell data.
"""

import asyncio
import sys
import os

# add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.enhanced_spell_system import SpellDataLoader, enhanced_spell_manager


async def main():
    """Load all spells from the D&D 5e API into data/spells.db"""
    print("Loading spells from D&D 5e API into local SQLite...")
    print("This may take 2-5 minutes depending on network speed")
    print()

    response = input("Continue with spell loading? (y/n): ").lower()
    if response != 'y':
        print("Spell loading cancelled.")
        return

    try:
        loader = SpellDataLoader(allow_network=True)
        loader.load_all_spells()

        stats = enhanced_spell_manager.get_spell_statistics()
        print()
        print("SUCCESS: Spell system ready!")
        print(f"Total spells loaded: {stats['total_spells']}")
        print()
        print("Spells by level:")
        for level, count in stats['spells_by_level'].items():
            level_name = "Cantrips" if level == 0 else f"Level {level}"
            print(f"  {level_name}: {count} spells")

        print()
        print("Testing spell lookup:")
        test_spells = ["Fireball", "Magic Missile", "Cure Wounds", "Eldritch Blast"]
        for spell_name in test_spells:
            spell = enhanced_spell_manager.get_spell(spell_name)
            if spell:
                print(f"  [OK] {spell.name} (Level {spell.level} {spell.school})")
            else:
                print(f"  [MISSING] {spell_name} not found")

    except Exception as e:
        print(f"ERROR: Failed to load spells: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
