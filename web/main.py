# web/main.py
import asyncio
import logging
import sys
import os
from typing import List, Dict, Optional, Any
from datetime import datetime
import json

# add parent dir so we can import from src
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from src.dynamic_dm import DynamicDM
from src.campaign_state_manager import campaign_state_manager
from src.llm_manager import llm_manager
from src.config import settings
from src.database import (
    get_db_session,
    get_campaign_by_name,
    get_or_create_chat_session,
    add_chat_message,
    get_full_conversation_history,
    add_session_summary,
    get_session_summaries,
    get_chat_session_with_campaign,
    create_tables
)
from src.dice_roller import dice_roller, AdvantageType
from src.character_manager import character_manager
from src.character_models import Character, NPC
from src.enhanced_spell_system import enhanced_spell_manager
from src.character_creation_api import router as character_creation_router
from src.level_progression import progression_manager
from src.animal_companion_manager import AnimalCompanionManager
from src.animal_companion_models import CompanionTemplate, AnimalCompanion
from web.campaign_routes import campaign_router

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="D&D AI DM", description="AI-powered D&D Dungeon Master API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(campaign_router)
app.include_router(character_creation_router)

if os.path.exists("web/build"):
    app.mount("/static", StaticFiles(directory="web/build"), name="static")

dynamic_dm = DynamicDM()
campaign_manager = campaign_state_manager

@app.on_event("startup")
async def startup_event():
    logger.info("Creating database tables...")
    await create_tables()
    logger.info("Database tables created successfully")

    logger.info("Loading LLM model at startup...")
    llm_manager.load_model()
    logger.info("LLM model preloaded successfully")

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.user_connections: Dict[str, WebSocket] = {}
        self.user_sessions: Dict[str, str] = {}  # user_id -> current_session_id

    async def connect(self, websocket: WebSocket, user_id: str = "player1"):
        await websocket.accept()
        self.active_connections.append(websocket)
        self.user_connections[user_id] = websocket
        # use user_id as session by default
        self.user_sessions[user_id] = user_id

    def disconnect(self, websocket: WebSocket, user_id: str = "player1"):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        if user_id in self.user_connections:
            del self.user_connections[user_id]
        if user_id in self.user_sessions:
            del self.user_sessions[user_id]

    def set_user_session(self, user_id: str, session_id: str):
        self.user_sessions[user_id] = session_id

    def get_user_session(self, user_id: str) -> str:
        return self.user_sessions.get(user_id, user_id)

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            await connection.send_text(message)

manager = ConnectionManager()

class CampaignInfo(BaseModel):
    name: Optional[str] = None
    act: int = 1
    location: str = "Starting Location"
    session: int = 0
    active_npcs: int = 0
    plot_threads: int = 0

class SystemStatus(BaseModel):
    dynamic_dm_loaded: bool
    campaign_loaded: Optional[str]
    campaign_info: Optional[CampaignInfo]
    campaign_id: Optional[int] = None

@app.get("/")
async def root():
    return {"message": "D&D AI DM Backend Running"}

@app.get("/api/status")
async def get_system_status(db: AsyncSession = Depends(get_db_session)):
    campaign_info = None
    campaign_name = None
    campaign_id = None
    if campaign_manager.current_state:
        campaign_name = campaign_manager.current_state.campaign_name
        state = campaign_manager.current_state
        if state:
            # grab campaign id from db
            campaign = await get_campaign_by_name(db, campaign_name)
            campaign_id = campaign.id if campaign else None

            campaign_info = CampaignInfo(
                name=campaign_name,
                act=state.current_act,
                location=state.location,
                session=state.session_count,
                active_npcs=len(state.npc_relationships),
                plot_threads=len(state.active_plot_threads)
            )
    return SystemStatus(
        dynamic_dm_loaded=dynamic_dm is not None,
        campaign_loaded=campaign_name,
        campaign_info=campaign_info,
        campaign_id=campaign_id
    )

@app.post("/api/load_campaign/{campaign_name}")
async def load_campaign(campaign_name: str):
    success = await campaign_manager.load_campaign(campaign_name)
    if success:
        campaign_state = campaign_manager.current_state
        status_message = {
            "type": "system",
            "message": f"Campaign loaded: {campaign_name}. Remember to click 'Start New Session' to begin a fresh session with recap!",
            "timestamp": datetime.now().isoformat(),
            "user_id": "system",
            "campaign_info": {
                "name": campaign_name,
                "act": campaign_state.current_act if campaign_state else 1,
                "location": campaign_state.location if campaign_state else "Starting Location",
                "session": campaign_state.session_count if campaign_state else 0
            }
        }
        await manager.broadcast(json.dumps(status_message))
        return {"success": True, "message": f"Campaign '{campaign_name}' loaded successfully"}
    else:
        raise HTTPException(status_code=400, detail=f"Failed to load campaign '{campaign_name}'")

@app.post("/api/clear_campaign")
async def clear_campaign():
    """Clear the currently loaded campaign"""
    print("DEBUG: clearing campaign")
    try:
        campaign_manager.current_state = None
        status_message = {
            "type": "system",
            "message": "Campaign cleared successfully",
            "timestamp": datetime.now().isoformat(),
            "user_id": "system"
        }
        await manager.broadcast(json.dumps(status_message))
        print("DEBUG: campaign cleared and broadcasted")
        return {"success": True, "message": "Campaign cleared successfully"}
    except Exception as e:
        print(f"ERROR: failed to clear campaign: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to clear campaign: {str(e)}")

@app.post("/api/sessions/start_new")
async def start_new_session(db: AsyncSession = Depends(get_db_session)):
    if not campaign_manager.current_state or not campaign_manager.current_state.campaign_name:
        raise HTTPException(status_code=400, detail="No campaign loaded")

    campaign_name = campaign_manager.current_state.campaign_name
    campaign = await get_campaign_by_name(db, campaign_name)
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    # make new session for current user
    user_id = "player1"
    from src.database import create_new_chat_session
    new_session = await create_new_chat_session(db, user_id, campaign.id)

    # tell connection manager about new session
    manager.set_user_session(user_id, new_session.session_id)

    # let everyone know session changed
    status_message = {
        "type": "session_change",
        "message": "New session started",
        "session_id": new_session.session_id,
        "timestamp": datetime.now().isoformat()
    }
    await manager.broadcast(json.dumps(status_message))

    return {"success": True, "message": "New session started", "session_id": new_session.session_id}

@app.get("/api/campaigns")
async def list_campaigns():
    campaigns_dir = "dnd_src_material/custom_campaigns"
    campaigns = []
    if os.path.exists(campaigns_dir):
        for file in os.listdir(campaigns_dir):
            if file.endswith('.md'):
                campaigns.append(file[:-3])
    return {"campaigns": campaigns}

