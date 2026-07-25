# Local PostgreSQL setup (fresh start)

App state (chat, characters, session summaries, campaign world memory, RAG vectors) uses PostgreSQL.
Offline rules stay on SQLite: `data/rules.db`, `data/spells.db`.

Nothing in this project requires a secret production password — use a local password you choose.

## 1. Install / start Postgres

Windows: install PostgreSQL 15+ (or use Docker). Ensure the server listens on `localhost:5432`.

Optional Docker:

```bash
docker run --name dnd-pg -e POSTGRES_USER=dnd -e POSTGRES_PASSWORD=dnd_local -e POSTGRES_DB=dnd_bot_v3 -p 5432:5432 -d pgvector/pgvector:pg16
```

(`pgvector` image includes the `vector` extension used by LlamaIndex RAG.)

## 2. Create role + database (if not using Docker)

In `psql` as a superuser:

```sql
CREATE USER dnd WITH PASSWORD 'dnd_local';
CREATE DATABASE dnd_bot_v3 OWNER dnd;
\c dnd_bot_v3
CREATE EXTENSION IF NOT EXISTS vector;
GRANT ALL ON SCHEMA public TO dnd;
```

## 3. Configure `.env`

```env
DATABASE_URL=postgresql+asyncpg://dnd:dnd_local@localhost:5432/dnd_bot_v3
```

Copy from `.env.example` and set Discord/API keys as needed. Discord fields may be dummy strings if you only use the web/ASCII UI.

## 4. Schema (Alembic)

```bash
# from repo root, with llama_env_311 active
pip install alembic
alembic upgrade head
```

Or nuclear recreate:

```bash
python scripts/reset_local_db.py --yes
```

That drops/recreates `dnd_bot_v3`, enables `vector`, and runs `alembic upgrade head`.

## 5. Offline rules + playtest seed

```bash
python scripts/load_rules_from_md.py --fresh
python scripts/seed_playtest.py --yes
```

Cheat sheet after seed: `/chars`, `/active <name>`, `/npc`, `/monster goblin`, `/session end`.

## 6. Soft reset (keep schema + campaign files)

```bash
python scripts/reset_play_data.py --yes
python scripts/reset_play_data.py --yes --characters --npcs
python scripts/seed_playtest.py
```

## Smoke check

```bash
python -c "import asyncio; from src.database import test_connection; print(asyncio.run(test_connection()))"
```

Should print `True`.
