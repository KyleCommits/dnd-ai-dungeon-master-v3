# src/campaign_state_manager.py
"""
Campaign PlayState layer.

Responsibility: load a campaign for play, track act/location/NPCs/plot threads,
and supply DynamicDM context. Phase 4: Postgres campaign_world_state is source of truth;
JSON sidecar is import-only fallback. Persist+index belongs to campaign_manager.
"""
import json
import logging
import os
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from .config import settings
from .database import async_session_scope

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

@dataclass
class NPCRelationship:
    """Tracks player relationships with NPCs"""
    name: str
    relationship: str  # "trusted", "enemy", "neutral", "suspicious", "ally", etc.
    trust_level: int   # -100 to 100
    last_interaction: str
    secrets_known: List[str]
    personal_connection: str  # Any personal connection or backstory

@dataclass
class PlotThread:
    """Represents an ongoing plot thread"""
    id: str
    name: str
    status: str  # "active", "completed", "failed", "dormant"
    importance: str  # "main", "side", "background"
    related_npcs: List[str]
    related_locations: List[str]
    player_actions: List[str]
    next_hooks: List[str]

@dataclass
class CampaignState:
    """Complete state of the campaign"""
    campaign_name: str
    current_act: int
    current_scene: str
    location: str
    session_count: int
    
    # Plot progression tracking
    completed_plot_points: List[str]
    missed_opportunities: List[str]
    active_plot_threads: List[PlotThread]
    
    # Character relationships
    npc_relationships: Dict[str, NPCRelationship]
    
    # Player choices and consequences
    major_decisions: List[Dict[str, Any]]
    reputation: Dict[str, int]  # reputation with different factions
    
    # Dynamic story elements
    custom_hooks: List[str]  # DM-created hooks based on player actions
    adaptive_elements: List[str]  # Story elements adapted from player choices
    
    # Meta information
    last_updated: str
    notes: str

