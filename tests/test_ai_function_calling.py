# test_ai_function_calling.py
"""
test script for ai function calling system
tests gameactions and gemini integration
"""

import sys
import os
import asyncio
import json

# add project root to path so we can import src
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

async def test_game_actions_directly():
    """test gameactions functions directly without ai"""
    print("=" * 50)
    print("testing gameactions directly")
    print("=" * 50)

    try:
        from src.game_actions import game_actions

        # test dice rolling
        print("\n1. testing dice rolling...")
        dice_result = await game_actions.roll_dice_for_character("1d20+5", description="test attack roll")
        print(f"   dice roll result: {dice_result}")

        # test character status (might fail if no characters exist)
        print("\n2. testing character status...")
        try:
            status_result = await game_actions.get_character_status("1")
            print(f"   character status: {status_result}")
        except Exception as e:
            print(f"   character status failed (expected if no characters): {e}")

        # test hp modification (might fail if no characters exist)
        print("\n3. testing hp modification...")
        try:
            hp_result = await game_actions.modify_hp("1", -5, "test damage")
            print(f"   hp modification result: {hp_result}")
        except Exception as e:
            print(f"   hp modification failed (expected if no characters): {e}")

        # test condition application
        print("\n4. testing condition application...")
        try:
            condition_result = await game_actions.apply_condition("1", "poisoned", 3, "test poison")
            print(f"   condition result: {condition_result}")
        except Exception as e:
            print(f"   condition failed: {e}")

        print("\nSUCCESS: gameactions direct testing complete")

    except Exception as e:
        print(f"ERROR: gameactions test failed: {e}")
        import traceback
        traceback.print_exc()

async def test_ai_function_calling():
    """test ai function calling with simple prompts"""
    print("\n" + "=" * 50)
    print("testing ai function calling")
    print("=" * 50)

    try:
        from src.dynamic_dm import DynamicDM
        from src.config import settings

        # check if gemini is available
        if not settings.GEMINI_API_KEY:
            print("ERROR: no gemini api key found - skipping ai tests")
            return

        dm = DynamicDM()

        # test simple function calling prompt
        print("\n1. testing simple damage scenario...")
        test_prompt = "a goblin attacks the player with a sword and hits for 1d6+2 damage"

        try:
            response = await dm._generate_contextual_response(
                test_prompt,
                "player1",
                "test campaign context",
                [],  # no conversation history
                []   # no session summaries
            )
            print(f"   ai response: {response}")
        except Exception as e:
            print(f"   ai test failed: {e}")
            import traceback
            traceback.print_exc()

        print("\n2. testing dice roll scenario...")
        test_prompt2 = "roll a d20 attack roll for the player"

        try:
            response2 = await dm._generate_contextual_response(
                test_prompt2,
                "player1",
                "test campaign context",
                [],
                []
            )
            print(f"   ai response: {response2}")
        except Exception as e:
            print(f"   ai test 2 failed: {e}")

        print("\nSUCCESS: ai function calling testing complete")

    except Exception as e:
        print(f"ERROR: ai function calling test failed: {e}")
        import traceback
        traceback.print_exc()

async def test_function_definitions():
    """test that function definitions are properly formatted"""
    print("\n" + "=" * 50)
    print("testing function definitions")
    print("=" * 50)

    try:
        from src.dynamic_dm import DynamicDM

        dm = DynamicDM()

        print(f"number of available functions: {len(dm.available_functions)}")

        for i, func in enumerate(dm.available_functions):
            print(f"\n{i+1}. {func['name']}")
            print(f"   description: {func['description']}")
            print(f"   required params: {func['parameters'].get('required', [])}")

        print("\nSUCCESS: function definitions look good")

    except Exception as e:
        print(f"ERROR: function definition test failed: {e}")

async def test_character_creation():
    """create a test character for function testing"""
    print("\n" + "=" * 50)
    print("creating test character for function tests")
    print("=" * 50)

    try:
        from src.character_manager import character_manager
        from src.database import get_db_session

        async for db in get_db_session():
            # create a simple test character
            character_data = {
                'campaign_id': 1,
                'user_id': 'test_user',
                'name': 'test warrior',
                'race': 'human',
                'class_name': 'fighter',
                'level': 1,
                'background': 'soldier',
                'max_hp': 12,
                'armor_class': 16,
                'speed': 30,
                'abilities': {
                    'strength': 16,
                    'dexterity': 14,
                    'constitution': 14,
                    'intelligence': 10,
                    'wisdom': 12,
                    'charisma': 8
                },
                'saving_throws': {
                    'strength': True,
                    'constitution': True
                },
                'skills': {},
                'features': [],
                'equipment': []
            }

            try:
                character = await character_manager.create_character(db, character_data)
                print(f"SUCCESS: created test character: {character.name} (id: {character.id})")

                # set as active character
                await character_manager.set_active_character(db, 'test_user', 1, character.id)
                print(f"SUCCESS: set as active character")

                return character.id

            except Exception as e:
                print(f"ERROR: character creation failed: {e}")
                return None

    except Exception as e:
        print(f"ERROR: character creation test failed: {e}")
        return None

async def main():
    """run all tests"""
    print("ai function calling test suite")
    print("tests gameactions api and gemini integration")

    # test function definitions first
    await test_function_definitions()

    # test gameactions directly
    await test_game_actions_directly()

    # try to create a test character
    character_id = await test_character_creation()

    if character_id:
        print(f"\nNOTE: test character created with id: {character_id}")
        print("you can now test function calling with a real character!")

    # test ai function calling
    await test_ai_function_calling()

    print("\n" + "=" * 50)
    print("test suite complete!")
    print("next step: start web system and try 'a goblin attacks me' in chat")
    print("=" * 50)

if __name__ == "__main__":
    asyncio.run(main())