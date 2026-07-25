# src/ascii_ui/render_npc.py
from typing import Any, Dict, List

from .frames import ability_line, box, key_value_rows


def render_npc(npc: Dict[str, Any], width: int = 64) -> str:
    name = npc.get("name", "NPC")
    npc_type = npc.get("npc_type", npc.get("type", "neutral"))
    race = npc.get("race", "?")
    class_name = npc.get("class_name") or "-"
    level = npc.get("level", 1)
    title = f"{name}  [{npc_type}]"

    status = "OK"
    if not npc.get("is_alive", True):
        status = "DEAD"
    elif npc.get("is_active") is False:
        status = "INACTIVE"

    rows = key_value_rows(
        [
            ("Race", race),
            ("Class", class_name),
            ("Level", level),
            ("HP", f"{npc.get('current_hp', '?')}/{npc.get('max_hp', '?')}"),
            ("AC", npc.get("armor_class", "?")),
            ("Speed", npc.get("speed", "?")),
            ("Status", status),
        ]
    )

    abilities = npc.get("abilities") or {}
    if abilities:
        rows.append("")
        rows.append(ability_line(abilities))

    relation = npc.get("relationship") or npc.get("notes")
    if relation:
        rows.append("")
        rows.append(f"Notes: {relation}")

    return box(rows, title=title, width=width)


def render_npc_list(npcs: List[Dict[str, Any]], width: int = 64) -> str:
    rows = []
    if not npcs:
        rows.append("(no NPCs)")
    for npc in npcs:
        marker = "X" if not npc.get("is_alive", True) else " "
        rows.append(
            f"{marker} [{npc.get('id', '-')}] {npc.get('name')} "
            f"{npc.get('npc_type', npc.get('type', '?'))} "
            f"HP {npc.get('current_hp', '?')}/{npc.get('max_hp', '?')}"
        )
    return box(rows, title="NPCs", width=width)
