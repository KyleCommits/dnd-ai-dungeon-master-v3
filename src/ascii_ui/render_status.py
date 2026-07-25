# src/ascii_ui/render_status.py
from typing import Any, Dict, Optional

from .frames import box, key_value_rows


def render_status(
    campaign: Optional[Dict[str, Any]] = None,
    active_character: Optional[Dict[str, Any]] = None,
    session_id: Optional[str] = None,
    extra: Optional[Dict[str, Any]] = None,
    width: int = 64,
) -> str:
    campaign = campaign or {}
    rows = key_value_rows(
        [
            ("Campaign", campaign.get("name") or "(none)"),
            ("Act", campaign.get("act", "-")),
            ("Location", campaign.get("location", "-")),
            ("Session#", campaign.get("session", "-")),
            ("SessionID", session_id or "-"),
        ]
    )

    if active_character:
        rows.append("")
        rows.append(
            f"Active: [{active_character.get('id')}] {active_character.get('name')} "
            f"HP {active_character.get('current_hp', '?')}/{active_character.get('max_hp', '?')} "
            f"AC {active_character.get('armor_class', '?')}"
        )
    else:
        rows.append("")
        rows.append("Active: (none)")

    if extra:
        for key, value in extra.items():
            rows.append(f"{key}: {value}")

    return box(rows, title="Status", width=width)


def render_help(width: int = 64) -> str:
    rows = [
        "Chat: type normally (no leading /)",
        "",
        "/help                 this help",
        "/status               campaign + active PC",
        "/campaigns            list campaign files",
        "/load <name>          load campaign",
        "/playtest [camp] [char]  load default campaign + Test Fighter",
        "/session start|end    start or end session (end saves summary+memory)",
        "",
        "/chars                list characters",
        "/active <id|name>     set active character",
        "/sheet                active PC sheet",
        "",
        "/companion            companion sheet",
        "/companion heal N     heal companion",
        "/companion damage N   damage companion",
        "",
        "/npcs                 list NPCs (includes trust from world memory)",
        "/npc <id|name>        NPC detail + trust",
        "",
        "/spells [query]       spells / search",
        "/cast <name> [level]  cast spell",
        "/prepare <name>       prepare spell",
        "/unprepare <name>     unprepare spell",
        "/rest short|long      rest",
        "",
        "/monster [query]      monster lookup (rules.db)",
        "/gear [query]         equipment lookup",
        "/equip <item>         equip from inventory",
        "/unequip <item>       unequip item",
        "",
        "/roll <NdM[+/-K]>     dice roll",
    ]
    return box(rows, title="ASCII Terminal Help", width=width)
