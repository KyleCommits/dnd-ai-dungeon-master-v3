#!/usr/bin/env python3
"""
Test script to check Acid Splash spell data
"""
import asyncio
import sys
sys.path.append('src')

async def check_acid_splash():
    from src.enhanced_spell_system import enhanced_spell_manager

    # Initialize the spell manager
    enhanced_spell_manager.initialize()

    # Get Acid Splash
    acid_splash = enhanced_spell_manager.get_spell("Acid Splash")

    if acid_splash:
        print(f"Acid Splash found:")
        print(f"  Name: {acid_splash.name}")
        print(f"  Level: {acid_splash.level}")
        print(f"  School: {acid_splash.school}")
        print(f"  Has damage: {acid_splash.damage is not None}")

        if acid_splash.damage:
            print(f"  Damage type: {acid_splash.damage.damage_type}")
            print(f"  Damage at slot levels: {acid_splash.damage.damage_at_slot_level}")

        print(f"  Has saving throw: {acid_splash.saving_throw is not None}")
        if acid_splash.saving_throw:
            print(f"  Save: {acid_splash.saving_throw.ability_score} {acid_splash.saving_throw.success_type}")
    else:
        print("Acid Splash not found!")

if __name__ == "__main__":
    asyncio.run(check_acid_splash())