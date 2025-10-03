# src/models.py
import datetime
from sqlalchemy import (
    Column,
    Integer,
    String,
    BigInteger,
    TIMESTAMP,
    JSON,
    Boolean,
    Text,
    ForeignKey
)
from sqlalchemy.orm import declarative_base, relationship
from sqlalchemy.dialects.postgresql import JSONB

Base = declarative_base()

class Campaign(Base):
    __tablename__ = 'campaigns'
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), unique=True, nullable=False)
    display_name = Column(String(255), nullable=False)
    description = Column(Text)
    file_path = Column(String(500), nullable=False)
    created_at = Column(TIMESTAMP, default=datetime.datetime.utcnow)
    last_played = Column(TIMESTAMP)
    is_active = Column(Boolean, default=True)

    chat_sessions = relationship("ChatSession", back_populates="campaign")
    summaries = relationship("SessionSummary", back_populates="campaign")

class ChatSession(Base):
    __tablename__ = 'chat_sessions'
    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String(255), unique=True, nullable=False)
    campaign_id = Column(Integer, ForeignKey('campaigns.id'))
    player_name = Column(String(255), default='Player')
    started_at = Column(TIMESTAMP, default=datetime.datetime.utcnow)
    last_activity = Column(TIMESTAMP, default=datetime.datetime.utcnow)
    is_active = Column(Boolean, default=True)

    campaign = relationship("Campaign", back_populates="chat_sessions")
    messages = relationship("ChatMessage", back_populates="session")
    campaign_state = relationship("CampaignState", back_populates="session", uselist=False)
    # characters relationship removed - now using character_models.py

class ChatMessage(Base):
    __tablename__ = 'chat_messages'
    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String(255), ForeignKey('chat_sessions.session_id'))
    message_type = Column(String(20), nullable=False)
    content = Column(Text, nullable=False)
    timestamp = Column(TIMESTAMP, default=datetime.datetime.utcnow)
    metadata_ = Column("metadata", JSONB)

    session = relationship("ChatSession", back_populates="messages")

class CampaignState(Base):
    __tablename__ = 'campaign_state'
    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String(255), ForeignKey('chat_sessions.session_id'))
    current_act = Column(Integer, default=1)
    current_scene = Column(Integer, default=1)
    location = Column(String(255))
    plot_flags = Column(JSONB, default={})
    npc_relationships = Column(JSONB, default={})
    active_plot_threads = Column(JSONB, default=[])
    player_inventory = Column(JSONB, default=[])
    updated_at = Column(TIMESTAMP, default=datetime.datetime.utcnow)

    session = relationship("ChatSession", back_populates="campaign_state")

class SessionSummary(Base):
    __tablename__ = 'session_summaries'
    id = Column(Integer, primary_key=True, autoincrement=True)
    campaign_id = Column(Integer, ForeignKey('campaigns.id'), nullable=False)
    session_number = Column(Integer, nullable=False)
    summary = Column(Text, nullable=False)
    created_at = Column(TIMESTAMP, default=datetime.datetime.utcnow)

    campaign = relationship("Campaign", back_populates="summaries")

# Character class moved to character_models.py for full D&D 5e implementation