# D&D AI Dungeon Master

Play D&D 5e without a human DM. The backend is the source of truth for rules and state; a local LLM narrates and drives the story through `TOOL_CALL` → GameActions.

## Goal

Sit down alone, play a long-running campaign, leave, and come back later with continuity (session summaries, NPC trust, plot/location memory).

## What’s working (Phases 1–4)

| Phase | Status | What you get |
|-------|--------|----------------|
| 1 Stabilize core | Done | Chat → tools → game state → narration |
| 2 Playable combat | Done (MVP) | Encounters, initiative, attacks/damage via GameActions |
| 3 Rule integration | Done (MVP) | Offline `rules.db` (monsters/gear) + `spells.db`; `/monster`, `/gear`, lookups |
| 4 Memory | Done (MVP) | Postgres world state, session summaries, Alembic, seed/reset scripts |
| 5 Campaign system | Partial | Generators exist; structured arc tracking still uneven |

### Features in practice

- **ASCII terminal UI** at `http://localhost:8080/` (React wood UI archived under `web/frontend_legacy`)
- **Local LLM** with `TOOL_CALL` / `END_TOOL_CALL` executed by `src/tool_executor.py`
- **Characters**: creation, HP, spells, equipment AC, animal companions
- **Combat**: turn-based encounters; catalog/DB monsters
- **Rules data**: local MD/PDF → SQLite (`data/rules.db`); spells on `data/spells.db`
- **Memory**: session summaries + `campaign_world_state` (NPC trust, plot threads, location)
- **Campaign generation**: multi-stage pipeline (still separate from play-state unification)

## Stack

- **UI**: ASCII browser terminal (FastAPI static + WebSocket chat)
- **API**: FastAPI
- **Postgres**: chat, characters, session summaries, world memory, RAG vectors
- **SQLite**: `data/rules.db`, `data/spells.db`
- **LLM**: local Transformers (primary for play); optional cloud keys for generation
- **Migrations**: Alembic

## Prerequisites

- Python 3.11+ (use `llama_env_311`)
- PostgreSQL with `vector` extension (for RAG)
- Local model path / config as needed in `.env`
- Optional: Gemini / xAI keys for campaign generation

## Quick start

```bash
# Clone and venv
git clone https://github.com/KyleCommits/dnd-ai-dungeon-master-v3.git
cd dungeon_master_discord_bot_v3
python -m venv llama_env_311
llama_env_311\Scripts\activate          # Windows
# source llama_env_311/bin/activate     # Linux/macOS

pip install -r requirements.txt
```

### 1. Configure `.env`

Copy from [`.env.example`](.env.example). Minimum for play:

```env
DATABASE_URL=postgresql+asyncpg://dnd:dnd_local@localhost:5432/dnd_bot_v3
# Discord fields can be placeholders if you only use the web/ASCII UI
DISCORD_TOKEN=unused
BOT_CHANNEL_ID=0
OWNER_ID=0
```

Full Postgres wipe/recreate notes: [`scripts/LOCAL_DB_SETUP.md`](scripts/LOCAL_DB_SETUP.md).

### 2. Fresh database + schema

```bash
# Nuclear: drop/recreate DB, enable vector, alembic upgrade head
python scripts/reset_local_db.py --yes

# Or, if the DB already exists:
alembic upgrade head
```

### 3. Offline rules (monsters / equipment)

Needs local files under `dnd_src_material/rules_and_supplements/` (gitignored).

```bash
python scripts/load_rules_from_md.py --fresh
# Lightweight combat set only:
python scripts/seed_test_monsters.py
```

### 4. Playtest seed (PCs, NPCs + trust, monsters)

```bash
# Soft wipe of play data + reseed (campaign name without .md)
python scripts/seed_playtest.py --yes --reset --campaign <your_campaign>

# Or piecemeal:
python scripts/reset_play_data.py --yes --characters --npcs
python scripts/seed_test_characters.py --campaign <your_campaign>
python scripts/seed_test_npcs.py --campaign <your_campaign>
python scripts/seed_test_monsters.py
```

### 5. Run

```bash
python start_web_system.py
```

Open **http://localhost:8080/**

## Useful ASCII commands

```
/help
/load <campaign>
/status
/chars
/active Test Fighter
/sheet
/npc Mayor Aldric
/monster goblin
/gear longsword
/equip Chain Mail
/session end          # summary + bump session_count
/session start        # auto-summarizes prior open session if needed
/roll 1d20+5
```

Bare text (no `/`) goes to the DM over WebSocket.

## Reset / seed command cheat sheet

| Command | Purpose |
|---------|---------|
| `python scripts/reset_local_db.py --yes` | Drop + recreate Postgres, migrate |
| `python scripts/reset_play_data.py --yes` | Clear sessions/summaries/world state |
| `python scripts/reset_play_data.py --yes --characters --npcs` | Also delete PCs and NPCs |
| `alembic upgrade head` | Apply schema migrations |
| `python scripts/load_rules_from_md.py --fresh` | Rebuild `data/rules.db` from local MD/PDF |
| `python scripts/seed_test_monsters.py` | Upsert goblin/wolf/orc/skeleton |
| `python scripts/seed_test_characters.py` | Test Fighter / Wizard / Cleric |
| `python scripts/seed_test_npcs.py` | Test NPCs + trust in world state |
| `python scripts/seed_playtest.py --yes --reset` | One-shot sandbox + printed cheat sheet |

Destructive scripts require `--yes`.

## Project layout

```
src/
  dynamic_dm.py              # DM brain + tool schemas
  tool_executor.py           # TOOL_CALL execution
  game_actions.py            # Mechanics + memory tools
  combat_system.py           # Encounters / attacks
  rules_db.py                # Offline monsters + equipment
  monster_catalog.py         # rules.db → combat stats
  campaign_state_manager.py  # World memory facade (Postgres)
  world_state_store.py       # campaign_world_state persistence
  ascii_ui/                  # Terminal command handlers + frames
web/
  main.py                    # FastAPI + ASCII static client
  ascii_client/              # Browser terminal
  frontend_legacy/           # Old React UI (archived)
alembic/                     # Schema migrations
scripts/
  LOCAL_DB_SETUP.md
  reset_local_db.py
  reset_play_data.py
  load_rules_from_md.py
  seed_playtest.py
  seed_test_*.py
  fixtures/
data/                        # *.db usually gitignored
dnd_src_material/            # Campaigns + rules (local / gitignored)
tests/
```

## How play works

1. You type an action in the ASCII terminal.
2. The local LLM may emit `TOOL_CALL` blocks.
3. `tool_executor` runs `GameActions` (HP, dice, combat, lookups, NPC trust, location, etc.).
4. State is stored in Postgres / SQLite; the LLM narrates from tool results + memory context.

The AI should not invent HP, AC, damage, or trust when a lookup/tool can supply them.

## Testing

```bash
# Prefer the venv interpreter
llama_env_311\Scripts\python.exe -m pytest tests/test_world_state.py tests/test_rules_db.py tests/test_combat.py tests/test_tool_executor.py tests/test_ascii_ui.py -q
```

## Backlog / limitations

- Campaign manager unification (`campaign_manager` vs `campaign_state_manager` vs generators)
- Enemy AI, concentration, opportunity attacks
- Deeper NPC / arc tracking (Phase 5)
- Single-player focus; no polished multiplayer sessions
- Combat positioning is narrative, not a grid
- React UI is legacy; ASCII is primary

## License

MIT License — free to use and modify. Please attribute if you build on this.

---

Built so you can play D&D without needing another human at the table.
