# src/world_state_store.py — Postgres persistence for campaign world memory
from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .models import Campaign, CampaignWorldState

logger = logging.getLogger(__name__)


def _npc_to_dict(npc) -> Dict[str, Any]:
    return {
        "name": npc.name,
        "relationship": npc.relationship,
        "trust_level": npc.trust_level,
        "last_interaction": npc.last_interaction,
        "secrets_known": list(npc.secrets_known or []),
        "personal_connection": npc.personal_connection or "",
    }


def _thread_to_dict(thread) -> Dict[str, Any]:
    return {
        "id": thread.id,
        "name": thread.name,
        "status": thread.status,
        "importance": thread.importance,
        "related_npcs": list(thread.related_npcs or []),
        "related_locations": list(thread.related_locations or []),
        "player_actions": list(thread.player_actions or []),
        "next_hooks": list(thread.next_hooks or []),
    }


def state_dataclass_to_row_fields(state) -> Dict[str, Any]:
    """Convert CampaignState dataclass → CampaignWorldState column values."""
    npc_map = {}
    for key, npc in (state.npc_relationships or {}).items():
        npc_map[key] = _npc_to_dict(npc) if hasattr(npc, "name") else npc
    threads = []
    for t in state.active_plot_threads or []:
        threads.append(_thread_to_dict(t) if hasattr(t, "id") else t)
    return {
        "current_act": state.current_act,
        "current_scene": str(state.current_scene),
        "location": state.location,
        "session_count": int(state.session_count or 0),
        "npc_relationships": npc_map,
        "active_plot_threads": threads,
        "major_decisions": list(state.major_decisions or []),
        "plot_flags": {},
        "completed_plot_points": list(state.completed_plot_points or []),
        "missed_opportunities": list(state.missed_opportunities or []),
        "reputation": dict(state.reputation or {}),
        "custom_hooks": list(state.custom_hooks or []),
        "adaptive_elements": list(state.adaptive_elements or []),
        "notes": state.notes or "",
        "updated_at": datetime.utcnow(),
    }


def row_to_state_dict(row: CampaignWorldState, campaign_name: str) -> Dict[str, Any]:
    return {
        "campaign_name": campaign_name,
        "current_act": row.current_act or 1,
        "current_scene": row.current_scene or "Opening",
        "location": row.location or "Starting Location",
        "session_count": row.session_count or 0,
        "completed_plot_points": row.completed_plot_points or [],
        "missed_opportunities": row.missed_opportunities or [],
        "active_plot_threads": row.active_plot_threads or [],
        "npc_relationships": row.npc_relationships or {},
        "major_decisions": row.major_decisions or [],
        "reputation": row.reputation or {},
        "custom_hooks": row.custom_hooks or [],
        "adaptive_elements": row.adaptive_elements or [],
        "last_updated": (row.updated_at or datetime.utcnow()).isoformat(),
        "notes": row.notes or "",
    }


async def get_campaign_by_name(db: AsyncSession, campaign_name: str) -> Optional[Campaign]:
    search = campaign_name if campaign_name.endswith(".md") else f"{campaign_name}.md"
    result = await db.execute(select(Campaign).where(Campaign.name == search))
    camp = result.scalars().first()
    if camp:
        return camp
    # also try bare name / display_name
    result = await db.execute(
        select(Campaign).where(
            (Campaign.name == campaign_name) | (Campaign.display_name == campaign_name)
        )
    )
    return result.scalars().first()


async def get_world_state_row(db: AsyncSession, campaign_id: int) -> Optional[CampaignWorldState]:
    result = await db.execute(
        select(CampaignWorldState).where(CampaignWorldState.campaign_id == campaign_id)
    )
    return result.scalars().first()


async def upsert_world_state(
    db: AsyncSession, campaign_id: int, fields: Dict[str, Any]
) -> CampaignWorldState:
    row = await get_world_state_row(db, campaign_id)
    if not row:
        row = CampaignWorldState(campaign_id=campaign_id)
        db.add(row)
    for key, value in fields.items():
        if hasattr(row, key):
            setattr(row, key, value)
    row.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(row)
    return row