class CampaignStateManager:
    """Manages the dynamic state of an active campaign"""
    
    def __init__(self):
        self.current_state: Optional[CampaignState] = None
        self.campaign_data: Optional[Dict[str, Any]] = None
        self.state_file_path = ""
        self.campaign_db_id: Optional[int] = None
        self.campaign_name: str = ""
    
    async def load_campaign(self, campaign_name: str) -> bool:
        """Load campaign data and initialize or restore state (Postgres first)."""
        try:
            campaign_file = os.path.join(settings.custom_campaign_path, f"{campaign_name}.md")
            if not os.path.exists(campaign_file):
                logging.error(f"Campaign file not found: {campaign_file}")
                return False
            
            self.campaign_data = await self._parse_campaign_file(campaign_file)
            self.campaign_name = campaign_name
            self.state_file_path = os.path.join(
                settings.custom_campaign_path, f"{campaign_name}_state.json"
            )

            await self._ensure_campaign_db_row(campaign_name, campaign_file)

            loaded = await self._load_state_from_db()
            if loaded:
                logging.info(f"Loaded campaign world state from Postgres for: {campaign_name}")
                return True

            if os.path.exists(self.state_file_path):
                self.current_state = await self._load_state_from_file()
                await self._save_state()
                logging.info(
                    f"Imported JSON sidecar into Postgres for: {campaign_name}"
                )
                return True

            self.current_state = await self._initialize_new_state(campaign_name)
            logging.info(f"Created new campaign world state for: {campaign_name}")
            return True
            
        except Exception as e:
            logging.error(f"Failed to load campaign {campaign_name}: {e}")
            return False

    async def _ensure_campaign_db_row(self, campaign_name: str, campaign_file: str) -> None:
        from .models import Campaign
        from .world_state_store import get_campaign_by_name

        async with async_session_scope() as db:
            camp = await get_campaign_by_name(db, campaign_name)
            if not camp:
                display = (
                    (self.campaign_data or {}).get("title")
                    or campaign_name.replace("_", " ").title()
                )
                camp = Campaign(
                    name=f"{campaign_name}.md" if not campaign_name.endswith(".md") else campaign_name,
                    display_name=display,
                    description=((self.campaign_data or {}).get("description") or "")[:2000],
                    file_path=campaign_file,
                    is_active=True,
                )
                db.add(camp)
                await db.commit()
                await db.refresh(camp)
                logging.info("Created campaigns row for %s (id=%s)", campaign_name, camp.id)
            self.campaign_db_id = camp.id

    async def _load_state_from_db(self) -> bool:
        if not self.campaign_db_id:
            return False
        from .world_state_store import get_world_state_row, row_to_state_dict

        async with async_session_scope() as db:
            row = await get_world_state_row(db, self.campaign_db_id)
            if not row:
                return False
            data = row_to_state_dict(row, self.campaign_name)
            self.current_state = self._dict_to_state(data)
            return True

    def _dict_to_state(self, data: Dict[str, Any]) -> CampaignState:
        npc_relationships = {}
        for npc_name, npc_data in data.get("npc_relationships", {}).items():
            if isinstance(npc_data, NPCRelationship):
                npc_relationships[npc_name] = npc_data
            else:
                npc_relationships[npc_name] = NPCRelationship(
                    name=npc_data.get("name", npc_name),
                    relationship=npc_data.get("relationship", "neutral"),
                    trust_level=int(npc_data.get("trust_level", 0)),
                    last_interaction=npc_data.get("last_interaction", ""),
                    secrets_known=list(npc_data.get("secrets_known") or []),
                    personal_connection=npc_data.get("personal_connection", ""),
                )
        active_plot_threads = []
        for thread_data in data.get("active_plot_threads", []):
            if isinstance(thread_data, PlotThread):
                active_plot_threads.append(thread_data)
            else:
                active_plot_threads.append(PlotThread(**thread_data))
        return CampaignState(
            campaign_name=data.get("campaign_name", self.campaign_name),
            current_act=int(data.get("current_act", 1)),
            current_scene=str(data.get("current_scene", "Opening")),
            location=str(data.get("location", "Starting Location")),
            session_count=int(data.get("session_count", 0)),
            completed_plot_points=list(data.get("completed_plot_points") or []),
            missed_opportunities=list(data.get("missed_opportunities") or []),
            active_plot_threads=active_plot_threads,
            npc_relationships=npc_relationships,
            major_decisions=list(data.get("major_decisions") or []),
            reputation=dict(data.get("reputation") or {}),
            custom_hooks=list(data.get("custom_hooks") or []),
            adaptive_elements=list(data.get("adaptive_elements") or []),
            last_updated=str(data.get("last_updated") or datetime.now().isoformat()),
            notes=str(data.get("notes") or ""),
        )
    
    async def _parse_campaign_file(self, filepath: str) -> Dict[str, Any]:
        """Parse campaign markdown file into structured data"""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Extract structured data from markdown (simplified parser)
            campaign_data = {
                "title": self._extract_title(content),
                "description": self._extract_section(content, "## Description"),
                "npcs": self._extract_npcs(content),
                "locations": self._extract_locations(content),
                "plot_points": self._extract_plot_points(content),
                "decision_points": self._extract_decision_points(content),
                "plot_twists": self._extract_plot_twists(content),
                "themes": self._extract_themes(content),
                "full_content": content
            }
            
            return campaign_data
            
        except Exception as e:
            logging.error(f"Failed to parse campaign file: {e}")
            return {}
    
    def _extract_title(self, content: str) -> str:
        """Extract campaign title from markdown"""
        lines = content.split('\n')
        for line in lines:
            if line.startswith('# '):
                return line[2:].strip()
        return "Unknown Campaign"
    
    def _extract_section(self, content: str, section_header: str) -> str:
        """Extract content from a specific markdown section"""
        lines = content.split('\n')
        in_section = False
        section_content = []
        
        for line in lines:
            if line.strip() == section_header:
                in_section = True
                continue
            elif line.startswith('##') and in_section:
                break
            elif in_section:
                section_content.append(line)
        
        return '\n'.join(section_content).strip()
    
    def _extract_npcs(self, content: str) -> List[Dict[str, str]]:
        """Extract NPC information from campaign"""
        npcs = []
        lines = content.split('\n')
        current_npc = None
        
        for line in lines:
            if line.startswith('### ') and 'NPC' in content[max(0, content.find(line) - 200):content.find(line)]:
                if current_npc:
                    npcs.append(current_npc)
                current_npc = {"name": line[4:].strip(), "description": ""}
            elif current_npc and line.strip() and not line.startswith('#'):
                current_npc["description"] += line + " "
        
        if current_npc:
            npcs.append(current_npc)
        
        return npcs
    
    def _extract_locations(self, content: str) -> List[Dict[str, str]]:
        """Extract location information from campaign"""
        locations = []
        lines = content.split('\n')
        in_locations = False
        current_location = None
        
        for line in lines:
            if '## Key Locations' in line:
                in_locations = True
                continue
            elif line.startswith('##') and in_locations:
                break
            elif in_locations and line.startswith('### '):
                if current_location:
                    locations.append(current_location)
                current_location = {"name": line[4:].strip(), "description": ""}
            elif current_location and line.strip() and not line.startswith('#'):
                current_location["description"] += line + " "
        
        if current_location:
            locations.append(current_location)
        
        return locations
    
    def _extract_plot_points(self, content: str) -> List[str]:
        """Extract major plot points from campaign acts"""
        plot_points = []
        
        # Extract from Act sections
        for act_num in [1, 2, 3]:
            act_content = self._extract_section(content, f"### Act {act_num}:")
            if act_content:
                # Simple extraction of key events (could be enhanced)
                sentences = act_content.split('.')
                for sentence in sentences[:3]:  # Take first 3 major points per act
                    if len(sentence.strip()) > 20:
                        plot_points.append(f"Act {act_num}: {sentence.strip()}")
        
        return plot_points
    
    def _extract_decision_points(self, content: str) -> List[str]:
        """Extract key decision points from campaign"""
        decision_content = self._extract_section(content, "### Key Decision Points")
        if not decision_content:
            return []
        
        decisions = []
        for line in decision_content.split('\n'):
            if line.strip().startswith('- '):
                decisions.append(line.strip()[2:])
        
        return decisions
    
    def _extract_plot_twists(self, content: str) -> List[str]:
        """Extract potential plot twists from campaign"""
        twist_content = self._extract_section(content, "### Potential Plot Twists")
        if not twist_content:
            return []
        
        twists = []
        for line in twist_content.split('\n'):
            if line.strip().startswith('- '):
                twists.append(line.strip()[2:])
        
        return twists
    
    def _extract_themes(self, content: str) -> List[str]:
        """Extract recurring themes from campaign"""
        theme_content = self._extract_section(content, "### Recurring Themes")
        if not theme_content:
            return []
        
        themes = []
        for line in theme_content.split('\n'):
            if line.strip().startswith('- '):
                themes.append(line.strip()[2:])
        
        return themes
    
    async def _initialize_new_state(self, campaign_name: str) -> CampaignState:
        """Initialize a new campaign state"""
        
        # Initialize NPC relationships from campaign data
        npc_relationships = {}
        for npc in self.campaign_data.get('npcs', []):
            npc_name = npc['name'].lower().replace(' ', '_')
            npc_relationships[npc_name] = NPCRelationship(
                name=npc['name'],
                relationship="neutral",
                trust_level=0,
                last_interaction="",
                secrets_known=[],
                personal_connection=""
            )
        
        # Create initial plot threads
        initial_threads = []
        for i, plot_point in enumerate(self.campaign_data.get('plot_points', [])[:5]):
            thread = PlotThread(
                id=f"main_plot_{i+1}",
                name=plot_point[:50] + "..." if len(plot_point) > 50 else plot_point,
                status="active" if i == 0 else "dormant",
                importance="main" if i < 3 else "side",
                related_npcs=[],
                related_locations=[],
                player_actions=[],
                next_hooks=[]
            )
            initial_threads.append(thread)
        
        state = CampaignState(
            campaign_name=campaign_name,
            current_act=1,
            current_scene="Opening",
            location="Starting Location",
            session_count=0,
            completed_plot_points=[],
            missed_opportunities=[],
            active_plot_threads=initial_threads,
            npc_relationships=npc_relationships,
            major_decisions=[],
            reputation={},
            custom_hooks=[],
            adaptive_elements=[],
            last_updated=datetime.now().isoformat(),
            notes="Campaign initialized"
        )
        
        await self._save_state()
        return state
    
    async def _load_state_from_file(self) -> CampaignState:
        """Load campaign state from legacy JSON sidecar (import path)."""
        try:
            with open(self.state_file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return self._dict_to_state(data)
        except Exception as e:
            logging.error(f"Failed to load state from file: {e}")
            raise
    
    async def _save_state(self) -> bool:
        """Save current campaign state to Postgres (and JSON sidecar backup)."""
        if not self.current_state:
            return False
        
        try:
            self.current_state.last_updated = datetime.now().isoformat()
            if self.campaign_db_id:
                from .world_state_store import state_dataclass_to_row_fields, upsert_world_state

                fields = state_dataclass_to_row_fields(self.current_state)
                async with async_session_scope() as db:
                    await upsert_world_state(db, self.campaign_db_id, fields)
                logging.info(
                    "Campaign world state saved to Postgres (campaign_id=%s)",
                    self.campaign_db_id,
                )
            # Best-effort JSON backup for offline inspection
            if self.state_file_path:
                try:
                    with open(self.state_file_path, 'w', encoding='utf-8') as f:
                        json.dump(asdict(self.current_state), f, indent=2, ensure_ascii=False)
                except Exception as backup_err:
                    logging.warning("JSON sidecar backup failed: %s", backup_err)
            return True
            
        except Exception as e:
            logging.error(f"Failed to save campaign state: {e}")
            return False

    async def bump_session_count(self) -> bool:
        if not self.current_state:
            return False
        self.current_state.session_count = int(self.current_state.session_count or 0) + 1
        self.current_state.last_updated = datetime.now().isoformat()
        return await self._save_state()

    async def set_location(self, location: str) -> bool:
        if not self.current_state:
            return False
        self.current_state.location = location
        self.current_state.last_updated = datetime.now().isoformat()
        return await self._save_state()

    async def update_plot_thread(
        self,
        thread_id: str,
        status: Optional[str] = None,
        note: Optional[str] = None,
        name: Optional[str] = None,
        create_if_missing: bool = False,
    ) -> bool:
        if not self.current_state:
            return False
        thread = None
        for t in self.current_state.active_plot_threads:
            if t.id == thread_id or t.name.lower() == thread_id.lower():
                thread = t
                break
        if not thread and create_if_missing:
            thread = PlotThread(
                id=thread_id.lower().replace(" ", "_"),
                name=name or thread_id,
                status=status or "active",
                importance="side",
                related_npcs=[],
                related_locations=[],
                player_actions=[],
                next_hooks=[],
            )
            self.current_state.active_plot_threads.append(thread)
        if not thread:
            return False
        if status:
            thread.status = status
        if note:
            thread.player_actions.append(note)
        if name:
            thread.name = name
        if status == "completed" and thread.name not in self.current_state.completed_plot_points:
            self.current_state.completed_plot_points.append(thread.name)
        self.current_state.last_updated = datetime.now().isoformat()
        return await self._save_state()
    
    async def update_player_action(self, action: str, location: str = None) -> bool:
        """Update campaign state based on player action"""
        if not self.current_state:
            return False
        
        try:
            # Update location if provided
            if location:
                self.current_state.location = location
            
            # Add to active plot threads
            for thread in self.current_state.active_plot_threads:
                if thread.status == "active":
                    thread.player_actions.append(action)
            
            # Update timestamp
            self.current_state.last_updated = datetime.now().isoformat()
            
            await self._save_state()
            return True
            
        except Exception as e:
            logging.error(f"Failed to update player action: {e}")
            return False
    
    async def update_npc_relationship(self, npc_name: str, relationship_change: str, trust_delta: int = 0) -> bool:
        """Update relationship with an NPC (creates entry if missing)."""
        if not self.current_state:
            return False
        
        try:
            npc_key = npc_name.lower().replace(' ', '_')
            
            if npc_key not in self.current_state.npc_relationships:
                self.current_state.npc_relationships[npc_key] = NPCRelationship(
                    name=npc_name,
                    relationship="neutral",
                    trust_level=0,
                    last_interaction="",
                    secrets_known=[],
                    personal_connection="",
                )

            npc = self.current_state.npc_relationships[npc_key]
            if relationship_change:
                npc.last_interaction = relationship_change
            npc.trust_level = max(-100, min(100, npc.trust_level + trust_delta))
            
            if npc.trust_level > 50:
                npc.relationship = "trusted"
            elif npc.trust_level > 20:
                npc.relationship = "ally"
            elif npc.trust_level > -20:
                npc.relationship = "neutral"
            elif npc.trust_level > -50:
                npc.relationship = "suspicious"
            else:
                npc.relationship = "enemy"
            
            await self._save_state()
            return True
            
        except Exception as e:
            logging.error(f"Failed to update NPC relationship: {e}")
            return False
    
    def get_campaign_context(self) -> str:
        """Generate context string for AI DM prompting"""
        if not self.current_state or not self.campaign_data:
            return ""
        
        context = f"""
ACTIVE CAMPAIGN: {self.current_state.campaign_name}
CURRENT STATUS: Act {self.current_state.current_act} - {self.current_state.current_scene}
LOCATION: {self.current_state.location}
SESSION: {self.current_state.session_count}

CAMPAIGN OVERVIEW:
{self.campaign_data.get('description', '')}

ACTIVE PLOT THREADS:
"""
        
        for thread in self.current_state.active_plot_threads[:3]:
            if thread.status == "active":
                context += f"- {thread.name} (Status: {thread.status})\n"
        
        context += f"""
KEY NPCs AND RELATIONSHIPS:
"""
        
        for npc_name, npc in self.current_state.npc_relationships.items():
            context += f"- {npc.name}: {npc.relationship} (Trust: {npc.trust_level})\n"
        
        context += f"""
RECENT PLAYER ACTIONS:
"""
        
        # Get recent actions from active threads
        recent_actions = []
        for thread in self.current_state.active_plot_threads:
            recent_actions.extend(thread.player_actions[-2:])  # Last 2 actions per thread
        
        for action in recent_actions[-5:]:  # Last 5 overall actions
            context += f"- {action}\n"
        
        context += f"""
AVAILABLE DECISION POINTS:
"""
        
        for decision in self.campaign_data.get('decision_points', [])[:3]:
            context += f"- {decision}\n"
        
        context += f"""
POTENTIAL PLOT TWISTS:
"""
        
        for twist in self.campaign_data.get('plot_twists', [])[:2]:
            context += f"- {twist}\n"
        
        return context.strip()
    
    def get_adaptive_hooks(self, player_current_action: str) -> List[str]:
        """Generate adaptive story hooks based on player action and campaign state"""
        if not self.current_state or not self.campaign_data:
            return []
        
        hooks = []
        
        # Get relevant NPCs for current situation
        relevant_npcs = []
        for npc_name, npc in self.current_state.npc_relationships.items():
            if npc.relationship in ["trusted", "ally", "suspicious"]:
                relevant_npcs.append(npc)
        
        # Generate hooks based on missed plot points
        for missed in self.current_state.missed_opportunities[-2:]:
            hooks.append(f"An opportunity arises to reconnect with: {missed}")
        
        # Generate hooks based on NPC relationships
        for npc in relevant_npcs[:2]:
            if npc.trust_level > 0:
                hooks.append(f"{npc.name} might have information about your current situation")
            else:
                hooks.append(f"{npc.name} seems to be watching your actions carefully")
        
        return hooks[:3]  # Return top 3 hooks

# Global instance for the bot to use
campaign_state_manager = CampaignStateManager()