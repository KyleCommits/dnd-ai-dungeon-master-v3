"""
Phase 4 world memory — unit tests (no Postgres required for core converters).
"""

import os
import sys
from datetime import datetime

import pytest

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)


def test_state_dataclass_roundtrip_fields():
    from src.campaign_state_manager import CampaignState, NPCRelationship, PlotThread
    from src.world_state_store import state_dataclass_to_row_fields, row_to_state_dict

    state = CampaignState(
        campaign_name="demo",
        current_act=2,
        current_scene="Market",
        location="River Town",
        session_count=3,
        completed_plot_points=["Found the map"],
        missed_opportunities=[],
        active_plot_threads=[
            PlotThread(
                id="main_1",
                name="Find the relic",
                status="active",
                importance="main",
                related_npcs=["Mayor Aldric"],
                related_locations=["River Town"],
                player_actions=["Asked about the relic"],
                next_hooks=[],
            )
        ],
        npc_relationships={
            "mayor_aldric": NPCRelationship(
                name="Mayor Aldric",
                relationship="ally",
                trust_level=25,
                last_interaction="Helped with bandits",
                secrets_known=[],
                personal_connection="",
            )
        },
        major_decisions=[],
        reputation={"town": 10},
        custom_hooks=[],
        adaptive_elements=[],
        last_updated=datetime.utcnow().isoformat(),
        notes="test",
    )
    fields = state_dataclass_to_row_fields(state)
    assert fields["location"] == "River Town"
    assert fields["session_count"] == 3
    assert fields["npc_relationships"]["mayor_aldric"]["trust_level"] == 25
    assert fields["active_plot_threads"][0]["id"] == "main_1"

    class FakeRow:
        current_act = fields["current_act"]
        current_scene = fields["current_scene"]
        location = fields["location"]
        session_count = fields["session_count"]
        npc_relationships = fields["npc_relationships"]
        active_plot_threads = fields["active_plot_threads"]
        major_decisions = fields["major_decisions"]
        plot_flags = {}
        completed_plot_points = fields["completed_plot_points"]
        missed_opportunities = fields["missed_opportunities"]
        reputation = fields["reputation"]
        custom_hooks = fields["custom_hooks"]
        adaptive_elements = fields["adaptive_elements"]
        notes = fields["notes"]
        updated_at = datetime.utcnow()

    data = row_to_state_dict(FakeRow(), "demo")
    assert data["location"] == "River Town"
    assert data["npc_relationships"]["mayor_aldric"]["trust_level"] == 25


def test_update_npc_relationship_in_memory():
    """Mutator updates trust bands without requiring DB if save is stubbed."""
    import asyncio
    from src.campaign_state_manager import (
        CampaignStateManager,
        CampaignState,
        NPCRelationship,
    )

    mgr = CampaignStateManager()
    mgr.current_state = CampaignState(
        campaign_name="demo",
        current_act=1,
        current_scene="Opening",
        location="Start",
        session_count=0,
        completed_plot_points=[],
        missed_opportunities=[],
        active_plot_threads=[],
        npc_relationships={},
        major_decisions=[],
        reputation={},
        custom_hooks=[],
        adaptive_elements=[],
        last_updated=datetime.utcnow().isoformat(),
        notes="",
    )
    mgr.campaign_db_id = None  # skip postgres
    mgr.state_file_path = ""

    async def _run():
        ok = await mgr.update_npc_relationship("Mayor Aldric", "helped", trust_delta=30)
        assert ok is True
        key = "mayor_aldric"
        assert key in mgr.current_state.npc_relationships
        npc = mgr.current_state.npc_relationships[key]
        assert npc.trust_level == 30
        assert npc.relationship == "ally"

    asyncio.run(_run())


def test_game_actions_memory_requires_campaign():
    import asyncio
    from src.game_actions import game_actions
    from src.campaign_state_manager import campaign_state_manager

    campaign_state_manager.current_state = None

    async def _run():
        r = await game_actions.update_npc_relationship("Bob", trust_delta=5)
        assert r["success"] is False
        r2 = await game_actions.set_location("Forest")
        assert r2["success"] is False

    asyncio.run(_run())


def test_ascii_help_mentions_npc():
    from src.ascii_ui.render_status import render_help

    text = render_help()
    assert "/npc" in text
    assert "/session" in text


def test_playtest_monster_seed_script():
    import importlib.util
    import tempfile

    from src.rules_db import RulesDB

    spec = importlib.util.spec_from_file_location(
        "seed_test_monsters",
        os.path.join(project_root, "scripts", "seed_test_monsters.py"),
    )
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)

    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    try:
        db = RulesDB(path)
        db.initialize_schema()
        for m in mod.PLAYTEST_MONSTERS:
            db.upsert_monster(m)
        goblin = db.get_monster("Goblin")
        assert goblin is not None
        assert goblin["ac"] == 15
        assert goblin["hp"] == 7
    finally:
        try:
            os.remove(path)
        except OSError:
            pass
