#!/usr/bin/env python3
"""
One-shot playtest sandbox: optional reset → characters → NPCs → monsters.

Usage:
  python scripts/seed_playtest.py
  python scripts/seed_playtest.py --yes --reset
  python scripts/seed_playtest.py --campaign my_campaign
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)


def run(cmd: list[str]) -> int:
    print(">>", " ".join(cmd))
    return subprocess.run(cmd, cwd=ROOT).returncode


def main() -> int:
    parser = argparse.ArgumentParser(description="Seed full playtest sandbox")
    parser.add_argument("--yes", action="store_true", help="Required with --reset")
    parser.add_argument("--reset", action="store_true", help="Clear play data first")
    parser.add_argument("--campaign", default=None)
    parser.add_argument("--user-id", default="player1")
    parser.add_argument("--full-monsters", action="store_true", help="Run full MD/PDF rules load")
    args = parser.parse_args()

    if args.reset:
        if not args.yes:
            print("ERROR: --reset requires --yes")
            return 1
        code = run(
            [
                sys.executable,
                "scripts/reset_play_data.py",
                "--yes",
                "--characters",
                "--npcs",
            ]
        )
        if code != 0:
            return code

    char_cmd = [sys.executable, "scripts/seed_test_characters.py", "--user-id", args.user_id]
    npc_cmd = [sys.executable, "scripts/seed_test_npcs.py"]
    mon_cmd = [sys.executable, "scripts/seed_test_monsters.py"]
    if args.campaign:
        char_cmd += ["--campaign", args.campaign]
        npc_cmd += ["--campaign", args.campaign]
    if args.full_monsters:
        mon_cmd.append("--full-load")

    for cmd in (char_cmd, npc_cmd, mon_cmd):
        code = run(cmd)
        if code != 0:
            print(f"ERROR: command failed: {' '.join(cmd)}")
            return code

    print("")
    print("=== PLAYTEST CHEAT SHEET ===")
    print("1. python start_web_system.py")
    print("2. Open http://localhost:8080/  (or :8081 if DND_PORT=8081)")
    print("3. /playtest             (loads default campaign + Test Fighter)")
    print("4. /npc Mayor Aldric")
    print("5. /monster goblin")
    print("6. /session end          (writes summary + bumps session_count)")
    print("SUCCESS: playtest seed complete")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
