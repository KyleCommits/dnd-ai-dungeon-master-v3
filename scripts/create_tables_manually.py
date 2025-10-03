#!/usr/bin/env python3
"""Manual table creation script to debug database issues"""

import asyncio
import sys
import os

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.database import create_tables

async def main():
    print("Attempting to create database tables...")
    result = await create_tables()
    if result:
        print("SUCCESS: All database tables created successfully!")
    else:
        print("FAILED: Could not create database tables")

if __name__ == "__main__":
    asyncio.run(main())