# src/ascii_ui/render_companion.py
from typing import Any, Dict, List, Optional

from .frames import ability_line, box, key_value_rows


def render_companion(companion: Dict[str, Any], width: int = 64) -> str:
    name = companion.get("name", "Companion")
    template = companion.get("template_name", companion.get("creature_type", "?"))
    level = companion.get("level", companion.get("companion_level", 1))
    title = f"{name}  ({template} L{level})"

    status_bits = []
    if companion.get("is_dead"):
        status_bits.append("DEAD")
    if companion.get("is_unconscious"):
        status_bits.append("UNCONSCIOUS")
    status = ", ".join(status_bits) if status_bits else "OK"

    speed = companion.get("speed") or {}
    if isinstance(speed, dict):
        speed_parts = []
        for key in ("land", "fly", "swim", "climb", "burrow"):
            val = speed.get(key)
            if val:
                speed_parts.append(f"{key} {val}")
        speed_str = ", ".join(speed_parts) if speed_parts else "-"
    else:
        speed_str = str(speed)

    rows = key_value_rows(
        [
            ("HP", f"{companion.get('current_hp', '?')}/{companion.get('max_hp', '?')}"),
            ("AC", companion.get("armor_class", "?")),
            ("Size", companion.get("size", "?")),
            ("CR", companion.get("challenge_rating", "?")),
            ("Speed", speed_str),
            ("Status", status),
            ("Bond", companion.get("relationship_level", "-")),
        ]
    )

    abilities = companion.get("abilities") or {}
    if abilities:
        rows.append("")
        rows.append(ability_line(abilities))

    attacks = companion.get("attacks") or []
    if attacks:
        rows.append("")
        rows.append("Attacks:")
        for atk in attacks[:6]:
            if isinstance(atk, dict):
                rows.append(
                    f"  - {atk.get('name', 'Attack')} "
                    f"{atk.get('bonus', atk.get('attack_bonus', ''))} "
                    f"{atk.get('damage', '')}"
                )
            else:
                rows.append(f"  - {atk}")

    specials = companion.get("special_abilities") or []
    if specials:
        rows.append("")
        if isinstance(specials, list):
            names = [
                s.get("name", str(s)) if isinstance(s, dict) else str(s) for s in specials[:6]
            ]
            rows.append("Special: " + ", ".join(names))
        else:
            rows.append(f"Special: {specials}")

    return box(rows, title=title, width=width)


def render_companion_list(companions: List[Dict[str, Any]], width: int = 64) -> str:
    rows = []
    if not companions:
        rows.append("(no companions)")
    for comp in companions:
        marker = "X" if comp.get("is_dead") else " "
        rows.append(
            f"{marker} [{comp.get('id')}] {comp.get('name')} "
            f"HP {comp.get('current_hp', '?')}/{comp.get('max_hp', '?')} "
            f"AC {comp.get('armor_class', '?')}"
        )
    return box(rows, title="Companions", width=width)


def pick_primary_companion(companions: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    living = [c for c in companions if not c.get("is_dead")]
    if living:
        return living[0]
    return companions[0] if companions else None
