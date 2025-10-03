#!/usr/bin/env python3
"""
Test script to check Bobby's spell data in the database
"""
import asyncio
import sys
sys.path.append('src')

async def check_bobby_spells():
    from src.database import get_db_session
    from src.character_models import Character, CharacterSpell
    from sqlalchemy import select
    from sqlalchemy.orm import selectinload

    async for db in get_db_session():
        # Get Bobby
        query = select(Character).options(selectinload(Character.abilities)).where(Character.id == 4)
        result = await db.execute(query)
        bobby = result.scalar_one_or_none()

        if bobby:
            print(f'Bobby found: {bobby.name}, class: {bobby.class_name}')

            # Get Bobby's spells
            spell_query = select(CharacterSpell).where(CharacterSpell.character_id == 4)
            result = await db.execute(spell_query)
            spells = result.scalars().all()
            print(f'Bobby has {len(spells)} spells in database')
            for spell in spells:
                print(f'  - {spell.spell_name} (Level {spell.spell_level}, Prepared: {spell.prepared})')
        else:
            print('Bobby not found!')
        break  # Only need one iteration

if __name__ == "__main__":
    asyncio.run(check_bobby_spells())