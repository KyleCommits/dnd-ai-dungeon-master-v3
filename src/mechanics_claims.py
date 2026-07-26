# src/mechanics_claims.py
"""Heuristic detection of invented mechanics and player mechanical intent tiers."""

from __future__ import annotations

import re
from enum import Enum
from typing import Optional, Tuple

# Patterns that strongly imply a mechanical outcome was narrated.
_CLAIM_PATTERNS = [
    re.compile(r"\btakes?\s+\d+\s+(?:points?\s+of\s+)?damage\b", re.I),
    re.compile(r"\bdeals?\s+\d+\s+(?:points?\s+of\s+)?damage\b", re.I),
    re.compile(r"\b(?:you|they|he|she|it)\s+heal(?:s|ed)?\s+\d+\b", re.I),
    re.compile(r"\b(?:hp|hit\s*points?)\s*(?:to|=|:)?\s*\d+\b", re.I),
    re.compile(r"\b(?:now\s+at|down\s+to)\s+\d+\s*(?:hp|hit\s*points?)\b", re.I),
    re.compile(r"\brolls?\s+a\s+\d+\b", re.I),
    re.compile(r"\bnat(?:ural)?\s*20\b", re.I),
    re.compile(r"\bnat(?:ural)?\s*1\b", re.I),
    # Real spell casts — not "casts a glance / her eyes / a smile"
    re.compile(
        r"\bcast(?:s|ing)?\s+(?:the\s+spell\s+)?"
        r"(?!a\s+(?:glance|look|eye|eyes|smile|shadow)\b)"
        r"(?!an?\s+)(?!her\s+)(?!his\s+)(?!their\s+)(?!your\s+)(?!my\s+)"
        r"[A-Za-z][A-Za-z'\-]*(?:\s+[A-Za-z][A-Za-z'\-]*){0,3}\b",
        re.I,
    ),
    re.compile(r"\b(?:spend|spends|spent|consume[sd]?)\s+(?:a\s+)?(?:spell\s+)?slot\b", re.I),
    re.compile(r"\b(?:critical\s+hit|crit(?:s|ted)?)\b", re.I),
    re.compile(r"\b(?:advantage|disadvantage)\b.*\b(?:roll|d20)\b", re.I),
    re.compile(r"\bmagical\s+energy\b", re.I),
    re.compile(r"\b(?:fireball|magic\s+missile|cure\s+wounds)\b", re.I),
    # Invented attack outcomes (soft-RP must not narrate hit/miss without tools)
    re.compile(r"\b(?:your|the)\s+(?:swing|blow|strike|attack)\s+miss(?:es|ed)?\b", re.I),
    re.compile(r"\bmiss(?:es|ed)?\s+(?:the\s+)?(?:table|target|goblin|door|orc)\b", re.I),
    re.compile(r"\b(?:hits?|strikes?|connects?)\s+(?:the\s+)?(?:table|target|goblin|door)\b", re.I),
    re.compile(r"\bnot even close\b", re.I),
]

_CAST_SPELL_RE = re.compile(
    r"\bcast(?:s|ing)?\s+(?:the\s+spell\s+)?([A-Za-z][A-Za-z'\-]*(?:\s+[A-Za-z][A-Za-z'\-]*){0,3})",
    re.I,
)

# Discourse / filler after the spell name: "i cast fireball instead"
_SPELL_TRAILING_STOP = frozenset({
    "instead", "again", "now", "please", "too", "asap", "quickly", "immediately",
    "first", "next", "though", "then", "here", "there", "anyway", "actually",
})

# High-precision AUTO intents (enough info to resolve without asking).
_AUTO_REST_RE = re.compile(r"\b(?:take|takes|taking|i\s+take)\s+(?:a\s+)?(?:short|long)\s+rest\b", re.I)
_AUTO_REST_RE2 = re.compile(r"\b(?:short|long)\s+rest\b", re.I)
_AUTO_ROLL_RE = re.compile(
    r"\b(?:roll|make)\s+(?:a\s+)?(?:\w+\s+)?(?:check|save|saving\s+throw)\b",
    re.I,
)
_AUTO_DICE_RE = re.compile(r"\broll\s+\d*d\d+\b", re.I)
_AUTO_DEATH_RE = re.compile(r"\bdeath\s+save\b", re.I)
_AUTO_INIT_RE = re.compile(r"\b(?:roll\s+)?initiative\b", re.I)

