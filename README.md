# D&D AI Dungeon Master

Play D&D 5e **without a human DM**. The backend is the source of truth for rules and state; a local LLM narrates and (increasingly) drives mechanics through `TOOL_CALL` → GameActions.

## Goal

Sit down alone, play a long-running campaign, leave, and come back later with continuity (session summaries, NPC trust, plot/location memory).

## Status (2026-07)

### Phases

| Phase | Status | Notes |
|-------|--------|--------|
| 1 Stabilize core | Done (MVP) | Chat → tools → state → narration path exists |
| 2 Playable combat | Done (MVP) | Encounters, initiative, attacks/damage via GameActions |
| 3 Rule integration | Done (MVP) | Offline `rules.db` + `spells.db`; `/monster`, `/gear`, lookups |
| 4 Memory | Done (MVP) | Postgres `campaign_world_state`, session summaries, Alembic, seeds |
| 5 Campaign system | **On hold** | Generators exist; structured arcs deferred until play loop is trustworthy |

### What works (playtested)

- **ASCII browser terminal** as primary UI (`python start_web_system.py` → `http://localhost:<port>/`)
- **Local Mistral 7B** DM replies (4-bit BitsAndBytes on RTX 4080 mobile 12GB; Llama 3.1 8B still selectable via `.env`)
- **Campaign load** + **character select** (`/load`, `/chars`, `/active`, `/sheet`)
- **Playtest sandbox**: seed PCs / NPCs+trust / monsters; reset DB / play data
- **Offline rules**: MD/PDF → `data/rules.db` (~250 monsters, equipment tables)
- **Memory plumbing**: session end summaries, world-state tools (trust, location, plot) wired
- **Startup hardening**: prefers `llama_env_311`, `/api/health`, main-thread CUDA load, prompt truncation to avoid GPU OOM

### Known gaps / TODOs (priority order)

**Next (playtest polish — do before Phase 5):**

1. **Tool compliance (MVP shipped)** — TOOL_CALL harden + cast legality; **clarify-first intent** (vague `I attack` asks how; does not invent outcomes). Still playtest richer AUTO resolves after clarification.
2. **Stronger grounding** — force `set_location` / world-state context so “where am I?” isn’t a generic tavern loop
3. **Latency (L1 in progress)** — default narrator is Mistral 7B 4-bit + tighter prompts; target soft-RP under ~15–20s. See `docs/LATENCY_EVAL_2026-07-26.md`. L2 (Ollama/llama.cpp) next if still slow.

**Later:**

4. **Phase 5 campaign system** — structured arcs, `major_decisions`, generator → play-state seeding (held off)
5. Campaign manager unification (`campaign_manager` vs `campaign_state_manager` vs generators)
6. Enemy AI, concentration, opportunity attacks
7. Multiplayer sessions; battle-map grid (intentionally narrative for now)

### Performance note (local GPU)

On an **Alienware-class laptop (e.g. i9, 32GB RAM, RTX 4080 mobile 12GB VRAM)**, local 7B/8B chat is playable but not instant. VRAM limits model/context size; reply time is mostly GPU decode + prompt size. L1 defaults: Mistral-7B-Instruct-v0.3 in 4-bit, smaller context, `generate_ms` logs. Multi-minute replies are treated as failures.

## Stack

- **UI**: ASCII terminal (FastAPI + WebSocket); React wood UI in `web/frontend_legacy` (deprecated)
- **API**: FastAPI
- **Postgres**: chat, characters, summaries, world memory, RAG vectors
- **SQLite**: `data/rules.db`, `data/spells.db`
- **LLM**: local Transformers (play); optional cloud keys for campaign *generation* only
- **Migrations**: Alembic

## Prerequisites

- Python **3.11** via `llama_env_311` (system Python 3.13 will break deps)
- PostgreSQL + `vector` extension
- Local Hugging Face model in `.env` (`LOCAL_MODEL_NAME`, `LOCAL_LOAD_IN_4BIT` / `LOCAL_QUANTIZATION`)
- Hugging Face login for gated models: accept license on the model page, then `huggingface-cli login`
- Optional: Gemini / xAI for campaign generation (not required for play)

## Quick start

```bash
git clone https://github.com/KyleCommits/dnd-ai-dungeon-master-v3.git
cd dungeon_master_discord_bot_v3

python -m venv llama_env_311
llama_env_311\Scripts\activate          # Windows
# source llama_env_311/bin/activate     # Linux/macOS

pip install -r requirements.txt
```

### 1. Configure `.env`

