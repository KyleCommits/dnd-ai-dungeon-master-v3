# src/attack_resolve.py
"""Weapon profiles and parsing for resolve_player_attack."""

from __future__ import annotations

import re
from typing import Dict, Optional, Tuple

# Simple weapon map: ability (str/dex), damage die, versatile ignored for MVP.
WEAPON_PROFILES: Dict[str, Dict] = {
    "unarmed": {"ability": "strength", "damage": "1d4", "finesse": False},
    "fist": {"ability": "strength", "damage": "1d4", "finesse": False},
    "fists": {"ability": "strength", "damage": "1d4", "finesse": False},
    "sword": {"ability": "strength", "damage": "1d8", "finesse": False},
    "longsword": {"ability": "strength", "damage": "1d8", "finesse": False},
    "shortsword": {"ability": "dexterity", "damage": "1d6", "finesse": True},
    "greatsword": {"ability": "strength", "damage": "2d6", "finesse": False},
    "scimitar": {"ability": "dexterity", "damage": "1d6", "finesse": True},
    "rapier": {"ability": "dexterity", "damage": "1d8", "finesse": True},
    "dagger": {"ability": "dexterity", "damage": "1d4", "finesse": True},
    "mace": {"ability": "strength", "damage": "1d6", "finesse": False},
    "warhammer": {"ability": "strength", "damage": "1d8", "finesse": False},
    "battleaxe": {"ability": "strength", "damage": "1d8", "finesse": False},
    "greataxe": {"ability": "strength", "damage": "1d12", "finesse": False},
    "handaxe": {"ability": "strength", "damage": "1d6", "finesse": False},
    "javelin": {"ability": "strength", "damage": "1d6", "finesse": False},
    "spear": {"ability": "strength", "damage": "1d6", "finesse": False},
    "club": {"ability": "strength", "damage": "1d4", "finesse": False},
    "quarterstaff": {"ability": "strength", "damage": "1d6", "finesse": False},
    "staff": {"ability": "strength", "damage": "1d6", "finesse": False},
    "shortbow": {"ability": "dexterity", "damage": "1d6", "finesse": False},
    "longbow": {"ability": "dexterity", "damage": "1d8", "finesse": False},
    "bow": {"ability": "dexterity", "damage": "1d8", "finesse": False},
    "crossbow": {"ability": "dexterity", "damage": "1d8", "finesse": False},
    "improvised": {"ability": "strength", "damage": "1d4", "finesse": False},
}

_ATTACK_VERBS = (
    r"attack(?:s|ing)?|swing(?:s|ing)?|strike(?:s|ing)?|hit(?:s|ting)?|"
    r"slash(?:es|ing)?|stab(?:s|bing)?|smash(?:es|ing)?|punch(?:es|ing)?|shoot(?:s|ing)?"
)
_ATTACK_TARGET_RE = re.compile(
    rf"\b(?:{_ATTACK_VERBS})\s+(?:at\s+|the\s+|a\s+|an\s+)?(.+?)"
    r"(?:\s*[—\-–]\s*|\s+with\s+|\s+using\s+|$)",
    re.I,
)
# "swing my sword at the table" (not generic "attack X at Y")
_SWING_WEAPON_AT_RE = re.compile(
    r"\b(?:swing(?:s|ing)?|strike(?:s|ing)?|slash(?:es|ing)?|stab(?:s|bing)?|hit(?:s|ting)?)\s+"
    r"(?:my\s+|the\s+|a\s+|an\s+)?([\w\-]+)\s+at\s+"
    r"(?:the\s+|a\s+|an\s+)?(.+)",
    re.I,
)
_METHOD_RE = re.compile(
    r"(?:—|-|–)\s*(?:my\s+|the\s+)?(.+)$|"
    r"\b(?:with|using|use)\s+(?:my\s+|the\s+)?(.+)$|"
    r"\b(unarmed|fists?|longsword|shortsword|greatsword|scimitar|rapier|dagger|"
    r"mace|warhammer|battleaxe|greataxe|handaxe|javelin|spear|club|quarterstaff|"
    r"staff|shortbow|longbow|crossbow|sword|axe|bow|hammer|improvised)\b",
    re.I,
)
_TARGET_TRAILING_STOP = frozenset({
    "again", "now", "please", "harder", "once", "more", "instead",
})

# Body attacks are unarmed unless a weapon is also named.
_UNARMED_VERB_RE = re.compile(
    r"\b(?:punch(?:es|ing)?|kick(?:s|ing)?|headbutt(?:s|ing)?|slap(?:s|ping)?|"
    r"smack(?:s|ing)?|elbow(?:s|ing)?|knee(?:s|ing)?)\b",
    re.I,
)