@app.post("/api/sessions/end/{session_id}")
async def end_session(session_id: str, db: AsyncSession = Depends(get_db_session)):
    try:
        chat_session = await get_chat_session_with_campaign(db, session_id)
        if not chat_session or not chat_session.campaign:
            raise HTTPException(status_code=404, detail="Active session or campaign not found.")

        history = await get_full_conversation_history(db, session_id)
        if not history:
            return {"message": "No history to summarize.", "summary": ""}

        formatted_history = "\n".join([f"{msg.message_type}: {msg.content}" for msg in history])
        
        summary_prompt = f"Summarize the key events, decisions, and outcomes from this D&D session transcript:\n\n{formatted_history}"
        print("DEBUG: generating session summary with gemini...")
        summary_text = await llm_manager.generate(summary_prompt, max_new_tokens=500, use_massive_context=True)
        print(f"DEBUG: got session summary: {summary_text[:100]}...")

        await add_session_summary(db, chat_session.campaign_id, summary_text)

        chat_session.is_active = False
        await db.commit()

        logger.info(f"Session {session_id} ended and summarized successfully.")
        return {"message": "Session ended successfully.", "summary": summary_text}
    except Exception as e:
        logger.error(f"Error ending session {session_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to end session: {str(e)}")

@app.get("/api/campaigns/{campaign_id}/summaries")
async def get_campaign_summaries(campaign_id: int, db: AsyncSession = Depends(get_db_session)):
    """Get all session summaries for a campaign"""
    print(f"DEBUG: getting summaries for campaign {campaign_id}")
    try:
        summaries = await get_session_summaries(db, campaign_id)
        print(f"DEBUG: found {len(summaries)} summaries")

        summary_data = []
        for summary in summaries:
            summary_data.append({
                "id": summary.id,
                "campaign_id": summary.campaign_id,
                "summary": summary.summary,
                "created_at": summary.created_at.isoformat() if summary.created_at else None
            })

        return {"summaries": summary_data, "count": len(summary_data)}
    except Exception as e:
        print(f"ERROR: failed to get summaries: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/current_campaign/summaries")
