# src/ascii_ui/render_character.py
from typing import Any, Dict, List, Optional

from .frames import ability_line, box, key_value_rows


def render_character_sheet(character: Dict[str, Any], width: int = 64) -> str:
    name = character.get("name", "Unknown")
    race = character.get("race", "?")
    class_name = character.get("class_name", "?")
    level = character.get("level", 1)
    header = f"{name}  {race} {class_name} {level}"

    hp = f"{character.get('current_hp', '?')}/{character.get('max_hp', '?')}"
    status_bits = []
    if not character.get("is_alive", True):
        status_bits.append("DEAD")
    if character.get("is_unconscious"):
        status_bits.append("UNCONSCIOUS")
    conditions = character.get("conditions") or []
    if isinstance(conditions, list):
        for c in conditions:
            if isinstance(c, dict):
                status_bits.append(str(c.get("name", c)))
            else:
                status_bits.append(str(c))
    status = ", ".join(status_bits) if status_bits else "OK"

    rows = key_value_rows(
        [
            ("HP", hp),
            ("AC", character.get("armor_class", "?")),
            ("Speed", character.get("speed", "?")),
            ("Prof", f"+{character.get('proficiency_bonus', 2)}"),
            ("Status", status),
            ("BG", character.get("background", "-")),
        ]
    )

    abilities = character.get("abilities") or {}
    if abilities:
        rows.append("")
        rows.append(ability_line(abilities))

    slots = character.get("spell_slots") or character.get("spell_slots_summary")
    if slots:
        rows.append("")
        rows.append(f"Slots: {_format_slots(slots)}")

    skills = character.get("skills") or []
    proficient = [
        s.get("name", s) if isinstance(s, dict) else str(s)
        for s in skills
        if (isinstance(s, dict) and s.get("proficient")) or not isinstance(s, dict)
    ]
    if proficient:
        rows.append("")
        rows.append("Skills: " + ", ".join(proficient[:12]))
        if len(proficient) > 12:
            rows.append(f"  ... +{len(proficient) - 12} more")

    equipment = character.get("equipment") or []
    if equipment:
        rows.append("")
        eq_names = []
        for item in equipment[:8]:
            if isinstance(item, dict):
                mark = "*" if item.get("equipped") else " "
                eq_names.append(f"{mark}{item.get('name', '?')}")
            else:
                eq_names.append(str(item))
        rows.append("Gear: " + ", ".join(eq_names))

    return box(rows, title=header, width=width)


def render_character_list(
    characters: List[Dict[str, Any]],
    active_id: Optional[int] = None,
    width: int = 64,
) -> str:
    rows = []
    if not characters:
        rows.append("(no characters)")
    for char in characters:
        marker = ">" if active_id is not None and char.get("id") == active_id else " "
        hp = f"{char.get('current_hp', '?')}/{char.get('max_hp', '?')}"
        rows.append(
            f"{marker} [{char.get('id')}] {char.get('name')} "
            f"{char.get('race')} {char.get('class_name')} "
            f"L{char.get('level')} HP {hp}"
        )
    return box(rows, title="Characters", width=width)


def _format_slots(slots: Any) -> str:
    if isinstance(slots, dict):
        parts = []
        for level in sorted(slots.keys(), key=lambda x: int(x) if str(x).isdigit() else 0):
            val = slots[level]
            if isinstance(val, dict):
                used = val.get("used", 0)
                total = val.get("total", val.get("max", "?"))
                parts.append(f"L{level}:{used}/{total}")
            else:
                parts.append(f"L{level}:{val}")
        return " ".join(parts)
    if isinstance(slots, list):
        parts = []
        for entry in slots:
            if isinstance(entry, dict):
                level = entry.get("level", "?")
                used = entry.get("used", 0)
                total = entry.get("total", entry.get("max", "?"))
                parts.append(f"L{level}:{used}/{total}")
            else:
                parts.append(str(entry))
        return " ".join(parts)
    return str(slots)
