# test_spells.py
"""
Test script for the enhanced spell system
"""

import sys
import os

# add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

def test_basic_functionality():
    """Test basic spell system functionality"""
    print("Testing Enhanced Spell System")
    print("=" * 40)

    try:
        from src.enhanced_spell_system import enhanced_spell_manager

        # init (uses existing db if available)
        enhanced_spell_manager.initialize()

        # test spell stats
        stats = enhanced_spell_manager.get_spell_statistics()
        print(f"Total spells in system: {stats['total_spells']}")

        if stats['total_spells'] == 0:
            print("No spells found. Run 'python load_spells.py' first to load spell data.")
            return

        # test spell lookup
        print("\nTesting spell lookup:")
        test_spells = ["Fireball", "Magic Missile", "Cure Wounds", "Eldritch Blast", "Counterspell"]

        for spell_name in test_spells:
            spell = enhanced_spell_manager.get_spell(spell_name)
            if spell:
                print(f"✓ {spell.name}")
                print(f"  Level: {spell.level}")
                print(f"  School: {spell.school}")
                print(f"  Casting Time: {spell.casting_time}")
                print(f"  Range: {spell.range}")
                print(f"  Components: {', '.join(spell.components)}")
                if spell.damage:
                    print(f"  Damage: {spell.damage.damage_type}")
                if spell.ritual:
                    print("  [Ritual]")
                if spell.concentration:
                    print("  [Concentration]")
                print()
            else:
                print(f"✗ {spell_name} not found")

        # test search stuff
        print("Testing spell search:")

        # search by level
        cantrips = enhanced_spell_manager.search_spells(level=0)
        print(f"Cantrips found: {len(cantrips)}")

        # search by school
        evocation_spells = enhanced_spell_manager.search_spells(school="evocation")
        print(f"Evocation spells found: {len(evocation_spells)}")

        # search by class
        wizard_spells = enhanced_spell_manager.search_spells(class_name="Wizard")
        print(f"Wizard spells found: {len(wizard_spells)}")

        print("\n" + "=" * 40)
        print("Spell system test completed successfully!")

    except ImportError as e:
        print(f"Import error: {e}")
        print("Make sure all dependencies are installed.")
    except Exception as e:
        print(f"Error during testing: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_basic_functionality()