# Session Recap — 2026-07-25

**Branch / remote:** `master` @ `88557f5` (pushed to `origin/master`)  
**Env:** `llama_env_311` (Python 3.11); Alienware M18 R2 (i9, 32GB, RTX 4080 mobile 12GB)  
**Product focus:** ASCII browser terminal + local Llama DM. React wood UI archived. Discord deprecated.  
**Prior recap:** [`docs/SESSION_RECAP_2026-07-24.md`](SESSION_RECAP_2026-07-24.md)

---

## What we accomplished

### A–E. Earlier today (through `b4b1db2`)

TOOL_CALL wiring, ASCII UI, rules.db, Phase 4 world memory, GPU OOM / startup fixes, `/playtest` + chat echo — see sections in git history / prior mid-day notes. Baseline commit before the intent/attack arc: `b4b1db2`.

### F. Playtest reliability — tools, cast, clarify (`→ 88557f5`)

| Item | Result |
| :--- | :--- |
| Cast hard-refuse | Fighter Fireball → lookup/consume + fixed refusal; no LLM tavern explosions |
| Spell legality | `consume_spell_slot(..., spell_name=)` validated in engine |
| Clarify-first | Vague `I attack` asks how; pending follow-up (`my sword`) merges |
| ASCII UX | Busy lock, duplicate DM ignore, `/session_start` alias, active PC on session start |
| Chat echo | Skip `user_message` broadcast (client owns “You:”) |

### G. Full attack resolution + inventory weapons

| Item | Result |
| :--- | :--- |
| `resolve_player_attack` | d20+bonus vs object AC, damage, scene object HP (`scene_objects.py`) |
| Template reply | “Rolling attack for you…” — no LLM inventing hit/miss |
| Inventory chooser | `weapon_choose.py` — 0/1/N matches; equipped default; never invent gear |
| Punch vs sword | Body verbs / intent `method=unarmed` must not use Longsword |

### H. Four-layer spine + small Intent LLM (end-state)

| Layer | Role | Implementation |
| :--- | :--- | :--- |
| 1 Intent | Player text → JSON | `player_intent.py` + **`intent_llm.py`** (Qwen 0.5B CPU default) |
| 2 Validate | Allowed? which gear? | `weapon_choose`, spell legality |
| 3 Resolve | Dice / HP / slots | `intent_resolver.py` → `GameActions` |
| 4 Narrate | Flavor only | Attack templates first; DM 8B for soft RP / cast success |

**Rules:** LLM never decides mechanics. Keyword regex demoted (`INTENT_RULES_FALLBACK=false`). Fail closed → clarify. `method=unknown` → ask how.

**Config (local `.env`; `src/config.py` is gitignored):**

```env
INTENT_MODEL_NAME=Qwen/Qwen2.5-0.5B-Instruct
INTENT_DEVICE=cpu
INTENT_TIMEOUT_SEC=12
INTENT_MAX_NEW_TOKENS=80
INTENT_RULES_FALLBACK=false
```

First natural-language line may download the 0.5B model.

**Playtested campaign:** `the_sirens_embrace_a_pirates_odyssey`  
**Default PC:** `Test Fighter` (Longsword equipped in seed)  
**Latency:** Intent CPU ~1–3s target; DM 8B still ≈ 30–90s/reply when narration runs.

---

## Commits (since 2026-07-24 recap)

1. `794fa4c` — Wire local LLM to execute GameActions via TOOL_CALL protocol.
2. `0199b34` — Add ASCII browser terminal and archive React wood UI.
3. `275e288` — Fix async DB sessions and harden flaky pytest suite.
4. `8700183` — Ignore docs/ and stop tracking local session plans.
5. `1d0c3d4` — Add offline rules.db lookups for monsters and equipment.
6. `18972e6` — Add Phase 4 world memory, Alembic, and playtest seed/reset scripts.
7. `1b8cd43` — Fix local play startup and GPU OOM during DM chat.
8. `b4b1db2` — Add /playtest bootstrap and fix ASCII chat echo.
9. **`88557f5` — Add small-LLM intent spine and inventory attack resolution.**

---

## How to get to a playable state (fast path)

```powershell
llama_env_311\Scripts\activate
# once per DB wipe / seed:
python scripts/reset_local_db.py --yes
python scripts/load_rules_from_md.py --fresh   # or seed_test_monsters.py
python scripts/seed_playtest.py --yes --reset --campaign the_sirens_embrace_a_pirates_odyssey

# ensure INTENT_* in .env (see .env.example / README)
$env:DND_PORT=8081   # if 8080 is ghosted
python start_web_system.py
# open http://localhost:8081/  (not 0.0.0.0)
```

