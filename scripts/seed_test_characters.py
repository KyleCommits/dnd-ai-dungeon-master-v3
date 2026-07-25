#!/usr/bin/env python3
"""Seed 2–3 playtest PCs. Idempotent by character name + campaign."""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

FIXTURE = os.path.join(ROOT, "scripts", "fixtures", "playtest_characters.json")
DEFAULT_USER = "player1"


async def _resolve_campaign_id(db, campaign_name: str | None):
    from sqlalchemy import select
    from src.models import Campaign
    from src.campaign_state_manager import campaign_state_manager

    if campaign_name:
        await campaign_state_manager.load_campaign(campaign_name)
        if campaign_state_manager.campaign_db_id:
            return campaign_state_manager.campaign_db_id

    result = await db.execute(select(Campaign).order_by(Campaign.id).limit(1))
    camp = result.scalars().first()
    if camp:
        bare = camp.name[:-3] if camp.name.endswith(".md") else camp.name
        await campaign_state_manager.load_campaign(bare)
        return camp.id
    return None


async def seed(campaign_name: str | None, user_id: str) -> int:
    from sqlalchemy import select
    from src.database import async_session_scope, dispose_engine
    from src.character_models import Character
    from src.character_manager import character_manager

    with open(FIXTURE, "r", encoding="utf-8") as f:
        fixtures = json.load(f)

    created = 0
    try:
        async with async_session_scope() as db:
            campaign_id = await _resolve_campaign_id(db, campaign_name)
            if not campaign_id:
                print("ERROR: no campaign in DB. Load a campaign first or pass --campaign")
                return 1

            first_id = None
            for data in fixtures:
                existing = await db.execute(
                    select(Character).where(
                        Character.campaign_id == campaign_id,
                        Character.name == data["name"],
                    )
                )
                char = existing.scalars().first()
                if char:
                    print(f"[OK] exists: {char.name} (id={char.id})")
                    if first_id is None:
                        first_id = char.id
                    continue

                payload = dict(data)
                payload["campaign_id"] = campaign_id
                payload["user_id"] = user_id
                char = await character_manager.create_character(db, payload)
                print(f"SUCCESS: created {char.name} (id={char.id})")
                created += 1
                if first_id is None:
                    first_id = char.id

            if first_id:
                await character_manager.set_active_character(db, user_id, campaign_id, first_id)
                print(f"SUCCESS: active character id={first_id} for user={user_id}")

        print(f"SUCCESS: seeded characters (new={created})")
        return 0
    finally:
        await dispose_engine()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--campaign", default=None, help="Campaign name without .md")
    parser.add_argument("--user-id", default=DEFAULT_USER)
    args = parser.parse_args()
    try:
        return asyncio.run(seed(args.campaign, args.user_id))
    except Exception as e:
        print(f"ERROR: {e}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
