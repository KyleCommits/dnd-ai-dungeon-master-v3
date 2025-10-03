#!/usr/bin/env python3
"""Inspect database tables to see what exists"""

import asyncio
import sys
import os

# add project root to python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.database import engine
import asyncpg

async def main():
    if not engine:
        print("FAILED: Database engine not initialized")
        return

    print("Connecting to database...")
    try:
        async with engine.connect() as conn:
            # see what tables exist
            result = await conn.execute("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'")
            tables = [row[0] for row in result.fetchall()]
            print(f"Existing tables: {tables}")

            # check characters table schema if it exists
            if 'characters' in tables:
                print("\nInspecting 'characters' table schema:")
                result = await conn.execute("""
                    SELECT column_name, data_type, is_nullable
                    FROM information_schema.columns
                    WHERE table_name = 'characters'
                    ORDER BY ordinal_position
                """)
                columns = result.fetchall()
                for col in columns:
                    print(f"  {col[0]} ({col[1]}) - nullable: {col[2]}")
            else:
                print("No 'characters' table found")

    except Exception as e:
        print(f"ERROR: {e}")

if __name__ == "__main__":
    asyncio.run(main())