In terminal:

```
/playtest
/session start
i punch the table
i swing at the table
i cast fireball
```

Expect: unarmed vs equipped Longsword via engine; Fireball hard-refused for Fighter.

---

## Architecture snapshot (current)

```
Player → ASCII terminal
  /commands → FastAPI → campaign_state / characters / rules.db
  bare chat → WebSocket → DynamicDM
                → IntentLLM (0.5B CPU) → PlayerIntent JSON
                → intent_resolver → GameActions (attack/cast/…)
                → (optional) DM 8B narration from results only
                → Postgres (chat, world state) + SQLite (rules/spells)
```

- **UI:** ASCII is primary (`web/ascii_client/`). React is legacy.
- **LLM:** Small model = interpreter; 8B = narrator. Cloud keys optional for campaign *generation* only.
- **Rules:** `data/rules.db` (monsters/gear) + `data/spells.db`.
- **Memory:** `campaign_world_state` in Postgres; session summaries on `/session end`.
- **Phase 5 (campaign arcs / generator unification):** **on hold** until the play loop is trustworthy.

---

## Starting point for the next AI session

### Read first
1. This recap: `docs/SESSION_RECAP_2026-07-25.md`
2. Prior recap: `docs/SESSION_RECAP_2026-07-24.md`
3. `README.md` (status + INTENT_* env)
4. Local plan (if present): `docs/chat_gpts_plan.md`
5. **Latency eval (2026-07-26):** `docs/LATENCY_EVAL_2026-07-26.md` — ChatGPT idea scorecard, companion-aware budget, phased L1/L2/L3; multi-minute DM replies treated as failures

### Recommended next work (priority order)

1. **Latency (see eval)** — implement Phase L1 then L2 from `docs/LATENCY_EVAL_2026-07-26.md` (4-bit / faster narrator / prompt cuts, then Ollama or llama.cpp adapter). Companions will share the narrator budget later.
2. **Playtest IntentLLM live** — confirm Qwen 0.5B JSON quality on messy lines (`i go for the table`); tune prompt / timeout; watch fail-closed rate.
3. **Stronger grounding** — location / world-state so “where am I?” isn’t a generic tavern loop; encourage `set_location`.
4. **Creature combat path** — `resolve_player_attack` object path is solid; wire more cleanly into active encounter `resolve_attack`.
5. **Phase 5** — held off until play loop feels solid.

### Explicitly deferred
- Campaign generation / arc manager unification
- Growing verb/keyword lists as the primary brain (anti-pattern; use IntentLLM)
- Battle map / grid combat
- Multiplayer sessions
- Persisting scene object HP across restarts (in-memory MVP OK)

### Working rules for next agent
- Prefer extending existing modules over parallel systems.
- Backend is source of truth; IntentLLM parses; engine resolves; DM narrates.
- Use `llama_env_311`; no emojis in project copy.
- Only commit/push when Kyle asks.
- `docs/` is gitignored — keep session recaps local unless asked to track them.
- Do **not** re-expand regex mole-whacking for punch/swing/etc. Fix the interpreter or clarify.

### Verify before claiming done
```
.\llama_env_311\Scripts\python.exe -m pytest tests/test_player_intent.py tests/test_attack_resolve.py tests/test_weapon_choose.py tests/test_tool_executor.py tests/test_spell_legality.py -q
```

---

## Quick “where is X?”

| Need | Look here |
| :--- | :--- |
| Intent schema / parse | `src/player_intent.py` |
| Small intent LLM | `src/intent_llm.py` |
| Intent → GameActions | `src/intent_resolver.py` |
| Inventory weapon pick | `src/weapon_choose.py` |
| Attack parse / reply template | `src/attack_resolve.py` |
| Scene object HP | `src/scene_objects.py` |
| Pending clarify | `src/pending_clarify.py` |
| TOOL_CALL + tool loop | `src/tool_executor.py` |
| AI function implementations | `src/game_actions.py` (`resolve_player_attack`) |
| DM prompt / schemas | `src/dynamic_dm.py` |
| ASCII slash commands | `src/ascii_ui/commands.py` (`/playtest` here) |
| ASCII client / busy lock | `web/ascii_client/terminal.js` |
| World memory store | `src/world_state_store.py`, `src/campaign_state_manager.py` |
| Offline rules DB | `src/rules_db.py`, `scripts/load_rules_from_md.py` |
| Playtest seed | `scripts/seed_playtest.py`, `scripts/fixtures/` |
| App + WebSocket | `web/main.py` |
| Startup | `start_web_system.py` |
| INTENT env docs | `.env.example`, `README.md` |
