#!/usr/bin/env python3
"""Seed Postgres NPCs + world-state trust entries."""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

FIXTURE = os.path.join(ROOT, "scripts", "fixtures", "playtest_npcs.json")


async def seed(campaign_name: str | None) -> int:
    from sqlalchemy import select
    from src.database import async_session_scope, dispose_engine
    from src.character_models import NPC
    from src.models import Campaign
    from src.campaign_state_manager import campaign_state_manager, NPCRelationship

    with open(FIXTURE, "r", encoding="utf-8") as f:
        fixtures = json.load(f)

    try:
        async with async_session_scope() as db:
            if campaign_name:
                await campaign_state_manager.load_campaign(campaign_name)
                campaign_id = campaign_state_manager.campaign_db_id
            else:
                result = await db.execute(select(Campaign).order_by(Campaign.id).limit(1))
                camp = result.scalars().first()
                if not camp:
                    print("ERROR: no campaign in DB")
                    return 1
                bare = camp.name[:-3] if camp.name.endswith(".md") else camp.name
                await campaign_state_manager.load_campaign(bare)
                campaign_id = camp.id

            if not campaign_id or not campaign_state_manager.current_state:
                print("ERROR: could not load campaign world state")
                return 1

            for data in fixtures:
                existing = await db.execute(
                    select(NPC).where(
                        NPC.campaign_id == campaign_id,
                        NPC.name == data["name"],
                    )
                )
                npc = existing.scalars().first()
                if not npc:
                    npc = NPC(
                        campaign_id=campaign_id,
                        name=data["name"],
                        race=data["race"],
                        class_name=data.get("class_name"),
                        level=data.get("level", 1),
                        npc_type=data["npc_type"],
                        max_hp=data["max_hp"],
                        current_hp=data["max_hp"],
                        armor_class=data["armor_class"],
                        speed=data.get("speed", 30),
                    )
                    db.add(npc)
                    print(f"SUCCESS: created NPC {data['name']}")
                else:
                    print(f"[OK] NPC exists: {data['name']}")

                key = data["name"].lower().replace(" ", "_")
                campaign_state_manager.current_state.npc_relationships[key] = NPCRelationship(
                    name=data["name"],
                    relationship=data.get("relationship", "neutral"),
                    trust_level=int(data.get("trust_level", 0)),
                    last_interaction=data.get("last_interaction", ""),
                    secrets_known=[],
                    personal_connection="",
                )

            await db.commit()

        await campaign_state_manager._save_state()
        print("SUCCESS: NPC trust entries saved to world state")
        return 0
    finally:
        await dispose_engine()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--campaign", default=None)
    args = parser.parse_args()
    try:
        return asyncio.run(seed(args.campaign))
    except Exception as e:
        print(f"ERROR: {e}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
