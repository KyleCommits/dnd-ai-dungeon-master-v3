# load_spells.py
"""
Utility script to load all D&D 5e spells from the API into the local database
"""

import asyncio
import sys
import os

# add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from src.enhanced_spell_system import enhanced_spell_manager

async def main():
    """Load all spells from the D&D 5e API"""
    print("Initializing enhanced spell system...")
    print("This will fetch all 319+ spells from the D&D 5e API")
    print("This process may take 2-5 minutes depending on network speed")
    print()

    # see if user wants to continue
    response = input("Continue with spell loading? (y/n): ").lower()
    if response != 'y':
        print("Spell loading cancelled.")
        return

    try:
        # init spell manager (loads spells if db empty)
        enhanced_spell_manager.initialize()

        # get stats
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
        print("Spells by school:")
        for school, count in stats['spells_by_school'].items():
            print(f"  {school.title()}: {count} spells")

        # test some spells
        print()
        print("Testing spell lookup:")
        test_spells = ["Fireball", "Magic Missile", "Cure Wounds", "Eldritch Blast"]
        for spell_name in test_spells:
            spell = enhanced_spell_manager.get_spell(spell_name)
            if spell:
                print(f"  ✓ {spell.name} (Level {spell.level} {spell.school.title()})")
            else:
                print(f"  ✗ {spell_name} not found")

    except Exception as e:
        print(f"ERROR: Failed to load spells: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())