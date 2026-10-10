# Session recap — 2026-10-10 Phase 0 (Dell bootstrap)

**Machine:** Dell Inspiron 7405 2-in-1 (Ryzen 5 4500U, 23.4 GB, Radeon iGPU)
**Plan:** [`PLAN_FINISH_AI_DM_2026-10-10.md`](PLAN_FINISH_AI_DM_2026-10-10.md)

## Done

- Python 3.11.9 via `py -3.11`; `llama_env_311` with CPU `torch==2.5.1+cpu`, `transformers==4.56.1`, `google-genai==1.46.0`.
- [`requirements-cpu.txt`](../requirements-cpu.txt) for this laptop; [`requirements-cuda.txt`](../requirements-cuda.txt) is the Alienware freeze (was `requirements_working.txt`).
- Recreated tracked [`src/config.py`](../src/config.py) (`pydantic-settings`) with every `settings.*` attribute callers use, plus `DM_BACKEND` / `GEMINI_*`.
- Stopped ignoring `docs/` and `src/config.py`. Removed the `*gemini*` gitignore glob so source and docs stay trackable.
- `.env.example` documents Gemini-first defaults. Local `.env` got the new keys (existing `GEMINI_API_KEY` kept).
- Offline rules: `data/rules.db` → **254 monsters, 51 equipment**.
- Spells: `data/spells.db` → **319 spells** (`scripts/load_spells.py --yes`).
- Config contract tests: [`tests/test_config.py`](../tests/test_config.py).

## Postgres

Docker Desktop is not installed (`winget` had no applicable installer). WSL Ubuntu
24.04 is present but `sudo` needs a password.

Used user-space PostgreSQL **17.11** binaries (EnterpriseDB zip, SHA-256 verified)
under `%LOCALAPPDATA%\dnd-ai-dm`. Start with
[`scripts/start_local_postgres.ps1`](../scripts/start_local_postgres.ps1).
`CREATE EXTENSION vector` warned (no pgvector) — expected; web play does not use RAG.

- `alembic upgrade head` → `001_initial`
- Seed: Test Fighter / Wizard / Cleric, Mayor Aldric, Innkeeper Mira, Captain Voss,
  goblin/wolf/orc/skeleton

## Tests

`pytest -m "not slow"` ignoring Discord / live-Gemini scripts:

- **182 passed**, 13 skipped, then 1 expected local-LLM fail (no `bitsandbytes`)
- After skip: local Transformers test skipped when `DM_BACKEND=gemini`

Config-only subset: 106 passed.

## Next

Phase 1: Gemini narrator backend behind `DM_BACKEND=gemini`.
