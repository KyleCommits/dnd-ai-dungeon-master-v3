# src/ascii_ui/render_monster.py
from typing import Any, Dict, List

from .frames import box, key_value_rows


def render_monster(monster: Dict[str, Any], width: int = 64) -> str:
    name = monster.get("name", "Monster")
    cr = monster.get("cr", "?")
    title = f"{name}  CR {cr}"
    rows = key_value_rows(
        [
            ("AC", monster.get("ac", "?")),
            ("HP", monster.get("hp", "?")),
            ("Size", monster.get("size", "-")),
            ("Type", monster.get("creature_type", "-")),
            ("Speed", monster.get("speed", "-")),
            ("DEX mod", monster.get("dexterity_modifier", 0)),
            ("Atk", f"+{monster.get('attack_bonus', 0)}"),
            ("Damage", monster.get("damage", "-")),
            ("Source", monster.get("source", "-")),
        ]
    )
    actions = monster.get("actions") or []
    if actions:
        rows.append("")
        rows.append("Actions:")
        for act in actions[:6]:
            if isinstance(act, dict):
                rows.append(
                    f"  - {act.get('name', 'Attack')} +{act.get('attack_bonus', '?')} "
                    f"{act.get('damage', '')} {act.get('damage_type', '')}"
                )
            else:
                rows.append(f"  - {act}")
    return box(rows, title=title, width=width)


def render_monster_list(monsters: List[Dict[str, Any]], width: int = 64) -> str:
    rows = []
    if not monsters:
        rows.append("(no monsters)")
    for m in monsters:
        rows.append(
            f"- {m.get('name')} CR {m.get('cr', '?')} "
            f"AC {m.get('ac', '?')} HP {m.get('hp', '?')}"
        )
    return box(rows, title="Monsters", width=width)
