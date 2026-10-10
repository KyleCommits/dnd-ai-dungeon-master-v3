# Session Recap — 2026-07-26

**Branch / remote:** `master` @ `ab64bf3` (pushed to `origin/master`)  
**Env:** `llama_env_311` (Python 3.11); Alienware M18 R2 (i9, 32GB, RTX 4080 mobile 12GB)  
**Product focus:** ASCII browser terminal + local LLM DM. React wood UI archived. Discord deprecated.  
**Prior recap:** [`docs/SESSION_RECAP_2026-07-25.md`](SESSION_RECAP_2026-07-25.md)  
**Latency plan:** [`docs/LATENCY_EVAL_2026-07-26.md`](LATENCY_EVAL_2026-07-26.md)

---

## Status: play is still very much broken

**Honest end-of-day assessment (Kyle):**

- Play is **not** in a trustworthy state. Soft RP, social lines, and attack routing still misfire in live use.
- Kyle has **not** playtested the latest fixes (discourse overrides / speak-path fallback / IntentLLM prompt tightening landed after the bad session log below).
- Unit tests pass for mocked IntentLLM paths; that is **not** the same as a working game.
- **Vibe coding may not work in the end** for this stack — iterating prompts, overrides, and small models without a disciplined eval harness has been producing whack-a-mole. Next sessions should assume the current approach might need a hard redesign (stronger structured intent, fewer narrative traps, or a different product cut), not more blind patches.

Do **not** claim the loop is playable until Kyle signs off after a live ASCII session.

---

## What we shipped in code today (`88557f5` → `ab64bf3`)

### A. Latency L1 (narrator)

| Item | Change |
| :--- | :--- |
| DM narrator | Default `mistralai/Mistral-7B-Instruct-v0.3`, **4-bit** BitsAndBytes, no CPU offload on DM path |
| Soft RP path | Narrate **without** full TOOL_CALL schema (~8k-char prefills were causing multi-minute / timeout hell) |
| Tokens / context | Shorter caps; `generate_ms` / token logs in `llm_manager` |
| ASCII UX | Terminal line timestamps `[HH:MM:SS]` |

### B. IntentLLM upgrade + spine hardening

| Item | Change |
| :--- | :--- |
| Intent model | **Qwen2.5-1.5B-Instruct on CPU** (0.5B was inventing attacks on greetings / social) |
| Schema | `repeat_last`; NPC name hints in prompt |
| World targets | `src/target_resolve.py` — npc / object / unknown (pronouns clarify; Mira ≠ furniture) |
| Last attack | `src/last_attack.py` — try again / method-only follow-ups |
| NPC surprise attack | Out-of-combat hostility stub + trust drop (`combat_started`); full encounter wiring still thin |
| Discourse overrides | `i say…` / quotes → speak (skip IntentLLM); apology/gold → override invented attack |
| Speak-path veto | Do not tell greeters to “name a weapon”; tighten “casts a glance” false positive |

### C. Design tension (important)

Kyle repeatedly rejected growing **verb/keyword lists** as the primary brain. Today still added **discourse** overrides (`speech_act`, `social_dialogue`) because 1.5B alone failed in playtest. That is a pragmatic patch, not proof the IntentLLM-first design is solved. If overrides keep multiplying, treat that as evidence the approach is failing.

---

## Live playtest log (before latest discourse patches) — still the reality check

New session; then:

| Player | Result (broken) |
| :--- | :--- |
| `hello!` | Soft RP veto → “Describe what you do… If you are attacking, say the target and weapon.” |
| `i say hello` | Partial RP, but meta stage directions leaked (“Continue the scene by asking…”) |
| apology / 1000 gold for tables | Clarify: “Can you repeat what happened…” |
| `i say "…destroyed your tables…"` | **Resolved as Longsword attack on tables** |

So: speak path, IntentLLM, and attack resolution were fighting each other. Code after that log tries to fix those exact failures — **unverified live**.

---

## How the system is *supposed* to work

```
Player → ASCII terminal
  bare chat → DynamicDM
    → IntentLLM (1.5B CPU) → PlayerIntent JSON
       (+ discourse overrides for i say / apology)
    → validate targets (world) + weapons (inventory)
    → resolve (GameActions / templates) OR speak → short Mistral narrate
    → Postgres + rules/spells DBs
```

