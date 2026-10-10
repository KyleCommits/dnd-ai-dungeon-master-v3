# 🧠 AI D&D System — Master Objective & Build Plan

## 🎯 CORE GOAL

Build a fully playable, AI-driven Dungeons & Dragons (5e-style) experience where:

- A single player can play a long-running campaign
- The AI acts as the Dungeon Master (DM)
- The system enforces rules, tracks state, and maintains continuity
- Campaigns can persist across many sessions (like real D&D)

This is NOT just a chatbot.

This is a:
> Persistent, stateful, AI-driven game engine

---

## 🧩 WHAT SUCCESS LOOKS LIKE

A player can:

1. Create a character
2. Enter a generated campaign
3. Take actions (talk, explore, fight, cast spells)
4. Have the AI respond as a DM
5. Engage in structured combat
6. Gain items, XP, and progress
7. Leave and return later
8. Continue the SAME world with memory intact

---

## CURRENT STATE (updated 2026-07)

Shipped relative to the original audit:

- FastAPI backend + ASCII browser terminal (primary UI); React moved to `web/frontend_legacy`
- DynamicDM + local LLM `TOOL_CALL` → `tool_executor` → GameActions
- Phase 2 combat: encounters, initiative, `resolve_attack`, combat GameActions
- Phase 3 rules data (offline): `scripts/load_rules_from_md.py` → `data/rules.db` (monsters + equipment); spells remain on `data/spells.db`
- Lookups: `get_monster` / `get_item` / `lookup_*` GameActions; ASCII `/monster` `/gear` `/equip` `/unequip`

Still open / lighter:

- Campaign manager unification (backlog)
- Enemy AI, concentration, opportunity attacks
- Deeper NPC relationship / arc tracking

---

## 🧠 CORE ARCHITECTURE (TARGET)

The system must be structured into 5 layers:

### 1. UI Layer (ASCII terminal primary; React legacy)
- Displays game state
- Accepts player input / slash commands

### 2. Game Engine (FastAPI)
- Source of truth
- Stores:
  - Player state
  - World state
  - Combat state

### 3. Rules Engine
- Handles:
  - Combat math
  - Spell effects
  - Dice rolls
- Uses structured data (NOT raw markdown prompts)

### 4. AI DM (DynamicDM)
- Interprets player intent
- Decides what happens next
- Calls tools (game_actions)

### 5. Memory System
- Stores:
  - Session summaries
  - NPCs
  - Player decisions
- Enables long campaigns

---

## 🔄 CORE GAME LOOP (CRITICAL)

This loop MUST work before expanding features:

1. Player sends input  
   ("I attack the goblin")

2. System parses intent  
   → action = "attack"

3. Game engine validates action  
   → is target valid?

4. Rules engine resolves outcome  
   → roll dice, calculate damage

5. Game state updates  
   → HP reduced, enemy reacts

6. AI DM narrates result  
   → "Your blade cuts deep..."

7. Loop continues

---

## 🧱 REQUIRED SYSTEMS (MVP)

To be playable, the following must exist:

### 1. Character System
- Stats (HP, AC, abilities)
- Inventory
- Level progression

### 2. Combat System
- Turn order
- Attack rolls
- Damage calculation
- Enemy AI

### 3. Spell System
- Spell lookup
- Effects resolution

### 4. Equipment System
- Items
- Equip/unequip
- Stat modifiers

### 5. Campaign System
- Locations
- Quests
- NPCs

### 6. Memory System
- Persistent world state
- Session continuity

---

## BACKLOG CLEANUP

1. Merge duplicate campaign systems
2. Keep a single spell path (`enhanced_spell_system` + `spells.db`)
3. Remove remaining redundant managers where safe

---

## BUILD PHASES

### PHASE 1 — STABILIZE CORE (DONE)
- Actions → tools → game state → narration path works (local LLM + GameActions)

### PHASE 2 — PLAYABLE COMBAT (DONE for MVP)
- Turn-based encounters, attacks, damage; enemy AI still thin

### PHASE 3 — RULE INTEGRATION (DONE for MVP)
- Local MD/PDF under `dnd_src_material/rules_and_supplements` → offline `data/rules.db`
- Regenerate: `python scripts/load_rules_from_md.py --fresh`
- Lookups: `get_spell()` (`spells.db`), `get_monster()` / `get_item()` (`rules.db`)
- ASCII + GameActions read-only `lookup_*`; combat/equip prefer DB rows

### PHASE 4 — MEMORY (DONE for MVP)
- Alembic migrations (`alembic upgrade head`); local reset docs in `scripts/LOCAL_DB_SETUP.md`
- Campaign world state in Postgres (`campaign_world_state`): NPC trust, plot threads, location, session_count
- GameActions: `update_npc_relationship`, `update_plot_thread`, `set_location`, `record_plot_event`
- `/session end` writes summary + bumps session_count; `/session start` auto-summarizes prior open session
- Playtest scripts: `reset_play_data.py`, `reset_local_db.py`, `seed_playtest.py` (+ character/NPC/monster seeds)

### PHASE 5 — CAMPAIGN SYSTEM (PARTIAL)
- Generators exist; structured arc tracking still uneven

---

## 🤖 AI RESPONSIBILITIES

The AI DM should:

DO:
- Interpret player intent
- Narrate outcomes
- Choose enemy actions
- Drive story forward

DO NOT:
- Invent rules
- Track raw game state
- Replace the game engine

---

## 🧠 IMPORTANT DESIGN RULES

1. AI is NOT the source of truth  
   → The backend is

2. Rules must be deterministic  
   → No guessing spell effects

3. State must persist  
   → Every session builds on the last

4. Systems must be unified  
   → No duplicate managers

---

## 🛠️ HOW TO WORK ON THIS PROJECT (FOR AI BUILDERS)

When making changes:

1. Read AUDIT.md first
2. Identify duplication before adding new code
3. Prefer extending existing systems over creating new ones
4. Keep logic inside the game engine, not the AI
5. Ensure every feature fits into the core game loop

---

## NEXT TASK (BACKLOG)

Unify the campaign systems (not blocking the play loop):

- campaign_manager
- campaign_state_manager
- detailed_campaign_generator

Goal: ONE consistent campaign system

---

## 🧭 END GOAL

A system where:

- The player can play indefinitely
- The AI behaves like a real DM
- The world evolves over time
- The experience feels like real D&D
