# Project state — 2026-10-10

Snapshot taken when restarting work on the Dell Inspiron 7405 2-in-1. Analysis was
read-only: no tests were run (no venv or Postgres on this machine yet).

## TL;DR

Working single-player prototype that plays end to end on the Alienware. The core
architecture is sound and the intent pipeline is the strongest part. What stands
between it and "fun to play" is latency, deterministic handling of non-combat
actions, location grounding, and cleanup — not more features.

## Size and activity

- ~19,900 lines in `src/`, ~1,500 in `web/main.py`, ~1,400 in `scripts/`,
  ~4,000 in `tests/` (201 test functions).
- 31 commits. Oct 2025 = original Discord bot. All real progress happened
  2026-07-24 → 2026-07-27. Untouched since. Clean tree, in sync with `origin/master`.
- Last 10 commits are all intent work (embedding classifier, slot filling, eval
  harness, margin calibration).

## Phase status (from README)

| Phase | Status |
|-------|--------|
| 1 Stabilize core | Done (MVP) |
| 2 Playable combat | Done (MVP) |
| 3 Rule integration | Done (MVP) |
| 4 Memory | Done (MVP) |
| 5 Campaign system | On hold until the play loop is trustworthy |

## How a turn works

All in `run_tool_loop` (`src/tool_executor.py`):

1. Pending clarification answer is merged, otherwise the embedding classifier labels
   the text (attack / cast / speak / rest / move / use_item / roll / repeat_last).
2. **speak** → short narration prompt with tool instructions stripped (fixed the
   90 s "hello" replies). Output is filtered; anything claiming dice/damage is
   replaced with a safe line.
3. **attack / cast** → resolved by the engine (`resolve_intent`) *before* the LLM.
   The LLM only narrates real results.
4. **everything else** (rest, move, use_item, checks) → full prompt; the LLM must
   emit a `TOOL_CALL` itself (max 2 rounds, 160 tokens).

Prompt context: compact world state (location, NPC trust, plot), session summaries,
campaign excerpt capped at 3,500 chars.

Current stack: Mistral 7B 4-bit (Transformers + BitsAndBytes, CUDA) narrator;
MiniLM-L6 kNN intent classifier over `data/intent/examples.jsonl` (292 rows),
held-out eval `tests/data/intent_eval.jsonl` (58 rows); Postgres + pgvector;
SQLite `rules.db` / `spells.db`; ASCII web terminal.

## What's solid

- Engine-is-authority is enforced for attack/cast: LLM never decides hit, damage,
  or slots. Spell legality checked.
- Intent pipeline: labeled data, held-out eval, measured mechanics margin
  (`INTENT_MECHANICS_MARGIN=0.02`), cache validation, documented rule "fix misreads
  with data, not keywords".
- Postgres memory with Alembic migrations; seed/reset scripts; `/playtest`.
- Offline rules lookups with in-code fallbacks.

## Weaknesses

1. **Only attack and cast are deterministic.** Rest, move, use_item and checks
   depend on the 7B emitting the right tool call. `resolve_intent`
   (`src/intent_resolver.py`) returns `handled=False` for them. This is also why
   location grounding is weak — `set_location` only fires if the LLM remembers.
2. **Overlapping intent layers.** Legacy keyword tiers (`classify_player_intent` in
   `mechanics_claims.py`), the embed classifier, `intent_from_rules`, regex bridges
   (`last_attack.py`, `pending_clarify.py`), and the `prose_claims_mechanics` output
   filter. Comments still call IntentLLM "primary" and `parse_player_intent` is
   called with `use_intent_llm=True`. Contradicts the README's "keyword lists were
   replaced" in places.
3. **~2,000 lines not imported by the live web path:** `bot.py`,
   `detailed_campaign_generator.py`, `analyze_structures.py`,
   `additional_class_features.py`, `character_calculator.py`,
   `llm_manager_dialogpt_test.py`, `setup_indexes.py`, `sync_campaigns.py`.
   Plus Discord-era tests (`test_discord_connection.py`, `test_send_message.py`) and
   `web/frontend_legacy/`.
4. **Large files:** `detailed_character_creator.py` (2,825, still live via
   `character_creation_api`), `web/main.py` (1,494, routes + websocket + startup).
   Three overlapping campaign modules (`campaign_manager`, `campaign_state_manager`,
   generators).
5. **Single-player by construction.** Global `campaign_state_manager`; last-attack
   and pending-clarify memory are in-process dicts (10 min TTL) and lost on restart.
