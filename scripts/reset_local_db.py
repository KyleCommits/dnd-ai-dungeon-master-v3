#!/usr/bin/env python3
"""
Nuclear reset: drop + recreate Postgres DB, enable vector, alembic upgrade head.

Usage:
  python scripts/reset_local_db.py --yes
"""
from __future__ import annotations

import argparse
import asyncio
import os
import subprocess
import sys
from urllib.parse import urlparse, urlunparse

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)


def _sync_url(async_url: str) -> str:
    return async_url.replace("postgresql+asyncpg://", "postgresql://")


def _admin_url(db_url: str) -> str:
    """Point at 'postgres' maintenance DB on same host."""
    parsed = urlparse(_sync_url(db_url))
    return urlunparse(parsed._replace(path="/postgres"))


async def recreate(db_url: str) -> None:
    import asyncpg

    sync = _sync_url(db_url)
    parsed = urlparse(sync)
    db_name = (parsed.path or "/dnd_bot_v3").lstrip("/") or "dnd_bot_v3"
    admin = _admin_url(db_url)

    print(f"Connecting to admin DB to recreate '{db_name}'...")
    conn = await asyncpg.connect(admin)
    try:
        await conn.execute(
            f"""
            SELECT pg_terminate_backend(pid)
            FROM pg_stat_activity
            WHERE datname = $1 AND pid <> pg_backend_pid()
            """,
            db_name,
        )
        await conn.execute(f'DROP DATABASE IF EXISTS "{db_name}"')
        await conn.execute(f'CREATE DATABASE "{db_name}"')
        print(f"SUCCESS: recreated database {db_name}")
    finally:
        await conn.close()

    conn2 = await asyncpg.connect(sync)
    try:
        await conn2.execute("CREATE EXTENSION IF NOT EXISTS vector")
        print("SUCCESS: enabled extension vector")
    except Exception as e:
        print(f"WARNING: could not enable vector extension: {e}")
    finally:
        await conn2.close()


def main() -> int:
    parser = argparse.ArgumentParser(description="Drop/recreate local Postgres + migrate")
    parser.add_argument("--yes", action="store_true", help="Required confirmation")
    args = parser.parse_args()
    if not args.yes:
        print("ERROR: refusing to run without --yes (destructive)")
        return 1

    from src.config import settings

    db_url = settings.DATABASE_URL
    if not db_url:
        print("ERROR: DATABASE_URL not set in .env")
        return 1

    try:
        asyncio.run(recreate(db_url))
    except Exception as e:
        print(f"ERROR: recreate failed: {e}")
        return 1

    result = subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        cwd=ROOT,
    )
    if result.returncode != 0:
        print("ERROR: alembic upgrade head failed")
        return result.returncode
    print("SUCCESS: alembic upgrade head complete")
    print("Next: python scripts/load_rules_from_md.py --fresh")
    print("Next: python scripts/seed_playtest.py --yes")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