def ability_mod(score: int) -> int:
    return (int(score) - 10) // 2


def resolve_weapon_key(method: str) -> str:
    m = (method or "unarmed").strip().lower()
    m = re.sub(r"^(?:my|the|a|an)\s+", "", m)
    # normalize "my sword" leftovers
    m = m.strip(" .,!")
    if m in WEAPON_PROFILES:
        return m
    for key in WEAPON_PROFILES:
        if key in m or m in key:
            return key
    if "sword" in m:
        return "sword"
    if "axe" in m:
        return "battleaxe"
    if "bow" in m:
        return "longbow"
    return "improvised"


def _clean_target(target: str) -> str:
    t = re.sub(r"^(?:the|a|an)\s+", "", (target or "").strip(" .,!"), flags=re.I).strip()
    words = t.split()
    while words and words[-1].lower() in _TARGET_TRAILING_STOP:
        words.pop()
    return " ".join(words).strip()


def parse_attack_utterance(text: str) -> Tuple[Optional[str], Optional[str]]:
    """
    From 'i attack a table — my sword' -> ('table', 'sword').
    Also 'i swing my sword at the table again' -> ('table', 'sword').
    Returns (target_name, method).
    """
    raw = (text or "").strip()
    if not raw:
        return None, None

    target = None
    method = None

    # Split on em-dash style clarify merge first
    if "—" in raw or " - " in raw:
        parts = re.split(r"\s*[—]\s*|\s+-\s+", raw, maxsplit=1)
        if len(parts) == 2:
            left, right = parts[0].strip(), parts[1].strip()
            tm = _ATTACK_TARGET_RE.search(left)
            if tm:
                target = tm.group(1).strip(" .,!")
            method = right
            method = re.sub(r"^(?:my|the|a|an|use|using|with)\s+", "", method, flags=re.I).strip()

    # "swing my sword at the table"
    if target is None or method is None:
        sm = _SWING_WEAPON_AT_RE.search(raw)
        if sm:
            method = method or sm.group(1).strip()
            target = target or sm.group(2).strip()

    if target is None:
        tm = _ATTACK_TARGET_RE.search(raw)
        if tm:
            target = tm.group(1).strip(" .,!")
            # strip trailing method clause from target
            target = re.split(r"\s+with\s+|\s+using\s+", target, maxsplit=1, flags=re.I)[0].strip()

    if method is None:
        mm = _METHOD_RE.search(raw)
        if mm:
            method = next((g for g in mm.groups() if g), None)
            if method:
                method = re.sub(r"^(?:my|the|a|an|use|using|with)\s+", "", method, flags=re.I).strip()

    # "i punch the table" → unarmed (do not fall through to equipped sword)
    if method is None and _UNARMED_VERB_RE.search(raw):
        method = "unarmed"

    if target:
        target = _clean_target(target)

    return target or None, method or None


def format_attack_reply(result: Dict) -> str:
    """Player-facing template from resolve_player_attack result (no LLM)."""
    if not result.get("success"):
        return result.get("message") or result.get("error") or "Attack failed."

    lines = ["Rolling attack for you…"]
    atk = result.get("attack_total")
    ac = result.get("ac")
    hit = result.get("hit")
    lines.append(f"Attack: {atk} vs AC {ac} — {'HIT' if hit else 'MISS'}")

    if hit:
        dmg = result.get("damage")
        dmg_detail = result.get("damage_detail") or ""
        if dmg is not None:
            extra = f" ({dmg_detail})" if dmg_detail else ""
            lines.append(f"Damage: {dmg}{extra}")
        name = result.get("target_name") or "target"
        if result.get("target_kind") == "object":
            hp = result.get("object_hp_remaining")
            max_hp = result.get("object_max_hp")
            if result.get("destroyed"):
                lines.append(f"The {name} is destroyed.")
            elif hp is not None and max_hp is not None:
                lines.append(f"The {name} (HP {hp}/{max_hp}) takes the hit.")
        else:
            thp = result.get("target_hp")
            if thp is not None:
                lines.append(f"{name} HP now {thp}.")
    else:
        name = result.get("target_name") or "target"
        if result.get("target_kind") == "npc":
            lines.append(f"Your blow misses {name}.")
        else:
            lines.append(f"Your blow misses the {name}.")

    msg = result.get("message")
    if msg:
        lines.append(msg)
    if result.get("combat_started"):
        lines.append("(Combat initiated.)")

    # Compact mechanics footer
    lines.append("")
    lines.append(
        f"[mechanics] attack={atk} ac={ac} hit={hit}"
        + (f" damage={result.get('damage')}" if hit else "")
        + (f" destroyed={result.get('destroyed')}" if result.get("target_kind") == "object" else "")
    )
    return "\n".join(lines)
