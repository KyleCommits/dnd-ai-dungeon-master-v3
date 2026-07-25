#!/usr/bin/env python3
"""
Soft reset: clear play/session data. Keeps schema and campaign markdown rows by default.

Usage:
  python scripts/reset_play_data.py --yes
  python scripts/reset_play_data.py --yes --characters --npcs
"""
from __future__ import annotations

import argparse
import asyncio
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)


async def reset(delete_characters: bool, delete_npcs: bool) -> None:
    from sqlalchemy import text
    from src.database import async_session_scope, dispose_engine, engine

    if engine is None:
        raise RuntimeError("Database engine not configured")

    try:
        await _reset_inner(delete_characters, delete_npcs)
    finally:
        await dispose_engine()


async def _reset_inner(delete_characters: bool, delete_npcs: bool) -> None:
    from sqlalchemy import text
    from src.database import async_session_scope

    async with async_session_scope() as db:
        # Order matters for FKs
        await db.execute(text("DELETE FROM chat_messages"))
        await db.execute(text("DELETE FROM session_summaries"))
        await db.execute(text("DELETE FROM campaign_state"))
        await db.execute(text("DELETE FROM campaign_world_state"))
        await db.execute(text("DELETE FROM chat_sessions"))
        await db.execute(text("DELETE FROM user_active_characters"))

        if delete_characters:
            from src.animal_companion_models import (
                CompanionEquipment,
                CompanionAbility,
                CompanionProgression,
                AnimalCompanion,
            )
            from src.character_models import (
                CharacterSpell,
                CharacterEquipment,
                CharacterFeature,
                CharacterSkill,
                CharacterAbility,
                CharacterHitDice,
                CharacterDeathSave,
                CharacterProgression,
                Character,
            )

            for model in (
                CompanionEquipment,
                CompanionAbility,
                CompanionProgression,
                AnimalCompanion,
                CharacterSpell,
                CharacterEquipment,
                CharacterFeature,
                CharacterSkill,
                CharacterAbility,
                CharacterHitDice,
                CharacterDeathSave,
                CharacterProgression,
                Character,
            ):
                try:
                    await db.execute(text(f"DELETE FROM {model.__tablename__}"))
                except Exception as e:
                    print(f"WARNING: skip {model.__tablename__}: {e}")

        if delete_npcs:
            from src.character_models import NPCSkill, NPCAbility, NPC

            for model in (NPCSkill, NPCAbility, NPC):
                try:
                    await db.execute(text(f"DELETE FROM {model.__tablename__}"))
                except Exception as e:
                    print(f"WARNING: skip {model.__tablename__}: {e}")

        await db.commit()
    print("SUCCESS: play data cleared")
    if delete_characters:
        print("SUCCESS: characters cleared")
    if delete_npcs:
        print("SUCCESS: NPCs cleared")


def main() -> int:
    parser = argparse.ArgumentParser(description="Clear play/session data")
    parser.add_argument("--yes", action="store_true", help="Required confirmation")
    parser.add_argument("--characters", action="store_true", help="Also delete PCs")
    parser.add_argument("--npcs", action="store_true", help="Also delete NPC rows")
    args = parser.parse_args()
    if not args.yes:
        print("ERROR: refusing to run without --yes (destructive)")
        return 1
    try:
        asyncio.run(reset(args.characters, args.npcs))
    except Exception as e:
        print(f"ERROR: {e}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
