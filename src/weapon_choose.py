# src/weapon_choose.py
"""Pick a weapon from character inventory — never invent gear from English alone."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence, Tuple

from .attack_resolve import WEAPON_PROFILES, resolve_weapon_key
from .equipment_system import ItemType, Weapon, inventory_manager

_UNARMED_HINTS = frozenset({
    "unarmed", "fist", "fists", "bare hands", "bare hand", "punch", "hands",
    "kick", "slap", "smack", "headbutt", "elbow", "knee",
})

_WEAPON_NAME_TOKENS = (
    "sword", "axe", "bow", "dagger", "mace", "hammer", "spear", "javelin",
    "staff", "club", "crossbow", "rapier", "scimitar", "flail", "pike",
    "trident", "whip", "dart", "sling", "halberd", "glaive", "morningstar",
    "warhammer", "battleaxe", "greataxe", "longsword", "shortsword", "greatsword",
)


@dataclass
class WeaponChoice:
    status: str  # ok | clarify | error
    weapon_name: Optional[str] = None
    damage_dice: str = "1d4"
    properties: List[str] = field(default_factory=list)
    ability: str = "strength"  # strength | dexterity
    finesse: bool = False
    from_inventory: bool = False
    prompt: Optional[str] = None
    options: List[str] = field(default_factory=list)

    def as_dict(self) -> Dict[str, Any]:
        return {
            "status": self.status,
            "weapon_name": self.weapon_name,
            "damage_dice": self.damage_dice,
            "properties": list(self.properties),
            "ability": self.ability,
            "finesse": self.finesse,
            "from_inventory": self.from_inventory,
            "prompt": self.prompt,
            "options": list(self.options),
        }


def normalize_hint(hint: str) -> str:
    h = re.sub(
        r"^(?:my|the|a|an|use|using|with|grab|wield)\s+",
        "",
        (hint or "").strip(),
        flags=re.I,
    )
    return h.strip(" .,!").lower()


def is_unarmed_hint(hint: str) -> bool:
    return normalize_hint(hint) in _UNARMED_HINTS


def is_inventory_weapon(item_name: str) -> bool:
    """True if catalog says weapon, or name looks like a weapon (custom +1 swords)."""
    if not item_name:
        return False
    catalog = inventory_manager.get_item(item_name)
    if isinstance(catalog, Weapon):
        return True
    if catalog is not None and getattr(catalog, "item_type", None) == ItemType.WEAPON:
        return True
    lower = item_name.lower()
    return any(tok in lower for tok in _WEAPON_NAME_TOKENS)


def _stats_for_weapon(item_name: str) -> Tuple[str, List[str], str, bool]:
    """Return (damage_dice, properties, ability, finesse)."""
    catalog = inventory_manager.get_item(item_name)
    if isinstance(catalog, Weapon) and catalog.damage:
        props = list(catalog.properties or [])
        finesse = any(str(p).lower() == "finesse" for p in props)
        ranged = "ranged" in str(getattr(catalog, "weapon_type", "")).lower()
        ability = "dexterity" if (finesse or ranged) else "strength"
        return catalog.damage.dice, props, ability, finesse

    # Fallback: map name token → static profile
    key = resolve_weapon_key(item_name)
    prof = WEAPON_PROFILES.get(key, WEAPON_PROFILES["improvised"])
    return (
        prof["damage"],
        [],
        prof.get("ability", "strength"),
        bool(prof.get("finesse")),
    )


def _ok_unarmed() -> WeaponChoice:
    prof = WEAPON_PROFILES["unarmed"]
    return WeaponChoice(
        status="ok",
        weapon_name="unarmed",
        damage_dice=prof["damage"],
        ability="strength",
        finesse=False,
        from_inventory=False,
    )


def _ok_weapon(name: str, from_inventory: bool = True) -> WeaponChoice:
    dice, props, ability, finesse = _stats_for_weapon(name)
    return WeaponChoice(
        status="ok",
        weapon_name=name,
        damage_dice=dice,
        properties=props,
        ability=ability,
        finesse=finesse,
        from_inventory=from_inventory,
    )


def _format_options(names: Sequence[str]) -> str:
    parts = [f"{i + 1}) {n}" for i, n in enumerate(names)]
    return "; ".join(parts)


def match_weapons(hint: str, weapon_names: Sequence[str]) -> List[str]:
    h = normalize_hint(hint)
    if not h:
        return []
    exact = [w for w in weapon_names if w.lower() == h]
    if exact:
        return exact
    # Prefer substring match (sword → Longsword, Shortsword)
    matches = [w for w in weapon_names if h in w.lower()]
    if matches:
        return matches
    # Reverse: inventory "Sword" vs hint "longsword"
    return [w for w in weapon_names if w.lower() in h]


def choose_weapon_from_inventory(
    equipment: Sequence[Tuple[str, bool]],
    method_hint: str = "",
    numbered_pick: Optional[int] = None,
    prior_options: Optional[Sequence[str]] = None,
) -> WeaponChoice:
    """
    Decision table over inventory.

    equipment: list of (item_name, equipped).
    numbered_pick: 1-based index into prior_options (follow-up "1").
    """
    if numbered_pick is not None and prior_options:
        idx = numbered_pick - 1
        if 0 <= idx < len(prior_options):
            name = prior_options[idx]
            if name.lower() in _UNARMED_HINTS or name.lower() == "unarmed":
                return _ok_unarmed()
            return _ok_weapon(name, from_inventory=is_inventory_weapon(name))
        return WeaponChoice(
            status="clarify",
            prompt=f"Pick a number from 1–{len(prior_options)}.",
            options=list(prior_options),
        )

    weapons = [(n, eq) for n, eq in equipment if is_inventory_weapon(n)]
    names = [n for n, _ in weapons]

    if is_unarmed_hint(method_hint):
        return _ok_unarmed()

    hint = normalize_hint(method_hint)

    # Numeric hint without prior_options: treat as invalid clarify
    if hint.isdigit():
        if names:
            opts = list(names)
            return WeaponChoice(
                status="clarify",
                prompt=(
                    f"Which weapon? {_format_options(opts)}"
                    + ("; or say unarmed" if opts else "")
                ),
                options=opts,
            )
        return _ok_unarmed()

    if hint:
        matches = match_weapons(hint, names)
        if len(matches) == 1:
            return _ok_weapon(matches[0])
        if len(matches) == 0:
            if names:
                opts = list(names)
                return WeaponChoice(
                    status="clarify",
                    prompt=(
                        f"You don't have a {hint}. "
                        f"Weapons you have: {_format_options(opts)}. "
                        f"Pick one, or say unarmed."
                    ),
                    options=opts,
                )
            return WeaponChoice(
                status="clarify",
                prompt=(
                    f"You don't have a {hint}, and you have no weapons. "
                    f"Attack unarmed?"
                ),
                options=["unarmed"],
            )
        opts = list(matches)
        return WeaponChoice(
            status="clarify",
            prompt=f"Which {hint} — {_format_options(opts)}?",
            options=opts,
        )

    # No hint: equipped sole weapon → inventory sole weapon → clarify
    equipped = [n for n, eq in weapons if eq]
    if len(equipped) == 1:
        return _ok_weapon(equipped[0])
    if len(names) == 1:
        return _ok_weapon(names[0])
    if len(names) == 0:
        return WeaponChoice(
            status="clarify",
            prompt="You have no weapons. Attack unarmed?",
            options=["unarmed"],
        )
    opts = list(names)
    equipped_note = ""
    if equipped:
        equipped_note = f" (equipped: {', '.join(equipped)})"
    return WeaponChoice(
        status="clarify",
        prompt=(
            f"Which weapon are you using{equipped_note}? "
            f"{_format_options(opts)}; or say unarmed."
        ),
        options=opts,
    )