# Ambiguous mechanical intents → clarify (do not force tools / invent outcomes).
_CLARIFY_ATTACK_RE = re.compile(
    r"\b(?:i\s+)?(?:attack|strike|shoot|stab|slash|hit|smash|punch|swing|cut|cleave|"
    r"kick|slap|smack|headbutt)\b",
    re.I,
)
_CLARIFY_ACTION_RE = re.compile(
    r"\b(?:i\s+)?(?:dash|dodge|disengage|hide|sneak|grapple|shove|help|ready|search)\b",
    re.I,
)
_CLARIFY_TRY_RE = re.compile(
    r"\b(?:i\s+)?(?:try|attempt)\s+to\s+\w+",
    re.I,
)

# Weapon-ish tokens only — do NOT match "with you" / "with her" (false attack cues).
_WEAPON_METHOD_WORDS = (
    r"sword|longsword|shortsword|greatsword|axe|bow|dagger|mace|spear|staff|club|"
    r"unarmed|fist|fists|hands|rapier|greataxe|battleaxe|crossbow|javelin|"
    r"quarterstaff|improvised|scimitar|warhammer|handaxe|shortbow|longbow"
)

# Attack is "clear enough" for AUTO only when method is specified (weapon/unarmed/etc).
_ATTACK_METHOD_RE = re.compile(
    rf"\b(?:with\s+(?:my\s+|the\s+)?(?:{_WEAPON_METHOD_WORDS})|"
    rf"using\s+(?:my\s+|the\s+)?(?:{_WEAPON_METHOD_WORDS})|"
    rf"my\s+(?:{_WEAPON_METHOD_WORDS})|"
    rf"(?:{_WEAPON_METHOD_WORDS})|bare\s+hands)\b",
    re.I,
)

_CLARIFY_TEMPLATES = {
    "attack": (
        "How do you attack — which weapon or unarmed — and what exactly are you "
        "trying to do to the target?"
    ),
    "dash": "Are you using the Dash action (move up to your speed again), or just describing hurried movement?",
    "dodge": "Confirm you want to take the Dodge action this turn?",
    "disengage": "Confirm you want to take the Disengage action this turn?",
    "hide": "Are you attempting the Hide action? Where are you trying to hide?",
    "sneak": "Are you trying to Hide, move quietly (Stealth), or something else?",
    "grapple": "Who are you trying to grapple, and do you confirm the Grapple special attack?",
    "shove": "Who or what are you shoving, and do you want to push or knock prone?",
    "help": "Who are you Helping, and with what task or attack?",
    "ready": "What trigger are you Readying for, and what action will you take?",
    "search": "What are you searching for, and where?",
    "try": "How are you attempting that — which ability or skill are you relying on?",
    "action": "What exactly are you trying to do, and how (ability, skill, or equipment)?",
}


class IntentTier(str, Enum):
    AUTO = "auto"
    CLARIFY = "clarify"
    NARRATIVE = "narrative"


def prose_claims_mechanics(text: str) -> bool:
    """True if narration appears to invent dice/HP/spell outcomes."""
    if not text or not text.strip():
        return False
    stripped = re.sub(
        r"TOOL_CALL\s*.*?END_TOOL_CALL",
        " ",
        text,
        flags=re.DOTALL | re.IGNORECASE,
    )
    for pat in _CLAIM_PATTERNS:
        if pat.search(stripped):
            return True
    return False


def extract_cast_spell_name(text: str) -> Optional[str]:
    """Best-effort spell name from 'I cast Fireball' style text."""
    if not text:
        return None
    m = _CAST_SPELL_RE.search(text.strip())
    if not m:
        return None
    name = m.group(1).strip(" .,!?:;\"'")
    stop = {"at", "on", "the", "a", "an", "my", "with", "towards", "toward"}
    parts = [w for w in name.split() if w.lower() not in stop]
    # Drop trailing filler so "fireball instead" → Fireball
    while parts and parts[-1].lower() in _SPELL_TRAILING_STOP:
        parts.pop()
    if not parts:
        return None
    return " ".join(p.capitalize() for p in parts)


