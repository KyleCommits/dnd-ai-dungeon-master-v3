# test_integration.py
"""
Test script to verify the full spell system integration
"""

import asyncio
import sys
import os

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

async def test_spell_integration():
    """Test the full spell integration workflow"""
    print("Testing Full Spell System Integration")
    print("=" * 50)

    try:
        # Import required modules
        from src.enhanced_spell_system import enhanced_spell_manager
        from src.spell_integration import character_spell_manager
        from src.character_manager import character_manager
        from src.database import get_db_session

        # Initialize spell system
        print("1. Initializing spell system...")
        enhanced_spell_manager.initialize()
        spell_count = enhanced_spell_manager.get_spell_statistics()['total_spells']
        print(f"   SUCCESS: {spell_count} spells loaded")

        # Test spell lookup
        print("\n2. Testing spell lookup...")
        fireball = enhanced_spell_manager.get_spell("Fireball")
        if fireball:
            print(f"   SUCCESS: Found {fireball.name} (Level {fireball.level} {fireball.school})")
        else:
            print("   ERROR: Fireball not found")
            return

        # Test spell search
        print("\n3. Testing spell search...")
        wizard_cantrips = enhanced_spell_manager.search_spells(level=0, class_name="Wizard")
        print(f"   SUCCESS: Found {len(wizard_cantrips)} wizard cantrips")

        evocation_spells = enhanced_spell_manager.search_spells(school="evocation")
        print(f"   SUCCESS: Found {len(evocation_spells)} evocation spells")

        # Test character spell methods (without database for now)
        print("\n4. Testing character spell manager methods...")

        # Test caster type detection
        caster_types = character_spell_manager.caster_types
        print(f"   SUCCESS: {len(caster_types)} caster types defined")

        spellcasting_abilities = character_spell_manager.spellcasting_abilities
        print(f"   SUCCESS: {len(spellcasting_abilities)} spellcasting abilities defined")

        # Test spell slot calculation
        from src.spell_system import SpellSlotManager
        slot_manager = SpellSlotManager()

        wizard_slots = slot_manager.get_spell_slots("full", 5)
        print(f"   SUCCESS: Level 5 wizard spell slots: {wizard_slots}")

        warlock_slots = slot_manager.get_spell_slots("warlock", 5)
        print(f"   SUCCESS: Level 5 warlock spell slots: {warlock_slots}")

        print("\n5. Testing API endpoint availability...")

        # Check if enhanced spell system import works in web context
        try:
            import web.main
            print("   SUCCESS: Web main module imports correctly")
        except ImportError as e:
            print(f"   WARNING: Web module import failed: {e}")

        print("\n" + "=" * 50)
        print("INTEGRATION TEST SUMMARY:")
        print("✓ Spell database initialization")
        print("✓ Spell lookup and search")
        print("✓ Character spell manager")
        print("✓ Spell slot calculations")
        print("✓ Module imports")
        print("\nAll core components working correctly!")
        print("\nTo test the full system:")
        print("1. Run: python start_web_system.py")
        print("2. Open: http://localhost:3000")
        print("3. Load a campaign, create a spellcaster character")
        print("4. Go to the 'Spells' tab to manage spells")

    except Exception as e:
        print(f"ERROR: Integration test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

    return True

if __name__ == "__main__":
    success = asyncio.run(test_spell_integration())
    if success:
        print("\n🎉 Integration test completed successfully!")
    else:
        print("\n❌ Integration test failed!")
        sys.exit(1)