6. **Machine-bound setup.** `requirements.txt` pins `torch==2.1.2`,
   `transformers==4.37`, `bitsandbytes` → needs Python 3.11 + NVIDIA GPU. Narrator
   is Transformers-only (`llm_manager.py`, local-only policy, no Gemini for chat).
   `docs/` is gitignored, so `docs/LATENCY_EVAL_2026-07-26.md` did not come over.
   Source books and campaign files are not in git.

## Gaps vs. the goal (play solo, leave, return with continuity)

Pieces exist (memory, summaries, trust, rules, combat). Missing:

- Speed: ~15–20 s replies at best on the Alienware; L2 (Ollama/llama.cpp) not started.
- Engine-resolved non-combat actions.
- Grounded location / scene state.
- A tested vertical slice; no campaign content work (Phase 5 on hold).

## Evaluation of the "Local LLM Summary" (external advice)

Right:
- 12 GB VRAM is enough; 12–14B 4-bit is a sensible next narrator; 27B+ impractical.
- Vertical slice next. No new hardware needed.
- Dell RAM really is 24 GB (23.4 GB usable).

Wrong or stale:
- **Intent:** recommends a fine-tuned 0.8–2B decision model — that's what the
  project moved *away* from. The Qwen 1.5B backend has no mechanics gate. Only
  revisit if `scripts/eval_intent.py` shows kNN plateauing, and any replacement must
  produce a calibrated margin.
- **"Wire equipment and resting":** already wired as `/rest`, `/equip`, `/unequip`
  and LLM tools (`trigger_rest`, `equip_item`, `update_inventory`). Real gap is
  engine-resolved natural-language rest/use_item (weakness 1).
- **Ignores latency and grounding**, the README's top open problems. A 12–14B model
  on Transformers + BitsAndBytes would be *slower*; move to llama.cpp/Ollama first.
- **Embeddings swap:** pgvector schema is 384-dim (MiniLM). EmbeddingGemma outputs
  768 (Matryoshka 512/256/128), never 384 → migration + re-embed. "EmbeddingGemma 2"
  and its size figures unverified.
- **Model news:** "Unsloth decision models" isn't a product (Unsloth is a fine-tune
  library). BitNet.cpp only runs natively ternary-trained models. Sub-1-bit
  (LittleBit) loses a lot of quality. Not actionable.
- **Pixel offline mode:** state lives in server Postgres; on-device intent gains
  nothing. Use the existing web UI over LAN/Tailscale.
- **Gemini narration** contradicts the local-only policy and needs code changes.

## Dell Inspiron 7405 2-in-1 (Ryzen 5 4500U, 23.4 GB, Radeon iGPU)

Present: Python 3.14, git, winget. Missing:

- Python 3.11 + `llama_env_311` (pins won't install on 3.14).
- Postgres with pgvector (no Docker either; `pgvector/pgvector:pg16` via Docker
  Desktop is easiest on Windows).
- `.env` (copy `.env.example`; Discord fields can be dummies).
- ~~`dnd_src_material/`~~ — copied from the Alienware (see update below).
- `data/rules.db` — not built yet; sources are now present, run
  `scripts/load_rules_from_md.py --fresh`.
- `data/spells.db` — `scripts/load_spells.py` pulls from the public 5e API (no books).
- Intent classifier works as-is (data is in git; MiniLM downloads, CPU is fine).
- Model weights — none. `llm_models/` only has `llama_urls.txt` (Meta signed
  download links, expired 2025-07-23). On the Alienware the weights live in the
  Hugging Face cache (`%USERPROFILE%\.cache\huggingface`), not in the repo.

### Venv

The Alienware `llama_env_311` (~10 GB, mostly CUDA torch) was not copied and
shouldn't be — Windows venvs embed absolute paths. Build a fresh one:

- `requirements.txt` is stale (`torch==2.1.2`, `transformers==4.37`).
  `requirements_working.txt` is the real Alienware freeze (`torch==2.5.1+cu121`,
  `transformers==4.56.1`, `accelerate==1.10.1`, `bitsandbytes==0.47.0`). Base the
  Dell venv on it.
- It pins `torchvision==0.16.2` (built for torch 2.1) against torch 2.5.1 — likely
  cause of the recurring `WinError 127` / `0xc0000139` warnings in old test logs.
- Dell: CPU `torch==2.5.1`, drop `torchaudio`/`torchvision` (verify unused first)
  and `bitsandbytes` (CUDA-only). Expect ~1–2 GB (estimate).

Narrator can't run here (needs CUDA). Options:
- Ollama/llama.cpp locally — roughly 10–15 tok/s for a 3B, 4–7 tok/s for a 7B Q4
  on this CPU (estimate).
- Same backend pointed at the Alienware over LAN.
- Gemini (breaks local-only policy).

## Update (same day): files copied from the Alienware

### `dnd_src_material/`

- `custom_campaigns/the_sirens_embrace_a_pirates_odyssey.md` + `_state.json` — the
  playtest campaign. `/playtest` and `seed_playtest.py --campaign ...` can work now.
- `rules_and_supplements/` — PHB, DMG, MM (57 KB, truncated as the loader expects),
  SRD 5.1 PDF, plus Xanathar's, Tasha's, Volo's, etc. Enough for a full `rules.db`.
- `campaigns/` — 13 published modules (MD) + 2 PDFs. Used for structure analysis /
  generation / RAG, not for the play loop.
- `reference_material/` — five condensed reference MDs.

### `docs/` (all local-only; `docs/` is gitignored)

- `SESSION_RECAP_2026-07-24..27.md` — daily recaps. 07-27 is the latest.
- `INTENT_CLASSIFIER_HANDOFF_2026-07-26.md` + `superpowers/specs|plans/` — intent
  redesign spec, plan, and handoff.
- `LATENCY_EVAL_2026-07-26.md` — L1/L2/L3 latency plan.
- `ZERO_COMPROMISE_GAPS_2026-07-27.md` — the most rigorous gap list; agrees with
  this analysis and goes further.
- `phase2_combat_rest_plan.md`, `chat_gpts_plan.md` — earlier phase plans.
- `DND_SRC_MATERIALS_REVIEW.md`, `AUDIT.md` — older reviews.

### What the docs add or change

- **Open item never closed:** the 07-27 recap says live smoke sign-off after
  `caad5e6` (`i attack the table again` fix) was not done. Don't call the game
  playable until that 9-line script passes after a clean restart:
  `/playtest` → `/session start` → hello / apology / `i attack the table` /
  `i attack the table again` / `try again` / `i attack Mira`.
- **More gaps than listed above** (from ZERO_COMPROMISE_GAPS):
  - Spell casts only consume a slot. No damage, saves, or concentration ("slot
    theater"). Effect helpers exist in `spell_integration._calculate_spell_effects`
    but aren't on the chat path.
  - Chat combat has no enemy turns, action economy, opportunity attacks, death
    saves, or concentration checks, and encounters are in-memory (lost on restart).
  - Any unmatched noun becomes an attackable `object` (`target_resolve.py`); scene
    object HP is in-memory.
  - No XP from play; leveling is REST-API only.
  - `spell_names` isn't passed to `parse_player_intent` in production, so cast slot
    resolution means "name extractable", not "in spellbook".
  - Eval set has no named-NPC attack row.
- **`AUDIT.md` is pre-July and stale.** It says equipment and resting aren't hooked
  into `game_actions.py`. That's almost certainly where the external summary's
  "wire equipment and resting" came from. Both were wired since.
- **Latency plan already specifies L2:** an Ollama/llama.cpp adapter behind
  `LLMManager.generate()` keeping the same async contract, GGUF Q4_K_M, prefix/KV
  reuse, then retire BitsAndBytes for the DM path. L3 = WebSocket token streaming
  and one shared DM + companion call. Notes `VLLM_*` env vars have no consumers
  (dead config). Its "keep IntentLLM on CPU" line is superseded by the embed
  classifier.
- **Documented build order** (ZERO_COMPROMISE_GAPS §5): P0.1 live sign-off +
  `spell_names` → P0.2 engine-resolve rest/roll/use_item/move → P1.1 spell effects
  → P1.2 chat combat loop + encounter persistence → P2 scene objects, XP,
  consumables → P3 memory quality, campaign-layer cleanup last. Next milestone:
  P0 closed + one full chat goblin fight with engine-owned turns and HP.

## Recommended next steps

Reconciled with ZERO_COMPROMISE_GAPS. Step 1 comes first only because the Dell
can't run the narrator at all without it.

1. L2 narrator adapter (Ollama/llama.cpp) per `LATENCY_EVAL_2026-07-26.md` —
   small model on the Dell, Alienware over LAN for quality.
2. P0.1: live smoke sign-off; plumb `spell_names`; add a named-NPC attack eval row.
3. P0.2: engine-resolve rest, roll, use_item (potion/heal minimum), then move/location
   (also fixes the "where am I?" grounding).
4. P1: spell effects + concentration, then the chat goblin fight milestone.
5. Cleanup: dead modules, collapse intent layers, fix stale comments.
6. Keep growing intent data; re-run `scripts/eval_intent.py`.
7. Decide whether `docs/` should stay gitignored — it's why notes get lost between
   machines.