def classify_player_intent(text: str) -> Tuple[IntentTier, str]:
    """
    Classify player text into AUTO / CLARIFY / NARRATIVE.

    Returns (tier, subtype) e.g. (IntentTier.CLARIFY, "attack").
    """
    if not text or not text.strip():
        return IntentTier.NARRATIVE, "empty"

    raw = text.strip()

    # AUTO: cast with extractable spell name
    spell = extract_cast_spell_name(raw)
    if spell and re.search(r"\bcast\b", raw, re.I):
        return IntentTier.AUTO, "cast"

    # AUTO: rest / explicit roll / death save / initiative
    if _AUTO_REST_RE.search(raw) or (
        _AUTO_REST_RE2.search(raw) and re.search(r"\b(?:rest|take|taking)\b", raw, re.I)
    ):
        return IntentTier.AUTO, "rest"
    if _AUTO_DICE_RE.search(raw) or _AUTO_ROLL_RE.search(raw):
        return IntentTier.AUTO, "roll"
    if _AUTO_DEATH_RE.search(raw):
        return IntentTier.AUTO, "death_save"
    if _AUTO_INIT_RE.search(raw):
        return IntentTier.AUTO, "initiative"

    # Attack with method and/or a target → AUTO; inventory chooser picks / clarifies weapon
    if _CLARIFY_ATTACK_RE.search(raw):
        from .attack_resolve import parse_attack_utterance

        target, method = parse_attack_utterance(raw)
        if method or _ATTACK_METHOD_RE.search(raw) or target:
            return IntentTier.AUTO, "attack_clear"
        # Bare "I attack" with no target/method → ask how
        return IntentTier.CLARIFY, "attack"

    # Other ambiguous actions
    for subtype, pattern in (
        ("dash", re.compile(r"\bdash\b", re.I)),
        ("dodge", re.compile(r"\bdodge\b", re.I)),
        ("disengage", re.compile(r"\bdisengage\b", re.I)),
        ("hide", re.compile(r"\bhide\b", re.I)),
        ("sneak", re.compile(r"\bsneak\b", re.I)),
        ("grapple", re.compile(r"\bgrapple\b", re.I)),
        ("shove", re.compile(r"\bshove\b", re.I)),
        ("help", re.compile(r"\b(?:i\s+)?help\b", re.I)),
        ("ready", re.compile(r"\bready\b", re.I)),
        ("search", re.compile(r"\bsearch\b", re.I)),
    ):
        if pattern.search(raw):
            return IntentTier.CLARIFY, subtype

    if _CLARIFY_TRY_RE.search(raw):
        return IntentTier.CLARIFY, "try"

    if _CLARIFY_ACTION_RE.search(raw):
        return IntentTier.CLARIFY, "action"

    # Cast without a usable spell name → clarify, don't invent
    if re.search(r"\bi\s+cast\b|\bcast\s+a\s+spell\b", raw, re.I):
        return IntentTier.CLARIFY, "cast_unclear"

    return IntentTier.NARRATIVE, "roleplay"


def clarification_prompt(subtype: str) -> str:
    """Fixed clarifying question so the local LLM cannot invent outcomes."""
    if subtype == "cast_unclear":
        return "Which spell are you casting, exactly?"
    return _CLARIFY_TEMPLATES.get(subtype, _CLARIFY_TEMPLATES["action"])


def has_attack_method(text: str) -> bool:
    """True if text names a weapon / unarmed / improvised method."""
    return bool(text and _ATTACK_METHOD_RE.search(text))


def player_requests_mechanics(text: str) -> bool:
    """True if intent is AUTO (needs tools). Kept for callers; prefer classify_player_intent."""
    tier, _ = classify_player_intent(text)
    return tier == IntentTier.AUTO
