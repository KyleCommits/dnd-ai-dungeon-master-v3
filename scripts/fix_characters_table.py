#!/usr/bin/env python3
"""Fix the characters table by dropping old table and recreating with new schema"""

import asyncio
import sys
import os

# add project root to python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import text
from src.database import engine
from src.models import Base

async def main():
    if not engine:
        print("FAILED: Database engine not initialized")
        return

    print("Fixing characters table...")
    try:
        async with engine.begin() as conn:
            # drop old characters table
            print("Dropping old characters table...")
            await conn.execute(text("DROP TABLE IF EXISTS characters CASCADE"))

            # drop related tables too
            print("Dropping old related tables...")
            await conn.execute(text("DROP TABLE IF EXISTS user_active_characters CASCADE"))
            await conn.execute(text("DROP TABLE IF EXISTS character_abilities CASCADE"))
            await conn.execute(text("DROP TABLE IF EXISTS character_skills CASCADE"))
            await conn.execute(text("DROP TABLE IF EXISTS character_features CASCADE"))
            await conn.execute(text("DROP TABLE IF EXISTS character_equipment CASCADE"))
            await conn.execute(text("DROP TABLE IF EXISTS character_spells CASCADE"))
            await conn.execute(text("DROP TABLE IF EXISTS character_progression CASCADE"))
            await conn.execute(text("DROP TABLE IF EXISTS character_level_history CASCADE"))
            await conn.execute(text("DROP TABLE IF EXISTS character_death_saves CASCADE"))
            await conn.execute(text("DROP TABLE IF EXISTS character_hit_dice CASCADE"))
            await conn.execute(text("DROP TABLE IF EXISTS character_milestones CASCADE"))
            await conn.execute(text("DROP TABLE IF EXISTS campaign_milestones CASCADE"))
            await conn.execute(text("DROP TABLE IF EXISTS npcs CASCADE"))
            await conn.execute(text("DROP TABLE IF EXISTS npc_abilities CASCADE"))
            await conn.execute(text("DROP TABLE IF EXISTS npc_skills CASCADE"))

            # recreate tables with new schema
            print("Creating new character tables...")
            await conn.run_sync(Base.metadata.create_all)

        print("SUCCESS: Characters table fixed with new D&D 5e schema!")

    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())