# src/ascii_ui/render_equipment.py
from typing import Any, Dict, List

from .frames import box, key_value_rows


def render_item(item: Dict[str, Any], width: int = 64) -> str:
    name = item.get("name", "Item")
    item_type = item.get("item_type", "gear")
    title = f"{name}  [{item_type}]"
    rows = key_value_rows(
        [
            ("Cost", item.get("cost", "-")),
            ("Weight", item.get("weight", "-")),
            ("Damage", f"{item.get('damage', '-')} {item.get('damage_type', '')}".strip()),
            ("Properties", item.get("properties", "-")),
            ("Base AC", item.get("base_ac", "-")),
            ("Max Dex", item.get("max_dex_bonus", "-")),
            ("Category", item.get("armor_category", "-")),
            ("Stealth", "disadvantage" if item.get("stealth_disadvantage") else "-"),
            ("Str req", item.get("strength_req", "-")),
            ("Source", item.get("source", "-")),
        ]
    )
    return box(rows, title=title, width=width)


def render_item_list(items: List[Dict[str, Any]], width: int = 64) -> str:
    rows = []
    if not items:
        rows.append("(no items)")
    for item in items:
        extra = ""
        if item.get("damage"):
            extra = f"{item.get('damage')} {item.get('damage_type', '')}"
        elif item.get("base_ac") is not None:
            extra = f"AC {item.get('base_ac')}"
        rows.append(f"- [{item.get('item_type', '?')}] {item.get('name')} {extra}".rstrip())
    return box(rows, title="Equipment", width=width)
