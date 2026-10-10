# Session Recap — 2026-07-27

**Branch / remote:** `master` @ `caad5e6` (pushed; `intent-classifier` fast-forwarded in)  
**Env:** `llama_env_311` (Python 3.11)  
**Prior recap:** [`docs/SESSION_RECAP_2026-07-26.md`](SESSION_RECAP_2026-07-26.md)  
**Handoff (detail):** [`docs/INTENT_CLASSIFIER_HANDOFF_2026-07-26.md`](INTENT_CLASSIFIER_HANDOFF_2026-07-26.md)  
**Spec / plan:** `docs/superpowers/specs/2026-07-26-intent-classifier-design.md`, `docs/superpowers/plans/2026-07-26-intent-classifier.md`

---

## Status: intent redesign landed on master; live sign-off still open

The embedding intent classifier is merged to `master`. Offline eval is strong. Live playtest found one real miss (`i attack the table again` → speak), which was fixed with labeled data and is on master. Kyle has not fully signed off the 9-line smoke script after that fix — restart the server so the embedding cache rebuilds, then retest.

Do **not** treat the game as fully playable until that live pass is green end-to-end.

---

## What shipped (`ab64bf3` → `caad5e6`)

Replaced free-form Qwen2.5-1.5B intent JSON with:

1. **Embedding kNN** over `data/intent/examples.jsonl` (MiniLM via `transformers.AutoModel`, not `sentence_transformers`)
2. **Closed-set slot filling** for attack/cast targets, weapons, spells
3. **Decision policy:** `attack`/`cast` only if margin clears the gate **and** slots resolve; otherwise `speak`
4. **Eval harness** `scripts/eval_intent.py` (speech→mechanics counted separately from other leaks)
5. **Regression gates** in `tests/test_intent_classifier.py` (slow marker)

### Measured (held-out 58 rows)

| | embed | llm (Qwen JSON, after few-shot fix) |
| :--- | :--- | :--- |
| Accuracy | **100%** | 81% |
| Latency p50 | ~15ms | ~6.6s |
| speech → mechanics | **0** | 1 |

Calibrated `INTENT_MECHANICS_MARGIN=0.02`. Sweep alone wanted 0.00 (zero speech leaks at every threshold); adversarial probes showed reflective speech can hit margin 1.0, so **slot resolution** is the real safety net and the margin is a tie-breaker.

Training set grew ~209 → ~292 examples via data-driven rounds (not keyword lists).

### Critical review fix (Task 5 debt)

`tool_executor` used to re-extract a spell name from raw text even after the policy downgraded to `speak`, so a low-margin cast could still consume a slot. Fixed: only derive `cast_spell` when `action == "cast"`.

Also: restored llm low-confidence clarify gate; validated intent config; repaired ~14 tests that mocked `generate_intent_json` without `INTENT_BACKEND=llm` (they were silently loading MiniLM).

---

## Live playtest notes (this session)

| Input | Result |
| :--- | :--- |
| `hello!` / `i say hello` | Narration (OK) |
| apology / 1000 gold for tables | Mira negotiates gold, **no** Longsword (OK — the old catastrophic bug) |
| `i attack the table` | Dice / MISS (OK) |
| `i attack the table again` | Mira narration, **no** attack (**bug** → fixed in `caad5e6`) |

**Interference:** an automated smoke script and the browser both used `user_id=player1`, causing mid-chat `/playtest` / `/session start` and interleaved DM replies. Not an intent bug. Run live smoke from the browser only.

---

## How intent works now

```
Player text
  → speech_act pre-pass (i say / quotes) → speak
  → embed kNN classify (default INTENT_BACKEND=embed)
  → if attack/cast: fill slots against NPC/weapon/spell lists
  → both margin OK and slots.resolved? → mechanics
  → else → speak (narrate, no game state)
```

Legacy Qwen path: `INTENT_BACKEND=llm` (measurement baseline only; not safe to ship).

**Misroute fix loop:** append `{"text","action"}` to `data/intent/examples.jsonl` → `python scripts/eval_intent.py` → retest. Documented in README.

---

## Config (`.env.example`)

```
INTENT_BACKEND=embed
INTENT_EMBED_MODEL=sentence-transformers/all-MiniLM-L6-v2
INTENT_EMBED_K=5
INTENT_MECHANICS_MARGIN=0.02
```

---

## Gotchas (unchanged)

- Python: `.\llama_env_311\Scripts\python.exe`
- pytest exit `-1073741819` on Windows teardown: trust the `N passed` line
- Never import `sentence_transformers`; read settings via `src/intent_config.py`
- Adding speak examples that mention an NPC can outvote `i attack Mira` — gates catch what eval misses
- `docs/` is gitignored; this recap is local-only unless force-added

---

## Still open

1. **Kyle live sign-off** on the smoke script after restart (includes `i attack the table again`)
2. Eval set still has **no named-NPC attack** row (gap that hid one regression earlier)
3. `spell_names` not plumbed from production yet — cast legality still relies on `intent_resolver`
4. Broader play beyond the 9-line smoke (combat flow, rest, cast live, etc.)

---

## Next session suggested start

```
.\llama_env_311\Scripts\python.exe start_web_system.py
```

Then at `http://localhost:8080/`: `/playtest` → `/session start` → hello / apology / `i attack the table` / `i attack the table again` / `try again` / `i attack Mira`.

If a line misroutes: log `Mechanics downgraded to speak`, add a labeled example, re-run `scripts/eval_intent.py`, do not raise the margin.
