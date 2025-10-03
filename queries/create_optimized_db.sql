-- Optimized D&D AI DM Database Schema
-- Drop and recreate database for fresh start

-- DROP DATABASE IF EXISTS discord_dnd;
-- CREATE DATABASE discord_dnd WITH ENCODING 'UTF8';

\c discord_dnd;

-- Enable vector extension for D&D rules RAG only
CREATE EXTENSION IF NOT EXISTS vector;

-- =====================================================
-- CORE CAMPAIGN MANAGEMENT
-- =====================================================

-- Active campaigns (replaces old empty campaigns table)
CREATE TABLE campaigns (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) UNIQUE NOT NULL,           -- File name: "crimson_conspiracy.md"
    display_name VARCHAR(255) NOT NULL,          -- UI display: "The Crimson Conspiracy"
    description TEXT,
    file_path VARCHAR(500) NOT NULL,             -- Full path to .md file
    created_at TIMESTAMP DEFAULT NOW(),
    last_played TIMESTAMP,
    is_active BOOLEAN DEFAULT true
);

-- =====================================================
-- WEB CHAT SYSTEM (NEW - Core Feature)
-- =====================================================

-- Chat sessions for conversation continuity
CREATE TABLE chat_sessions (
    id SERIAL PRIMARY KEY,
    session_id VARCHAR(255) UNIQUE NOT NULL,     -- Browser session ID
    campaign_id INTEGER REFERENCES campaigns(id),
    player_name VARCHAR(255) DEFAULT 'Player',
    started_at TIMESTAMP DEFAULT NOW(),
    last_activity TIMESTAMP DEFAULT NOW(),
    is_active BOOLEAN DEFAULT true
);

-- Chat messages for conversation memory
CREATE TABLE chat_messages (
    id SERIAL PRIMARY KEY,
    session_id VARCHAR(255) REFERENCES chat_sessions(session_id),
    message_type VARCHAR(20) NOT NULL,           -- 'player' or 'dm'
    content TEXT NOT NULL,
    timestamp TIMESTAMP DEFAULT NOW(),
    metadata JSONB                               -- For future features
);

-- Create index for fast message retrieval
CREATE INDEX idx_chat_messages_session_time ON chat_messages(session_id, timestamp);

-- =====================================================
-- CAMPAIGN STATE TRACKING
-- =====================================================

-- Campaign progression state
CREATE TABLE campaign_state (
    id SERIAL PRIMARY KEY,
    session_id VARCHAR(255) REFERENCES chat_sessions(session_id),
    current_act INTEGER DEFAULT 1,
    current_scene INTEGER DEFAULT 1,
    location VARCHAR(255),
    plot_flags JSONB DEFAULT '{}',
    npc_relationships JSONB DEFAULT '{}',
    active_plot_threads JSONB DEFAULT '[]',
    player_inventory JSONB DEFAULT '[]',
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Session summaries for long-term campaign memory
CREATE TABLE session_summaries (
    id SERIAL PRIMARY KEY,
    campaign_id INTEGER REFERENCES campaigns(id) NOT NULL,
    session_number INTEGER NOT NULL,
    summary TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(campaign_id, session_number)
);

-- =====================================================
-- D&D RULES RAG SYSTEM (ESSENTIAL - KEEP)
-- =====================================================

-- NOTE: The 'dnd_rules' and 'data_dnd_rules' tables for the RAG system
-- are now created and managed automatically by the 'src/rag_setup.py' script
-- using LlamaIndex's PGVectorStore. This ensures the schema matches what the
-- library expects. They are no longer defined manually in this SQL file.

-- =====================================================
-- CHARACTER MANAGEMENT (FUTURE)
-- =====================================================

-- Player character sheets
CREATE TABLE characters (
    id SERIAL PRIMARY KEY,
    session_id VARCHAR(255) REFERENCES chat_sessions(session_id),
    name VARCHAR(255) NOT NULL,
    class VARCHAR(100),
    level INTEGER DEFAULT 1,
    stats JSONB DEFAULT '{}',                   -- STR, DEX, CON, INT, WIS, CHA
    skills JSONB DEFAULT '{}',
    equipment JSONB DEFAULT '[]',
    backstory TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

-- =====================================================
-- UTILITY FUNCTIONS
-- =====================================================

-- Function to clean up old inactive sessions (run periodically)
CREATE OR REPLACE FUNCTION cleanup_old_sessions()
RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    -- Mark sessions inactive if no activity for 24 hours
    UPDATE chat_sessions
    SET is_active = false
    WHERE last_activity < NOW() - INTERVAL '24 hours'
    AND is_active = true;

    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;

-- Function to get conversation history for session
CREATE OR REPLACE FUNCTION get_conversation_history(p_session_id VARCHAR, p_limit INTEGER DEFAULT 20)
RETURNS TABLE(
    message_type VARCHAR,
    content TEXT,
    msg_timestamp TIMESTAMP
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        cm.message_type,
        cm.content,
        cm.timestamp
    FROM chat_messages cm
    WHERE cm.session_id = p_session_id
    ORDER BY cm.timestamp DESC
    LIMIT p_limit;
END;
$$ LANGUAGE plpgsql;

-- =====================================================
-- INITIAL DATA
-- =====================================================

-- Example campaign entry
INSERT INTO campaigns (name, display_name, description, file_path) VALUES
('crimson_conspiracy.md', 'The Crimson Conspiracy', 'A tale of political intrigue in the city', 'dnd_src_material/custom_campaigns/crimson_conspiracy.md');

-- =====================================================
-- MIGRATION NOTES
-- =====================================================

/*
DROPPED TABLES (from old schema):
- All data_dnd_bot_campaign_* tables (~600 MB) - Not used, campaigns loaded from files
- All data_campaign_* tables - Same reason
- campaign_structures - Unused
- message_history - Replaced with chat_messages
- shops, world_state - Unused

KEPT & RENAMED:
- data_dnd_bot_rules → dnd_rules (optimized with categories)

NEW TABLES:
- campaigns - Proper campaign metadata
- chat_sessions - Session management
- chat_messages - Conversation history
- campaign_state - Game state tracking
- characters - Character sheets

BENEFITS:
- 95% smaller database (~50 MB vs 800+ MB)
- Proper conversation memory
- Session persistence
- Optimized for web system
- Clean, focused schema
*/