async def get_current_campaign_summaries(db: AsyncSession = Depends(get_db_session)):
    """Get session summaries for the currently loaded campaign"""
    print("DEBUG: getting summaries for current campaign")
    try:
        if not campaign_manager.current_state or not campaign_manager.current_state.campaign_name:
            raise HTTPException(status_code=400, detail="No campaign currently loaded")

        campaign_name = campaign_manager.current_state.campaign_name
        campaign = await get_campaign_by_name(db, campaign_name)
        if not campaign:
            raise HTTPException(status_code=404, detail="Current campaign not found in database")

        summaries = await get_session_summaries(db, campaign.id)
        print(f"DEBUG: found {len(summaries)} summaries for {campaign_name}")

        summary_data = []
        for summary in summaries:
            summary_data.append({
                "id": summary.id,
                "campaign_id": summary.campaign_id,
                "summary": summary.summary,
                "created_at": summary.created_at.isoformat() if summary.created_at else None
            })

        return {
            "campaign_name": campaign_name,
            "campaign_id": campaign.id,
            "summaries": summary_data,
            "count": len(summary_data)
        }
    except HTTPException:
        raise
    except Exception as e:
        print(f"ERROR: failed to get current campaign summaries: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# dice rolling stuff

class DiceRollRequest(BaseModel):
    dice_count: int = 1
    dice_sides: int = 20
    modifier: int = 0
    advantage: str = "normal"  # "normal", "advantage", "disadvantage"
    description: Optional[str] = None

class SkillRollRequest(BaseModel):
    skill: str
    advantage: str = "normal"

class AbilityRollRequest(BaseModel):
    ability: str
    advantage: str = "normal"

class AbilityCheckRequest(BaseModel):
    ability: str
    advantage: str = "normal"

class CustomDiceRequest(BaseModel):
    notation: str  # e.g., "2d6+3", "1d20", "4d6"
    modifier: int = 0

@app.post("/api/dice/roll")
async def roll_dice(request: DiceRollRequest):
    try:
        advantage_type = AdvantageType(request.advantage)
        result = dice_roller.roll_dice(
            request.dice_count,
            request.dice_sides,
            request.modifier,
            advantage_type,
            request.description
        )

        return {
            "total": result.total,
            "rolls": result.individual_rolls,
            "dropped": result.dropped_rolls,
            "notation": result.dice_notation,
            "modifier": result.modifier,
            "advantage": result.advantage_type.value,
            "description": result.description
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/dice/skill")
async def roll_skill(request: SkillRollRequest, user_id: str = "player1", db: AsyncSession = Depends(get_db_session)):
    try:
        print(f"DEBUG: Skill roll request - skill: {request.skill}, advantage: {request.advantage}, user_id: {user_id}")

        # get active character
        print(f"DEBUG: Campaign manager current state: {campaign_manager.current_state}")
        if not campaign_manager.current_state or not campaign_manager.current_state.campaign_name:
            print("DEBUG: No active campaign")
            raise HTTPException(status_code=400, detail="No active campaign")

        print(f"DEBUG: Looking for campaign: {campaign_manager.current_state.campaign_name}")
        campaign = await get_campaign_by_name(db, campaign_manager.current_state.campaign_name)
        if not campaign:
            print("DEBUG: Campaign not found in database")
            raise HTTPException(status_code=404, detail="Campaign not found")

        print(f"DEBUG: Found campaign {campaign.id}, getting active character for user {user_id}")

        # debug - show all chars for user
        all_characters = await character_manager.get_user_characters(db, user_id, campaign.id)
        print(f"DEBUG: All characters for user {user_id} in campaign {campaign.id}: {[c.name for c in all_characters]}")

        active_character = await character_manager.get_active_character(db, user_id, campaign.id)
        if not active_character:
            print("DEBUG: No active character found")
            # fallback to campaign 1
            print("DEBUG: Trying campaign ID 1 as fallback...")
            all_characters_c1 = await character_manager.get_user_characters(db, user_id, 1)
            print(f"DEBUG: Characters in campaign 1: {[c.name for c in all_characters_c1]}")
            if all_characters_c1:
                active_character = all_characters_c1[0]  # Use first character as fallback
                print(f"DEBUG: Using fallback character: {active_character.name}")
            else:
                raise HTTPException(status_code=400, detail="No active character found")

        print(f"DEBUG: Found active character {active_character.id}, rolling skill check")
        advantage_type = AdvantageType(request.advantage)
        result = await dice_roller.roll_skill_check(active_character.id, request.skill, advantage_type, db)

        print(f"DEBUG: Skill check result: {result}")
        return {
            "total": result.total,
            "rolls": result.individual_rolls,
            "dropped": result.dropped_rolls,
            "notation": result.dice_notation,
            "modifier": result.modifier,
            "advantage": result.advantage_type.value,
            "description": result.description
        }
    except Exception as e:
        print(f"DEBUG: Exception in skill roll: {type(e).__name__}: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/dice/ability")
async def roll_ability(request: AbilityRollRequest, user_id: str = "player1", db: AsyncSession = Depends(get_db_session)):
    try:
        print(f"DEBUG: Generic ability roll request - ability: {request.ability}, advantage: {request.advantage}")

        # get active char or use fake stats
        active_character = None
        try:
            if campaign_manager.current_state and campaign_manager.current_state.campaign_name:
                campaign = await get_campaign_by_name(db, campaign_manager.current_state.campaign_name)
                if campaign:
                    active_character = await character_manager.get_active_character(db, user_id, campaign.id)
        except Exception as e:
            print(f"DEBUG: Could not get active character: {e}")

        if active_character:
            print(f"DEBUG: Using active character {active_character.id}")
            advantage_type = AdvantageType(request.advantage)
            result = await dice_roller.roll_ability_check(active_character.id, request.ability, advantage_type)
        else:
            print(f"DEBUG: No active character, using mock stats")
            advantage_type = AdvantageType(request.advantage)
            result = await dice_roller.roll_ability_check_mock(request.ability, advantage_type)

        return {
            "total": result.total,
            "rolls": result.individual_rolls,
            "dropped": result.dropped_rolls,
            "notation": result.dice_notation,
            "modifier": result.modifier,
            "advantage": result.advantage_type.value,
            "description": result.description
        }
    except Exception as e:
        print(f"ERROR in roll_ability: {type(e).__name__}: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/dice/custom")
async def roll_custom(request: CustomDiceRequest):
    try:
        result = dice_roller.parse_dice_notation(request.notation, request.modifier)

        return {
            "total": result.total,
            "rolls": result.individual_rolls,
            "notation": result.dice_notation,
            "modifier": result.modifier,
            "description": result.description
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# character management endpoints

class CharacterCreateRequest(BaseModel):
    campaign_id: int
    name: str
    race: str
    class_name: str
    background: str
    level: int = 1
    abilities: Dict[str, int]
    skills: Dict[str, bool]
    saving_throws: Dict[str, bool]
    max_hp: int
    armor_class: int
    speed: int = 30
    features: List[Dict[str, Any]] = []
    equipment: List[Dict[str, Any]] = []

class CharacterUpdateRequest(BaseModel):
    name: Optional[str] = None
    current_hp: Optional[int] = None
    max_hp: Optional[int] = None
    armor_class: Optional[int] = None
    level: Optional[int] = None

class NPCCreateRequest(BaseModel):
    campaign_id: int
    name: str
    race: str
    class_name: Optional[str] = None
    level: int = 1
    npc_type: str  # 'ally', 'enemy', 'neutral'
    abilities: Dict[str, int]
    max_hp: int
    armor_class: int
    speed: int = 30

class CompanionCreateRequest(BaseModel):
    character_id: int
    template_id: int
    campaign_id: int
    name: str
    personality_traits: Optional[str] = ""
    backstory: Optional[str] = ""
    notes: Optional[str] = ""

class CompanionHealRequest(BaseModel):
    healing_amount: int

class CompanionDamageRequest(BaseModel):
    damage_amount: int

# spell management models
class SpellSearchRequest(BaseModel):
    level: Optional[int] = None
    school: Optional[str] = None
    class_name: Optional[str] = None
    name_contains: Optional[str] = None
    ritual: Optional[bool] = None
    concentration: Optional[bool] = None

class CastSpellRequest(BaseModel):
    spell_name: str
    slot_level: int

class LearnSpellRequest(BaseModel):
    spell_name: str

@app.get("/api/characters")
async def list_user_characters(user_id: str = "player1", campaign_id: Optional[int] = None, db: AsyncSession = Depends(get_db_session)):
    """Get all characters for a user in a specific campaign."""
    if not campaign_id:
        # get current campaign
        if not campaign_manager.current_state or not campaign_manager.current_state.campaign_name:
            raise HTTPException(status_code=400, detail="No active campaign")

        campaign = await get_campaign_by_name(db, campaign_manager.current_state.campaign_name)
        if not campaign:
            raise HTTPException(status_code=404, detail="Campaign not found")
        campaign_id = campaign.id

    characters = await character_manager.get_user_characters(db, user_id, campaign_id)

    character_list = []
    for char in characters:
        character_list.append({
            "id": char.id,
            "name": char.name,
            "race": char.race,
            "class_name": char.class_name,
            "level": char.level,
            "current_hp": char.current_hp,
            "max_hp": char.max_hp,
            "armor_class": char.armor_class,
            "is_alive": char.is_alive,
            "is_unconscious": char.is_unconscious
        })

    # get active character
    active_character = await character_manager.get_active_character(db, user_id, campaign_id)
    active_character_data = None
    if active_character:
        active_character_data = {
            "id": active_character.id,
            "name": active_character.name,
            "race": active_character.race,
            "class_name": active_character.class_name,
            "level": active_character.level,
            "current_hp": active_character.current_hp,
            "max_hp": active_character.max_hp,
            "armor_class": active_character.armor_class,
            "speed": active_character.speed,
            "is_alive": active_character.is_alive,
            "is_unconscious": active_character.is_unconscious
        }

    return {
        "characters": character_list,
        "active_character": active_character_data
    }

@app.get("/api/characters/{character_id}")
async def get_character_details(character_id: int, db: AsyncSession = Depends(get_db_session)):
    """Get full character details including abilities, skills, equipment."""
    character = await character_manager.get_character_full(db, character_id)
    if not character:
        raise HTTPException(status_code=404, detail="Character not found")

    # put together all character data
    abilities = character.abilities[0] if character.abilities else None
    character_data = {
        "id": character.id,
        "name": character.name,
        "race": character.race,
        "class_name": character.class_name,
        "level": character.level,
        "background": character.background,
        "current_hp": character.current_hp,
        "max_hp": character.max_hp,
        "armor_class": character.armor_class,
        "speed": character.speed,
        "proficiency_bonus": character.proficiency_bonus,
        "is_alive": character.is_alive,
        "is_unconscious": character.is_unconscious,
        "death_save_successes": character.death_save_successes,
        "death_save_failures": character.death_save_failures,
        "abilities": {
            "strength": abilities.strength if abilities else 10,
            "dexterity": abilities.dexterity if abilities else 10,
            "constitution": abilities.constitution if abilities else 10,
            "intelligence": abilities.intelligence if abilities else 10,
            "wisdom": abilities.wisdom if abilities else 10,
            "charisma": abilities.charisma if abilities else 10,
        } if abilities else {},
        "saving_throws": {
            "strength": abilities.str_save_prof if abilities else False,
            "dexterity": abilities.dex_save_prof if abilities else False,
            "constitution": abilities.con_save_prof if abilities else False,
            "intelligence": abilities.int_save_prof if abilities else False,
            "wisdom": abilities.wis_save_prof if abilities else False,
            "charisma": abilities.cha_save_prof if abilities else False,
        } if abilities else {},
        "skills": [
            {
                "name": skill.skill_name,
                "proficient": skill.proficient,
                "expertise": skill.expertise
            } for skill in character.skills
        ],
        "features": [
            {
                "name": feature.feature_name,
                "source": feature.source,
                "description": feature.description
            } for feature in character.features
        ],
        "equipment": [
            {
                "name": item.item_name,
                "quantity": item.quantity,
                "equipped": item.equipped,
                "attuned": item.attuned
            } for item in character.equipment
        ],
        "spells": [
            {
                "name": spell.spell_name,
                "level": spell.spell_level,
                "prepared": spell.prepared,
                "known": spell.known
            } for spell in character.spells
        ]
    }

    return character_data

@app.post("/api/characters")
async def create_character(request: CharacterCreateRequest, user_id: str = "player1", db: AsyncSession = Depends(get_db_session)):
    """Create a new character."""
    try:
        character_data = {
            "campaign_id": request.campaign_id,
            "user_id": user_id,
            "name": request.name,
            "race": request.race,
            "class_name": request.class_name,
            "background": request.background,
            "level": request.level,
            "abilities": request.abilities,
            "skills": request.skills,
            "saving_throws": request.saving_throws,
            "max_hp": request.max_hp,
            "armor_class": request.armor_class,
            "speed": request.speed,
            "features": request.features,
            "equipment": request.equipment
        }

        character = await character_manager.create_character(db, character_data)
        return {"message": "Character created successfully", "character_id": character.id}

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.put("/api/characters/{character_id}")
async def update_character(character_id: int, request: CharacterUpdateRequest, db: AsyncSession = Depends(get_db_session)):
    """Update character details."""
    character = await character_manager.get_character_full(db, character_id)
    if not character:
        raise HTTPException(status_code=404, detail="Character not found")

    if request.name is not None:
        character.name = request.name
    if request.current_hp is not None:
        character.current_hp = min(request.current_hp, character.max_hp)
    if request.max_hp is not None:
        character.max_hp = request.max_hp
    if request.armor_class is not None:
        character.armor_class = request.armor_class
    if request.level is not None:
        character.level = request.level
        character.proficiency_bonus = character_manager.get_proficiency_bonus(request.level)

    await db.commit()
    return {"message": "Character updated successfully"}

@app.post("/api/characters/{character_id}/death-save")
async def roll_death_save(character_id: int, session_id: str = "current", db: AsyncSession = Depends(get_db_session)):
    """Roll a death saving throw for a character."""
    try:
        result = await character_manager.roll_death_save(db, character_id, session_id)
        return result
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/characters/{character_id}/heal")
async def heal_character(character_id: int, hp_amount: int, db: AsyncSession = Depends(get_db_session)):
    """Heal a character by the specified amount."""
    try:
        await character_manager.heal_character(db, character_id, hp_amount)
        return {"message": f"Character healed for {hp_amount} HP"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/characters/{character_id}/set-active")
async def set_active_character(character_id: int, user_id: str = "player1", db: AsyncSession = Depends(get_db_session)):
    """Set a character as the user's active character."""
    character = await character_manager.get_character_full(db, character_id)
    if not character:
        raise HTTPException(status_code=404, detail="Character not found")

    await character_manager.set_active_character(db, user_id, character.campaign_id, character_id)
    return {"message": f"{character.name} is now the active character"}

@app.get("/api/characters/active")
async def get_active_character(user_id: str = "player1", campaign_id: Optional[int] = None, db: AsyncSession = Depends(get_db_session)):
    """Get the user's currently active character."""
    if not campaign_id:
        if not campaign_manager.current_state or not campaign_manager.current_state.campaign_name:
            raise HTTPException(status_code=400, detail="No active campaign")

        campaign = await get_campaign_by_name(db, campaign_manager.current_state.campaign_name)
        if not campaign:
            raise HTTPException(status_code=404, detail="Campaign not found")
        campaign_id = campaign.id

    character = await character_manager.get_active_character(db, user_id, campaign_id)
    if not character:
        return {"active_character": None}

    return {
        "active_character": {
            "id": character.id,
            "name": character.name,
            "race": character.race,
            "class_name": character.class_name,
            "level": character.level,
            "current_hp": character.current_hp,
            "max_hp": character.max_hp
        }
    }

# character dice rolling
@app.post("/api/characters/{character_id}/roll-ability")
async def roll_character_ability(
    character_id: int,
    request: AbilityCheckRequest,
    db: AsyncSession = Depends(get_db_session)
):
    """Roll an ability check for a specific character."""
    try:
        print(f"DEBUG: Roll ability request - character_id: {character_id}, ability: {request.ability}, advantage: {request.advantage}")
        advantage_type = AdvantageType(request.advantage)
        print(f"DEBUG: Advantage type converted: {advantage_type}")
        result = await dice_roller.roll_ability_check(character_id, request.ability, advantage_type, db)
        print(f"DEBUG: Roll result: {result}")
        return {
            "total": result.total,
            "rolls": result.individual_rolls,
            "modifier": result.modifier,
            "advantage": result.advantage_type.value,
            "description": result.description,
            "dropped": result.dropped_rolls
        }
    except Exception as e:
        print(f"DEBUG: Exception in roll_character_ability: {str(e)}")
        print(f"DEBUG: Exception type: {type(e)}")
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/characters/{character_id}/roll-skill")
async def roll_character_skill(
    character_id: int,
    request: SkillRollRequest,
    db: AsyncSession = Depends(get_db_session)
):
    """Roll a skill check for a specific character."""
    try:
        advantage_type = AdvantageType(request.advantage)
        result = await dice_roller.roll_skill_check(character_id, request.skill, advantage_type, db)
        return {
            "total": result.total,
            "rolls": result.individual_rolls,
            "modifier": result.modifier,
            "advantage": result.advantage_type.value,
            "description": result.description,
            "dropped": result.dropped_rolls
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/characters/{character_id}/roll-save")
async def roll_character_save(
    character_id: int,
    request: AbilityCheckRequest,
    db: AsyncSession = Depends(get_db_session)
):
    """Roll a saving throw for a specific character."""
    try:
        print(f"DEBUG: Saving throw request - character_id: {character_id}, ability: {request.ability}, advantage: {request.advantage}")
        advantage_type = AdvantageType(request.advantage)
        result = await dice_roller.roll_saving_throw(character_id, request.ability, advantage_type, db)
        print(f"DEBUG: Saving throw result: {result}")
        return {
            "total": result.total,
            "rolls": result.individual_rolls,
            "modifier": result.modifier,
            "advantage": result.advantage_type.value,
            "description": result.description,
            "dropped": result.dropped_rolls
        }
    except Exception as e:
        print(f"ERROR in roll_character_save: {type(e).__name__}: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))

# npc management for dm
@app.post("/api/npcs")
async def create_npc(request: NPCCreateRequest, db: AsyncSession = Depends(get_db_session)):
    """Create a new NPC (DM only)."""
    try:
        npc_data = {
            "campaign_id": request.campaign_id,
            "name": request.name,
            "race": request.race,
            "class_name": request.class_name,
            "level": request.level,
            "npc_type": request.npc_type,
            "abilities": request.abilities,
            "max_hp": request.max_hp,
            "armor_class": request.armor_class,
            "speed": request.speed
        }

        npc = await character_manager.create_npc(db, npc_data)
        return {"message": "NPC created successfully", "npc_id": npc.id}

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# level up stuff
@app.get("/api/characters/{character_id}/level-up-options")
async def get_level_up_options(character_id: int, db: AsyncSession = Depends(get_db_session)):
    """Get level up options for a character."""
    try:
        character = await character_manager.get_character_full(db, character_id)
        if not character:
            raise HTTPException(status_code=404, detail="Character not found")

        # Get constitution modifier from character abilities
        constitution = 10
        if character.abilities and len(character.abilities) > 0:
            constitution = character.abilities[0].constitution
        con_modifier = max(-5, min(5, (constitution - 10) // 2))

        # Use the progression manager to get level up details
        character_data = {
            "level": character.level,
            "class_name": character.class_name.title(),
            "constitution_modifier": con_modifier
        }

        level_up_details = progression_manager.calculate_level_up(character_data)

        if "error" in level_up_details:
            raise HTTPException(status_code=400, detail=level_up_details["error"])

        # Format features for frontend
        formatted_features = []
        new_level = level_up_details["new_level"]


        for feature in level_up_details.get("new_features", []):
            feature_data = {
                "name": feature["name"],
                "description": feature["description"]
            }

            # Check if this feature has choices (from the enhanced ClassFeature)
            if "choices" in feature and feature["choices"]:
                feature_data["requires_choice"] = True
                feature_data["choice_type"] = feature.get("choice_type", "subclass")
                feature_data["choices"] = feature["choices"]

            formatted_features.append(feature_data)

        return {
            "hp_gain_options": [
                level_up_details["hit_die"],  # roll max
                level_up_details["hp_gain_average"],  # average
                max(1, 1 + con_modifier),  # minimum (1 + con)
                level_up_details["hp_gain_maximum"]  # theoretical max
            ],
            "features": formatted_features,
            "asi_or_feat": level_up_details.get("ability_score_improvement", False),
            "new_level": level_up_details["new_level"],
            "hit_die": level_up_details["hit_die"],
            "con_modifier": con_modifier,
            "proficiency_bonus": level_up_details.get("proficiency_bonus", 2),
            "spell_changes": level_up_details.get("spell_slot_changes", {})
        }

    except Exception as e:
        print(f"Error getting level up options: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get level up options: {str(e)}")

@app.post("/api/characters/{character_id}/level-up")
async def level_up_character(character_id: int, request: dict, db: AsyncSession = Depends(get_db_session)):
    """Process character level up."""
    try:
        character = await character_manager.get_character_full(db, character_id)
        if not character:
            raise HTTPException(status_code=404, detail="Character not found")

        if character.level >= 20:
            raise HTTPException(status_code=400, detail="Character is already at maximum level")

        hp_gain = request.get("hp_gain", 1)
        ability_improvements = request.get("ability_score_improvements", {})
        selected_feat = request.get("selected_feat", "")
        subclass_choices = request.get("subclass_choices", {})

        # Update character level and HP
        new_level = character.level + 1
        new_max_hp = character.max_hp + hp_gain
        new_current_hp = character.current_hp + hp_gain  # Also heal when leveling up

        # Update character in database manually
        character.level = new_level
        character.max_hp = new_max_hp
        character.current_hp = new_current_hp

        # Update abilities if they exist and there are improvements
        if character.abilities and len(character.abilities) > 0 and ability_improvements:
            ability_record = character.abilities[0]
            for ability_name, increase in ability_improvements.items():
                if increase > 0:
                    current_value = getattr(ability_record, ability_name, 10)
                    new_value = min(20, current_value + increase)
                    setattr(ability_record, ability_name, new_value)
                    print(f"Updated {ability_name}: {current_value} -> {new_value}")

        # Add feat to character features if selected
        if selected_feat:
            # This would need to be implemented based on your character features system
            print(f"Character {character.name} selected feat: {selected_feat}")

        # Commit the changes
        await db.commit()
        await db.refresh(character)

        updated_character = character

        print(f"Character {character.name} leveled up to level {new_level}!")
        print(f"HP increased by {hp_gain} (now {new_max_hp})")
        if ability_improvements:
            print(f"Ability improvements: {ability_improvements}")
        if selected_feat:
            print(f"Selected feat: {selected_feat}")

        # Get current abilities for return
        current_abilities = {}
        if updated_character.abilities and len(updated_character.abilities) > 0:
            ability_record = updated_character.abilities[0]
            current_abilities = {
                "strength": ability_record.strength,
                "dexterity": ability_record.dexterity,
                "constitution": ability_record.constitution,
                "intelligence": ability_record.intelligence,
                "wisdom": ability_record.wisdom,
                "charisma": ability_record.charisma
            }

        return {
            "message": f"Character leveled up to level {new_level}!",
            "character": {
                "id": updated_character.id,
                "name": updated_character.name,
                "level": updated_character.level,
                "max_hp": updated_character.max_hp,
                "current_hp": updated_character.current_hp,
                "abilities": current_abilities
            }
        }

    except Exception as e:
        print(f"Error leveling up character: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to level up character: {str(e)}")

# Enhanced dice endpoints that use active character
@app.post("/api/dice/skill-character")
async def roll_skill_with_character(request: SkillRollRequest, user_id: str = "player1", db: AsyncSession = Depends(get_db_session)):
    """Roll a skill check using the active character's stats."""
    try:
        # get active character
        if not campaign_manager.current_state or not campaign_manager.current_state.campaign_name:
            raise HTTPException(status_code=400, detail="No active campaign")

        campaign = await get_campaign_by_name(db, campaign_manager.current_state.campaign_name)
        if not campaign:
            raise HTTPException(status_code=404, detail="Campaign not found")

        character = await character_manager.get_active_character(db, user_id, campaign.id)
        if not character:
            raise HTTPException(status_code=400, detail="No active character")

        advantage_type = AdvantageType(request.advantage)
        result = await dice_roller.roll_skill_check(character.id, request.skill, advantage_type, db)

        return {
            "total": result.total,
            "rolls": result.individual_rolls,
            "dropped": result.dropped_rolls,
            "notation": result.dice_notation,
            "modifier": result.modifier,
            "advantage": result.advantage_type.value,
            "description": result.description,
            "character_name": character.name
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# ============= Animal Companion API Endpoints =============

@app.get("/api/companions/templates")
async def get_companion_templates(companion_type: str = "beast_master", db: AsyncSession = Depends(get_db_session)):
    """Get available companion templates."""
    try:
        companion_manager = AnimalCompanionManager(db)
        await companion_manager.initialize_companion_templates()
        templates = await companion_manager.get_available_companions(companion_type)
        return {"templates": templates}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/companions/templates/{template_id}")
async def get_companion_template(template_id: int, db: AsyncSession = Depends(get_db_session)):
    """Get detailed information about a specific companion template."""
    try:
        template = await db.execute(
            select(CompanionTemplate).where(CompanionTemplate.id == template_id)
        )
        template = template.scalar_one_or_none()

        if not template:
            raise HTTPException(status_code=404, detail="Template not found")

        return {
            "id": template.id,
            "name": template.name,
            "size": template.size,
            "challenge_rating": template.challenge_rating,
            "armor_class": template.armor_class,
            "hit_points": template.hit_points,
            "hit_dice": template.hit_dice,
            "abilities": {
                "strength": template.strength,
                "dexterity": template.dexterity,
                "constitution": template.constitution,
                "intelligence": template.intelligence,
                "wisdom": template.wisdom,
                "charisma": template.charisma
            },
            "speed": {
                "land": template.speed_land,
                "fly": template.speed_fly,
                "swim": template.speed_swim,
                "climb": template.speed_climb,
                "burrow": template.speed_burrow
            },
            "skills": template.skills,
            "special_abilities": template.special_abilities,
            "attacks": template.attacks,
            "environment": template.environment,
            "description": template.description
        }
    except Exception as e:
        print(f"DEBUG: Exception in roll_character_ability: {str(e)}")
        print(f"DEBUG: Exception type: {type(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/companions")
async def create_companion(request: CompanionCreateRequest, db: AsyncSession = Depends(get_db_session)):
    """Create a new animal companion."""
    try:
        companion_manager = AnimalCompanionManager(db)
        result = await companion_manager.create_companion(
            character_id=request.character_id,
            template_id=request.template_id,
            campaign_id=request.campaign_id,
            name=request.name,
            personality_traits=request.personality_traits,
            backstory=request.backstory,
            notes=request.notes
        )

        if not result.get("success"):
            raise HTTPException(status_code=400, detail=result.get("error"))

        return {"message": "Companion created successfully", "companion": result["companion"]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/companions/character/{character_id}")
async def get_character_companions(character_id: int, include_dead: bool = False, db: AsyncSession = Depends(get_db_session)):
    """Get all companions for a character."""
    try:
        companion_manager = AnimalCompanionManager(db)
        companions = await companion_manager.get_character_companions(character_id, include_dead)
        return {"companions": companions}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/companions/{companion_id}")
async def get_companion(companion_id: int, db: AsyncSession = Depends(get_db_session)):
    """Get detailed companion stats."""
    try:
        companion_manager = AnimalCompanionManager(db)
        companion = await companion_manager.get_companion_full_stats(companion_id)

        if "error" in companion:
            raise HTTPException(status_code=404, detail=companion["error"])

        return {"companion": companion}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/companions/{companion_id}/heal")
async def heal_companion(companion_id: int, request: CompanionHealRequest, db: AsyncSession = Depends(get_db_session)):
    """Heal a companion."""
    try:
        companion_manager = AnimalCompanionManager(db)
        result = await companion_manager.heal_companion(companion_id, request.healing_amount)

        if not result.get("success"):
            raise HTTPException(status_code=400, detail=result.get("error"))

        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/companions/{companion_id}/damage")
async def damage_companion(companion_id: int, request: CompanionDamageRequest, db: AsyncSession = Depends(get_db_session)):
    """Apply damage to a companion."""
    try:
        companion_manager = AnimalCompanionManager(db)
        result = await companion_manager.damage_companion(companion_id, request.damage_amount)

        if not result.get("success"):
            raise HTTPException(status_code=400, detail=result.get("error"))

        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/companions/{companion_id}/level-up")
async def level_up_companion(companion_id: int, ranger_level: int, db: AsyncSession = Depends(get_db_session)):
    """Level up a companion based on ranger level."""
    try:
        companion_manager = AnimalCompanionManager(db)
        result = await companion_manager.level_up_companion(companion_id, ranger_level)

        if not result.get("success"):
            raise HTTPException(status_code=400, detail=result.get("error"))

        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/companions/{companion_id}")
async def dismiss_companion(companion_id: int, db: AsyncSession = Depends(get_db_session)):
    """Dismiss/release a companion."""
    try:
        companion_manager = AnimalCompanionManager(db)
        result = await companion_manager.dismiss_companion(companion_id)

        if not result.get("success"):
            raise HTTPException(status_code=400, detail=result.get("error"))

        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ============= Spell Management API Endpoints =============

@app.get("/api/spells/search")
async def search_spells(
    level: Optional[int] = None,
    school: Optional[str] = None,
    class_name: Optional[str] = None,
    name_contains: Optional[str] = None,
    ritual: Optional[bool] = None,
    concentration: Optional[bool] = None
):
    """Search spells with various criteria."""
    print(f"DEBUG: spell search called with params: level={level}, school={school}, class_name={class_name}")
    try:
        # Initialize spell system if needed
        print("DEBUG: initializing spell manager")
        enhanced_spell_manager.initialize()
        print("DEBUG: spell manager initialized")

        search_params = {}
        if level is not None:
            search_params['level'] = level
        if school:
            search_params['school'] = school.lower()
        if class_name:
            search_params['class_name'] = class_name
        if name_contains:
            search_params['name_contains'] = name_contains
        if ritual is not None:
            search_params['ritual'] = ritual
        if concentration is not None:
            search_params['concentration'] = concentration

        print(f"DEBUG: searching spells with params: {search_params}")
        spells = enhanced_spell_manager.search_spells(**search_params)
        print(f"DEBUG: found {len(spells)} spells")

        spell_data = []
        for spell in spells:
            spell_info = {
                "index": spell.index,
                "name": spell.name,
                "level": spell.level,
                "school": spell.school,
                "casting_time": spell.casting_time,
                "range": spell.range,
                "components": spell.components,
                "duration": spell.duration,
                "description": spell.description,
                "ritual": spell.ritual,
                "concentration": spell.concentration,
                "classes": [c.name for c in spell.classes]
            }

            if spell.damage:
                spell_info["damage_type"] = spell.damage.damage_type
                spell_info["damage_at_slot_level"] = spell.damage.damage_at_slot_level

            if spell.saving_throw:
                spell_info["saving_throw"] = {
                    "ability": spell.saving_throw.ability,
                    "success_type": spell.saving_throw.success_type
                }

            if spell.area_of_effect:
                spell_info["area_of_effect"] = {
                    "type": spell.area_of_effect.type,
                    "size": spell.area_of_effect.size
                }

            if spell.higher_level:
                spell_info["higher_level"] = spell.higher_level

            spell_data.append(spell_info)

        print(f"DEBUG: returning {len(spell_data)} spells")
        return {"spells": spell_data, "count": len(spell_data)}
    except Exception as e:
        print(f"ERROR: spell search failed: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/spells/{spell_name}")
async def get_spell_details(spell_name: str):
    """Get detailed information about a specific spell."""
    try:
        enhanced_spell_manager.initialize()
        spell = enhanced_spell_manager.get_spell(spell_name)

        if not spell:
            raise HTTPException(status_code=404, detail="Spell not found")

        spell_data = {
            "index": spell.index,
            "name": spell.name,
            "level": spell.level,
            "school": spell.school,
            "casting_time": spell.casting_time,
            "range": spell.range,
            "components": spell.components,
            "duration": spell.duration,
            "description": spell.description,
            "ritual": spell.ritual,
            "concentration": spell.concentration,
            "classes": [c.name for c in spell.classes],
            "material": spell.material
        }

        if spell.damage:
            spell_data["damage"] = {
                "type": spell.damage.damage_type,
                "at_slot_level": spell.damage.damage_at_slot_level
            }

        if spell.saving_throw:
            spell_data["saving_throw"] = {
                "ability": spell.saving_throw.ability,
                "success_type": spell.saving_throw.success_type
            }

        if spell.area_of_effect:
            spell_data["area_of_effect"] = {
                "type": spell.area_of_effect.type,
                "size": spell.area_of_effect.size
            }

        if spell.higher_level:
            spell_data["higher_level"] = spell.higher_level

        if spell.heal_at_slot_level:
            spell_data["heal_at_slot_level"] = spell.heal_at_slot_level

        return {"spell": spell_data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/characters/{character_id}/spells")
async def get_character_spells(character_id: int, db: AsyncSession = Depends(get_db_session)):
    """Get all spells for a character."""
    try:
        print(f"DEBUG: Getting spells for character ID: {character_id}")
        enhanced_spell_manager.initialize()
        print(f"DEBUG: Spell manager initialized")
        spell_data = await character_manager.get_character_spells(db, character_id)
        print(f"DEBUG: Spell data retrieved: {spell_data is not None}")

        if not spell_data:
            # Character might not be a spellcaster
            return {
                "character_id": character_id,
                "is_spellcaster": False,
                "spells_by_level": {},
                "spell_slots": [],
                "total_spells": 0
            }

        # Format spells for frontend
        formatted_spells = {}
        for level, spell_list in spell_data.get("spells_by_level", {}).items():
            formatted_spells[str(level)] = []
            for spell_info in spell_list:
                spell = spell_info["spell"]
                formatted_spell = {
                    "name": spell.name,
                    "level": spell.level,
                    "school": spell.school,
                    "casting_time": spell.casting_time,
                    "range": spell.range,
                    "components": spell.components,
                    "duration": spell.duration,
                    "description": spell.description,
                    "is_prepared": spell_info["is_prepared"],
                    "is_known": spell_info["is_known"],
                    "times_cast_today": spell_info["times_cast_today"],
                    "ritual": spell.ritual,
                    "concentration": spell.concentration
                }

                if spell.damage:
                    formatted_spell["damage"] = {
                        "type": spell.damage.damage_type,
                        "at_slot_level": spell.damage.damage_at_slot_level
                    }

                formatted_spells[str(level)].append(formatted_spell)

        return {
            "character_id": character_id,
            "character_name": spell_data.get("character_name"),
            "class_name": spell_data.get("class_name"),
            "level": spell_data.get("level"),
            "is_spellcaster": True,
            "caster_type": spell_data.get("caster_type"),
            "spellcasting_ability": spell_data.get("spellcasting_ability"),
            "spellcasting_modifier": spell_data.get("spellcasting_modifier"),
            "spell_save_dc": spell_data.get("spell_save_dc"),
            "spell_attack_bonus": spell_data.get("spell_attack_bonus"),
            "spell_slots": spell_data.get("spell_slots", []),
            "spells_by_level": formatted_spells,
            "total_spells": spell_data.get("total_spells", 0)
        }
    except Exception as e:
        print(f"ERROR in get_character_spells: {type(e).__name__}: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/characters/{character_id}/spells/quick")
async def get_quick_spells(character_id: int, db: AsyncSession = Depends(get_db_session)):
    """Get quick access spells (cantrips + prepared spells) for sidebar."""
    try:
        enhanced_spell_manager.initialize()
        spell_data = await character_manager.get_character_spells(db, character_id)

        if not spell_data.get("is_spellcaster", False):
            return {"is_spellcaster": False, "spell_slots": [], "prepared_spells": [], "cantrips": []}

        # Extract cantrips and prepared spells only
        cantrips = []
        prepared_spells = []

        for level_str, spells in spell_data.get("spells_by_level", {}).items():
            level = int(level_str)
            for spell in spells:
                spell_obj = spell["spell"]  # Get the enhanced spell object
                if level == 0:  # Cantrips
                    cantrips.append({
                        "name": spell_obj.name,
                        "level": spell_obj.level,
                        "school": spell_obj.school,
                        "is_known": spell.get("is_known", False)
                    })
                elif spell.get("is_prepared", False):  # Prepared spells only
                    prepared_spells.append({
                        "name": spell_obj.name,
                        "level": spell_obj.level,
                        "school": spell_obj.school,
                        "is_prepared": True
                    })

        # Sort by level, then name
        cantrips.sort(key=lambda x: x["name"])
        prepared_spells.sort(key=lambda x: (x["level"], x["name"]))

        return {
            "is_spellcaster": True,
            "spell_slots": spell_data.get("spell_slots", []),
            "prepared_spells": prepared_spells[:8],  # Limit to first 8 for UI
            "cantrips": cantrips[:8]  # Limit to first 8 for UI
        }
    except Exception as e:
        print(f"ERROR in get_quick_spells: {type(e).__name__}: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/characters/{character_id}/spells/cast")
async def cast_spell(character_id: int, request: CastSpellRequest, db: AsyncSession = Depends(get_db_session)):
    """Cast a spell for a character."""
    try:
        enhanced_spell_manager.initialize()
        result = await character_manager.cast_spell(db, character_id, request.spell_name, request.slot_level)

        if not result.get("success"):
            raise HTTPException(status_code=400, detail=result.get("error"))

        # Format the response
        spell = result["spell"]
        response_data = {
            "success": True,
            "spell_name": spell.name,
            "slot_level_used": result["slot_level_used"],
            "times_cast_today": result["times_cast_today"],
            "spell_effects": result["spell_effects"]
        }

        # Add damage roll if applicable
        if "damage" in result["spell_effects"]:
            damage_info = result["spell_effects"]["damage"]
            if damage_info.get("dice"):
                # Roll damage dice
                damage_result = dice_roller.parse_dice_notation(damage_info["dice"])
                response_data["damage_roll"] = {
                    "total": damage_result.total,
                    "rolls": damage_result.individual_rolls,
                    "notation": damage_result.dice_notation,
                    "damage_type": damage_info["type"]
                }

        # Add healing roll if applicable
        if "healing" in result["spell_effects"]:
            healing_info = result["spell_effects"]["healing"]
            if healing_info.get("dice"):
                healing_result = dice_roller.parse_dice_notation(healing_info["dice"])
                response_data["healing_roll"] = {
                    "total": healing_result.total,
                    "rolls": healing_result.individual_rolls,
                    "notation": healing_result.dice_notation
                }

        return response_data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/characters/{character_id}/spells/prepare")
async def prepare_spell(
    character_id: int,
    request: dict,
    db: AsyncSession = Depends(get_db_session)
):
    """Prepare or unprepare a spell for a character."""
    try:
        spell_name = request.get("spell_name")
        prepare = request.get("prepare", True)

        if not spell_name:
            raise HTTPException(status_code=400, detail="spell_name is required")

        # Update the preparation status
        result = await character_manager.prepare_spell(db, character_id, spell_name, prepare)

        if not result.get("success"):
            raise HTTPException(status_code=400, detail=result.get("error", "Failed to prepare spell"))

        return {"success": True, "message": f"Spell {'prepared' if prepare else 'unprepared'} successfully"}

    except Exception as e:
        print(f"ERROR in prepare_spell: {type(e).__name__}: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/characters/{character_id}/rest")
async def character_rest(
    character_id: int,
    request: dict,
    db: AsyncSession = Depends(get_db_session)
):
    """Handle character rest (short or long) with spell slot recovery."""
    try:
        rest_type = request.get("rest_type", "long")  # "short" or "long"

        if rest_type not in ["short", "long"]:
            raise HTTPException(status_code=400, detail="rest_type must be 'short' or 'long'")

        result = await character_manager.character_rest(db, character_id, rest_type)

        if not result.get("success"):
            raise HTTPException(status_code=400, detail=result.get("error", "Failed to rest"))

        return result

    except Exception as e:
        print(f"ERROR in character_rest: {type(e).__name__}: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/characters/{character_id}/spells/learn")
async def learn_spell(character_id: int, request: LearnSpellRequest, db: AsyncSession = Depends(get_db_session)):
    """Learn a new spell for a character."""
    try:
        enhanced_spell_manager.initialize()
        result = await character_manager.learn_spell(db, character_id, request.spell_name)

        if not result.get("success"):
            raise HTTPException(status_code=400, detail=result.get("error"))

        spell = result["spell"]
        return {
            "success": True,
            "message": f"Successfully learned {spell.name}",
            "spell": {
                "name": spell.name,
                "level": spell.level,
                "school": spell.school,
                "description": spell.description
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/spells/statistics")
async def get_spell_statistics():
    """Get statistics about the spell database."""
    try:
        enhanced_spell_manager.initialize()
        stats = enhanced_spell_manager.get_spell_statistics()
        return stats
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.websocket("/ws/{user_id}")
async def websocket_endpoint(websocket: WebSocket, user_id: str, db: AsyncSession = Depends(get_db_session)):
    print(f"DEBUG: websocket connection attempt for user {user_id}")
    await manager.connect(websocket, user_id)
    print(f"DEBUG: websocket connected for user {user_id}")
    try:
        while True:
            print(f"DEBUG: waiting for message from {user_id}")
            data = await websocket.receive_text()
            print(f"DEBUG: received data from {user_id}: {data}")
            message_data = json.loads(data)

            if message_data.get("type") == "chat":
                user_message = message_data.get("message", "")
                print(f"DEBUG: processing chat message: {user_message}")

                if not campaign_manager.current_state or not campaign_manager.current_state.campaign_name:
                    print("DEBUG: no campaign state, skipping")
                    continue

                campaign_name = campaign_manager.current_state.campaign_name
                print(f"DEBUG: using campaign: {campaign_name}")
                campaign = await get_campaign_by_name(db, campaign_name)
                if not campaign:
                    print("DEBUG: campaign not found in db")
                    continue

                # Use the current session ID from the connection manager
                current_session_id = manager.get_user_session(user_id)
                print(f"DEBUG: using session id: {current_session_id}")
                chat_session = await get_or_create_chat_session(db, current_session_id, campaign.id)
                print(f"DEBUG: got chat session: {chat_session.session_id}")
                await add_chat_message(db, chat_session.session_id, 'player', user_message)
                print("DEBUG: added player message to db")

                await manager.broadcast(json.dumps({
                    "type": "user_message", "user_id": user_id, "message": user_message,
                    "timestamp": datetime.now().isoformat()
                }))
                print("DEBUG: broadcasted user message")

                print("DEBUG: generating dm response...")
                dm_response = await dynamic_dm.generate_response(user_message, current_session_id)
                print(f"DEBUG: got dm response: {dm_response[:100]}...")

                await add_chat_message(db, chat_session.session_id, 'dm', dm_response)
                print("DEBUG: added dm message to db")

                await manager.broadcast(json.dumps({
                    "type": "dm_response", "user_id": "DM", "message": dm_response,
                    "timestamp": datetime.now().isoformat()
                }))
                print("DEBUG: broadcasted dm response")

    except WebSocketDisconnect:
        print(f"DEBUG: websocket disconnect for {user_id}")
        manager.disconnect(websocket, user_id)
    except Exception as e:
        print(f"ERROR: websocket error for user {user_id}: {e}")
        import traceback
        traceback.print_exc()
        manager.disconnect(websocket, user_id)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080, reload=True)
