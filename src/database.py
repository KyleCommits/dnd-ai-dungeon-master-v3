# src/database.py
import logging
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, selectinload
from sqlalchemy.future import select
from sqlalchemy.sql import func
from .config import settings
from .models import Campaign, ChatSession, ChatMessage, SessionSummary, Base
from .character_models import (
    Character, NPC, CharacterAbility, CharacterSkill, CharacterFeature,
    CharacterEquipment, CharacterSpell, UserActiveCharacter,
    CharacterProgression, CharacterDeathSave, CharacterHitDice,
    NPCAbility, NPCSkill
)
from .animal_companion_models import (
    CompanionTemplate, AnimalCompanion, CompanionProgression,
    CompanionAbility, CompanionEquipment
)
import asyncpg
from typing import List, Optional

# fix database url if needed
db_url = settings.DATABASE_URL
if db_url and not db_url.startswith("postgresql+asyncpg://"):
    if db_url.startswith("postgresql://"):
        db_url = db_url.replace("postgresql://", "postgresql+asyncpg://")
        logging.warning(f"Corrected DATABASE_URL to use asyncpg: {db_url}")
    else:
        logging.error(f"Unsupported DATABASE_URL format: {db_url}")
        db_url = None

# create async engine
try:
    if db_url:
        engine = create_async_engine(
            db_url,
            echo=False,
        )
        AsyncSessionLocal = sessionmaker(
            bind=engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )
        logging.info("Database engine and session maker created successfully.")
    else:
        raise ValueError("DATABASE_URL is not set or has an unsupported format.")
except Exception as e:
    logging.error(f"Failed to create database engine: {e}")
    engine = None
    AsyncSessionLocal = None

async def get_db_session():
    if AsyncSessionLocal is None:
        raise ConnectionError("Database is not configured. Cannot create a session.")
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()

async def get_campaign_by_name(db_session: AsyncSession, campaign_name: str) -> Optional[Campaign]:
    search_name = campaign_name if campaign_name.endswith('.md') else f"{campaign_name}.md"
    result = await db_session.execute(
        select(Campaign).where(Campaign.name == search_name)
    )
    return result.scalars().first()

async def get_or_create_chat_session(db_session: AsyncSession, session_id: str, campaign_id: int) -> ChatSession:
    """
    Gets an active chat session, reactivates an inactive one, or creates a new one.
    """
    # see if session already exists
    result = await db_session.execute(
        select(ChatSession).where(ChatSession.session_id == session_id)
    )
    session = result.scalars().first()

    if session:
        # found it, reactivate
        session.is_active = True
        session.last_activity = func.now()
        session.campaign_id = campaign_id # make sure it's linked to current campaign
        await db_session.commit()
        return session
    else:
        # not found, make new one
        new_session = ChatSession(
            session_id=session_id,
            campaign_id=campaign_id,
            is_active=True
        )
        db_session.add(new_session)
        await db_session.commit()
        await db_session.refresh(new_session)
        return new_session

async def create_new_chat_session(db_session: AsyncSession, user_id: str, campaign_id: int) -> ChatSession:
    """
    Creates a new chat session with a unique ID for a fresh start.
    """
    import uuid
    new_session_id = f"{user_id}_{uuid.uuid4().hex[:8]}"

    new_session = ChatSession(
        session_id=new_session_id,
        campaign_id=campaign_id,
        is_active=True
    )
    db_session.add(new_session)
    await db_session.commit()
    await db_session.refresh(new_session)
    return new_session

async def add_chat_message(db_session: AsyncSession, session_id: str, message_type: str, content: str) -> ChatMessage:
    new_message = ChatMessage(session_id=session_id, message_type=message_type, content=content)
    db_session.add(new_message)
    await db_session.commit()
    await db_session.refresh(new_message)
    return new_message

async def get_conversation_history(db_session: AsyncSession, session_id: str, limit: int = 15) -> List[ChatMessage]:
    result = await db_session.execute(
        select(ChatMessage)
        .where(ChatMessage.session_id == session_id)
        .order_by(ChatMessage.timestamp.desc())
        .limit(limit)
    )
    history = result.scalars().all()
    return history[::-1]

async def get_full_conversation_history(db_session: AsyncSession, session_id: str) -> List[ChatMessage]:
    result = await db_session.execute(
        select(ChatMessage)
        .where(ChatMessage.session_id == session_id)
        .order_by(ChatMessage.timestamp.asc())
    )
    return result.scalars().all()

async def get_session_summaries(db_session: AsyncSession, campaign_id: int) -> List[SessionSummary]:
    result = await db_session.execute(
        select(SessionSummary)
        .where(SessionSummary.campaign_id == campaign_id)
        .order_by(SessionSummary.session_number.asc())
    )
    return result.scalars().all()

async def add_session_summary(db_session: AsyncSession, campaign_id: int, summary: str) -> SessionSummary:
    result = await db_session.execute(
        select(func.max(SessionSummary.session_number))
        .where(SessionSummary.campaign_id == campaign_id)
    )
    max_session = result.scalar_one_or_none() or 0
    next_session_number = max_session + 1
    new_summary = SessionSummary(
        campaign_id=campaign_id,
        session_number=next_session_number,
        summary=summary
    )
    db_session.add(new_summary)
    await db_session.commit()
    await db_session.refresh(new_summary)
    logging.info(f"Added summary for session {next_session_number} to campaign {campaign_id}")
    return new_summary

async def get_chat_session_with_campaign(db_session: AsyncSession, session_id: str) -> Optional[ChatSession]:
    result = await db_session.execute(
        select(ChatSession)
        .options(selectinload(ChatSession.campaign))
        .where(ChatSession.session_id == session_id)
    )
    return result.scalars().first()

async def create_tables():
    """create all the database tables including character stuff"""
    if not engine:
        logging.error("Database engine not initialized.")
        return False
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logging.info("Successfully created all database tables.")
        return True
    except Exception as e:
        logging.error(f"Failed to create database tables: {e}")
        return False

async def test_connection():
    if not engine:
        logging.error("Database engine not initialized.")
        return False
    try:
        async with engine.connect() as conn:
            logging.info("Successfully connected to the database.")
            return True
    except asyncpg.exceptions.ConnectionDoesNotExistError as e:
        logging.error(f"Database connection failed: {e}. Please ensure the database server is running and accessible.")
        return False
    except Exception as e:
        logging.error(f"An unexpected database error occurred: {e}")
        return False

if __name__ == '__main__':
    import asyncio
    asyncio.run(test_connection())
