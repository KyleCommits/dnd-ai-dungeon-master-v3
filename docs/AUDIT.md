# Architecture Audit Report

## 1. System Overview
The project is a hybrid D&D AI Dungeon Master system with two main interfaces:
- **Legacy Discord Bot**: `start_system.py` / `src/bot.py`.
- **Modern Web System**: `start_web_system.py` / `web/main.py` (FastAPI backend + React frontend).

The core logic resides in `src/`. The web system appears to be the current primary focus.

## 2. Component Completeness Analysis

| Component | File | Status | Notes |
| :--- | :--- | :--- | :--- |
| **Campaign Manager** | `src/campaign_manager.py` | Partial | Handles file-based campaign creation & indexing. Registration in DB needs updating. |
| **Campaign State Mgr**| `src/campaign_state_manager.py` | Complete | Manages dynamic campaign state (NPCs, plots). Used by DynamicDM and Web. |
| **Detailed Campaign Gen**| `src/detailed_campaign_generator.py`| Partial | Intended for campaign generation. Used by bot.py. |
| **Dynamic DM** | `src/dynamic_dm.py` | Complete | Main LLM interaction hub, handles function calling. |
| **Spell System (Legacy)**| `src/spell_system.py` | Partial | Simple dict-based database. Probably deprecated. |
| **Enhanced Spell System**| `src/enhanced_spell_system.py`| Complete | SQLite-backed, full D&D API integration. Used by Web. |
| **Equipment System** | `src/equipment_system.py` | Partial | Defines structures but lacks robust integration in `game_actions.py`. |
| **Game Actions** | `src/game_actions.py` | Partial | Maps LLM functions to game state. Needs expansion to link all systems. |

## 3. Gameplay Loop Trace (Web)
1. **Input**: User sends chat message via WebSocket (`web/main.py:websocket_endpoint`).
2. **Context**: `dynamic_dm.py` retrieves conversation history, session summaries, campaign context.
3. **AI Generation**: `dynamic_dm.py` calls `llm_manager.generate()`, providing `available_functions`.
4. **Action**: If LLM decides to call a function (e.g., `modify_hp`), `game_actions.py` performs the action on the database.
5. **Database**: `src/database.py` handles persistent state updates (HP, session logs).
6. **Response**: DM response is broadcasted via WebSocket to the frontend.

## 4. Architectural Observations & Redundancies

### Campaign Management Redundancy
- `campaign_manager.py`: File-based generation & DB indexing.
- `detailed_campaign_generator.py`: Generates the campaign content.
- `campaign_state_manager.py`: Manages active campaign state (the "what is happening now" aspect).
- **Recommendation**: Align these three. Generator creates, Manager registers/indexes, State Manager tracks progression.

### Spell System Redundancy
- `spell_system.py`: Static dictionary, limited content.
- `enhanced_spell_system.py`: Full API-backed SQLite DB.
- **Conclusion**: `enhanced_spell_system.py` is the clear winner for the future. `spell_system.py` appears to be dead code for the web application.

### Function Calling (`game_actions.py`)
- Currently supports `modify_hp`, `roll_dice`, `apply_condition`, `consume_spell_slot`, `get_character_status`.
- **Missing**: No clear mapping for complex interactions like equipping items, resting mechanics, or tactical positioning.

## 5. Missing Pieces for Playable Solo Campaign
- **Tactical Combat**: Lack of positioning/grid support in `combat_system.py` makes it difficult for the AI DM to run combats beyond narrative descriptions.
- **Full Equipment Loop**: `equipment_system.py` is not yet hooked into `game_actions.py` or character management.
- **Resting Mechanics**: While mentioned, they need a clear implementation to handle HP/spell slot recovery automatically in the DB.
