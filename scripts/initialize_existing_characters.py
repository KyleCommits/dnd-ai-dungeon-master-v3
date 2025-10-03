# initialize_existing_characters.py
"""
Utility to initialize spells for existing characters that were created before the spell system
"""

import asyncio
import sys
import os

# add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

async def initialize_existing_characters():
    """Initialize spells for all existing spellcaster characters"""
    print("Initializing Spells for Existing Characters")
    print("=" * 50)

    try:
        from src.database import get_db_session
        from src.character_manager import character_manager
        from src.spell_integration import character_spell_manager
        from src.character_models import Character
        from sqlalchemy import select

        # get db session
        async for db in get_db_session():
            # get all characters
            result = await db.execute(select(Character))
            all_characters = result.scalars().all()

            print(f"Found {len(all_characters)} characters total")

            spellcaster_classes = [
                "Wizard", "Sorcerer", "Cleric", "Druid", "Bard", "Warlock",
                "Paladin", "Ranger", "Eldritch Knight", "Arcane Trickster"
            ]

            spellcasters_found = []
            for character in all_characters:
                if character.class_name in spellcaster_classes:
                    spellcasters_found.append(character)
                    print(f"  - {character.name} (Level {character.level} {character.class_name})")

            print(f"\nFound {len(spellcasters_found)} spellcaster characters")

            if not spellcasters_found:
                print("No spellcaster characters found. Nothing to initialize.")
                return

            response = input(f"\nInitialize spells for {len(spellcasters_found)} characters? (y/n): ").lower()
            if response != 'y':
                print("Spell initialization cancelled.")
                return

            print("\nInitializing spells...")

            success_count = 0
            for character in spellcasters_found:
                try:
                    print(f"\nInitializing spells for {character.name} ({character.class_name})...")

                    # see if character already has spells
                    existing_spells = await character_manager.get_character_spells(db, character.id)
                    if existing_spells and existing_spells.get('total_spells', 0) > 0:
                        print(f"  {character.name} already has {existing_spells['total_spells']} spells - skipping")
                        continue

                    # Initialize spells for this character
                    await character_spell_manager.initialize_character_spells(db, character)

                    # Verify spells were added
                    updated_spells = await character_manager.get_character_spells(db, character.id)
                    spell_count = updated_spells.get('total_spells', 0)

                    print(f"  SUCCESS: Added {spell_count} spells to {character.name}")
                    success_count += 1

                except Exception as e:
                    print(f"  ERROR: Failed to initialize spells for {character.name}: {e}")

            print(f"\n" + "=" * 50)
            print(f"SPELL INITIALIZATION COMPLETE")
            print(f"Successfully initialized: {success_count}/{len(spellcasters_found)} characters")

            if success_count > 0:
                print(f"\nYour existing spellcaster characters now have their spells!")
                print("You can view and manage them in the 'Spells' tab.")

            break  # Exit the async generator

    except Exception as e:
        print(f"ERROR: Failed to initialize characters: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(initialize_existing_characters())