Copy [`.env.example`](.env.example). Minimum for play:

```env
DATABASE_URL=postgresql+asyncpg://dnd:dnd_local@localhost:5432/dnd_bot_v3
DISCORD_TOKEN=unused
BOT_CHANNEL_ID=0
OWNER_ID=0
LOCAL_MODEL_NAME=mistralai/Mistral-7B-Instruct-v0.3
LOCAL_LOAD_IN_4BIT=true
LOCAL_QUANTIZATION=4bit
INTENT_MODEL_NAME=Qwen/Qwen2.5-1.5B-Instruct
INTENT_DEVICE=cpu
```

Intent parsing uses a small local model (default Qwen 1.5B on CPU) that outputs JSON only — including `repeat_last` and NPC name hints. The 7B narrator (4-bit) handles soft RP; the engine resolves combat/spells and validates attack targets against world state (NPC vs object). Prefetch: `huggingface-cli download mistralai/Mistral-7B-Instruct-v0.3` and `Qwen/Qwen2.5-1.5B-Instruct`.

Postgres setup: [`scripts/LOCAL_DB_SETUP.md`](scripts/LOCAL_DB_SETUP.md).

### 2. Database

```bash
python scripts/reset_local_db.py --yes
# or: alembic upgrade head
```

### 3. Offline rules

Needs `dnd_src_material/rules_and_supplements/` (local / gitignored).

```bash
python scripts/load_rules_from_md.py --fresh
# or light combat set:
python scripts/seed_test_monsters.py
```

### 4. Playtest seed

```bash
# Campaign name = filename without .md under custom_campaigns/
python scripts/seed_playtest.py --yes --reset --campaign the_sirens_embrace_a_pirates_odyssey
```

### 5. Run (ASCII UI)

```bash
# Always use the venv. Prefer localhost, not 0.0.0.0, in the browser.
python start_web_system.py
```

Open **http://localhost:8080/**  

If port 8080 is stuck on Windows:

```powershell
$env:DND_PORT=8081
python start_web_system.py
# then http://localhost:8081/
```

`start_system.py` is the **legacy Discord** entrypoint (deprecated) — use `start_web_system.py`.

Optional: `DND_UVICORN_RELOAD=1` for auto-reload (off by default).

## Play loop (ASCII)

```
/help
/playtest                 # load default campaign + Test Fighter
/sheet
/npc Mayor Aldric
/monster goblin
/gear longsword
/session end
/roll 1d20+5
```

Then type **normal text** (no `/`) to talk to the DM, e.g. `I look around the inn and greet Mira.`

## Reset / seed cheat sheet

| Command | Purpose |
|---------|---------|
| `python scripts/reset_local_db.py --yes` | Drop + recreate Postgres, migrate |
| `python scripts/reset_play_data.py --yes` | Clear sessions / summaries / world state |
| `python scripts/reset_play_data.py --yes --characters --npcs` | Also delete PCs and NPCs |
| `alembic upgrade head` | Apply schema migrations |
| `python scripts/load_rules_from_md.py --fresh` | Rebuild `data/rules.db` |
| `python scripts/seed_playtest.py --yes --reset --campaign <name>` | Full sandbox + cheat sheet |

Destructive scripts require `--yes`.

## Project layout

```
src/
  dynamic_dm.py              # DM brain + tool schemas
  tool_executor.py           # TOOL_CALL execution
  game_actions.py            # Mechanics + memory tools
  combat_system.py
  rules_db.py / monster_catalog.py
  campaign_state_manager.py  # Play-state facade
  world_state_store.py       # Postgres campaign_world_state
  ascii_ui/
web/
  main.py                    # FastAPI + ASCII client
  ascii_client/
  frontend_legacy/           # Old React UI
alembic/
scripts/                     # DB reset, rules load, playtest seeds
dnd_src_material/            # Campaigns + rules (local)
tests/
```

## How play works

1. You type in the ASCII terminal.
2. Slash commands update state via the API; bare text goes to the DM over WebSocket.
3. The local LLM may emit `TOOL_CALL` blocks; `tool_executor` runs `GameActions`.
4. Postgres / SQLite hold truth; the LLM narrates from tool results + truncated campaign/memory context.

## Testing

```bash
llama_env_311\Scripts\python.exe -m pytest tests/test_world_state.py tests/test_rules_db.py tests/test_combat.py tests/test_tool_executor.py tests/test_ascii_ui.py -q
```

## License

MIT License — free to use and modify. Please attribute if you build on this.

---

Built so you can play D&D without needing another human at the table.