| Layer | Owner |
| :--- | :--- |
| 1 Intent | Small local model → JSON (`speak` / `attack` / `cast` / `repeat_last`) |
| 2 Validate | Engine: gear, spells, NPC vs object vs unknown |
| 3 Resolve | Engine dice / HP / slots — never the narrator |
| 4 Narrate | Mistral 7B flavor only; soft RP skips tool schema |

**Rules (aspirational until live-proven):** LLM never decides hit/miss/damage. Fail closed → clarify. Backend is authority.

**Config (local `.env`; `src/config.py` gitignored — see `.env.example`):**

```env
LOCAL_MODEL_NAME=mistralai/Mistral-7B-Instruct-v0.3
LOCAL_LOAD_IN_4BIT=true
LOCAL_QUANTIZATION=4bit
INTENT_MODEL_NAME=Qwen/Qwen2.5-1.5B-Instruct
INTENT_DEVICE=cpu
INTENT_TIMEOUT_SEC=20
INTENT_MAX_NEW_TOKENS=100
INTENT_RULES_FALLBACK=false
```

---

## Commits

1. `88557f5` — Small-LLM intent spine and inventory attack resolution (2026-07-25).
2. **`ab64bf3` — Upgrade local DM stack: Mistral 7B 4-bit, IntentLLM 1.5B, safer speak/attack routing.** (2026-07-26)

`docs/` remains gitignored (recaps stay local).

---

## Starting point for the next AI session

### Read first
1. **This recap** — especially the broken-status section
2. Prior: `docs/SESSION_RECAP_2026-07-25.md`
3. `docs/LATENCY_EVAL_2026-07-26.md`
4. `README.md` + `.env.example`

### Recommended next work (priority order)

1. **Live playtest gate (Kyle)** — restart stack, run a short scripted session; record pass/fail. Do not ship more intent “fixes” until this happens.
2. **Decide: continue IntentLLM spine or redesign** — if social/attack confusion persists after the untested patches, stop vibe-patching and design an eval set + clearer player conventions (or a different intent approach).
3. **Latency measurement** — soft-RP wall time with Mistral 4-bit; then L2 (Ollama/llama.cpp) only if still failing the 15–20s bar.
4. **Grounding** — location / world-state so “where am I?” isn’t a generic tavern.
5. **Creature combat** — real encounter start from NPC attack (current path is a stub).
6. **Phase 5 (campaign arcs)** — still on hold.

### Explicitly deferred
- Campaign generation unification
- Battle map / multiplayer
- Treating more English lists as the primary brain (anti-pattern — but overrides already creeping in)
- Declaring the product “playable” from pytest green alone

### Working rules for next agent
- Prefer extending existing modules; backend is source of truth.
- Use `llama_env_311`; no emojis in project copy.
- Only commit/push when Kyle asks.
- `docs/` is gitignored.
- **Do not claim play works** without Kyle’s live confirmation.
- Be skeptical of vibe coding: prefer small verified loops over large speculative patches.

### Minimal live smoke (after restart)

```
/playtest
/session start
hello!
i say hello
im sorry that i destroyed your tables. will 1000 gold cover the damage?
i say "sorry about the tables"
i attack the table
try again
i attack Mira
```

Expect: first four → speak/narrate (no Longsword); table → engine attack; Mira → NPC/hostility path not furniture.

### Verify (tests only — not play)

```
.\llama_env_311\Scripts\python.exe -m pytest tests/test_player_intent.py tests/test_attack_resolve.py tests/test_weapon_choose.py tests/test_tool_executor.py -q -k "not llm_manager"
```

---

## Quick “where is X?”

| Need | Look here |
| :--- | :--- |
| Intent schema / discourse overrides | `src/player_intent.py` |
| Intent LLM prompt | `src/intent_llm.py` |
| World target kinds | `src/target_resolve.py` |
| Last attack / try again | `src/last_attack.py` |
| Intent → GameActions | `src/intent_resolver.py` |
| TOOL_CALL + speak soft path | `src/tool_executor.py` |
| Attack / NPC hostility | `src/game_actions.py` |
| Mechanics claim detector | `src/mechanics_claims.py` |
| Narrator load / 4-bit | `src/llm_manager.py` |
| ASCII timestamps | `web/ascii_client/terminal.js` |
| INTENT / LOCAL env docs | `.env.example`, `README.md` |
