# src/ascii_ui/render_spell.py
from typing import Any, Dict, List

from .frames import box, key_value_rows, wrap_text


def render_spell(spell: Dict[str, Any], width: int = 64) -> str:
    name = spell.get("name", "Spell")
    level = spell.get("level", 0)
    school = spell.get("school", "?")
    level_label = "Cantrip" if level == 0 else f"Level {level}"
    title = f"{name}  ({level_label}, {school})"

    components = spell.get("components")
    if isinstance(components, (list, tuple)):
        components = ", ".join(str(c) for c in components)

    rows = key_value_rows(
        [
            ("Casting", spell.get("casting_time", "-")),
            ("Range", spell.get("range", "-")),
            ("Duration", spell.get("duration", "-")),
            ("Components", components or "-"),
            ("Concentration", "yes" if spell.get("concentration") else "no"),
            ("Ritual", "yes" if spell.get("ritual") else "no"),
        ]
    )

    desc = spell.get("description") or spell.get("desc") or ""
    if isinstance(desc, list):
        desc = " ".join(str(d) for d in desc)
    if desc:
        rows.append("")
        rows.extend(wrap_text(str(desc), width - 4)[:12])

    damage = spell.get("damage")
    if damage:
        rows.append("")
        rows.append(f"Damage: {damage}")

    return box(rows, title=title, width=width)


def render_spell_list(
    title: str,
    spells: List[Dict[str, Any]],
    slots: Any = None,
    width: int = 64,
) -> str:
    rows: List[str] = []
    if slots:
        from .render_character import _format_slots

        rows.append(f"Slots: {_format_slots(slots)}")
        rows.append("")

    if not spells:
        rows.append("(no spells)")
    else:
        for spell in spells:
            level = spell.get("level", 0)
            prepared = "P" if spell.get("is_prepared") or spell.get("prepared") else " "
            known = "K" if spell.get("is_known") or spell.get("known") else " "
            school = spell.get("school", "")
            rows.append(
                f"[{prepared}{known}] L{level} {spell.get('name', '?')} {school}"
            )

    return box(rows, title=title, width=width)
