# src/pending_clarify.py
"""Short-lived pending clarification so follow-ups like 'i use my sword' resolve the prior ask."""

from __future__ import annotations

import re
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from .mechanics_claims import IntentTier, has_attack_method

# Follow-ups that supply method/weapon without repeating "attack"
_FOLLOWUP_METHOD_RE = re.compile(
    r"\b(?:use|using|with|grab|wield)\s+(?:my\s+|the\s+)?[\w\-]+|"
    r"\b(?:my\s+)?(?:longsword|shortsword|greatsword|scimitar|rapier|dagger|mace|"
    r"warhammer|battleaxe|greataxe|handaxe|javelin|spear|club|quarterstaff|"
    r"shortbow|longbow|crossbow|sword|axe|bow|staff|hammer|unarmed|fists?)\b",
    re.I,
)

_AFFIRM_RE = re.compile(
    r"^(?:yes|yeah|yep|ok|okay|sure|do\s+it|go\s+ahead)(?:\s*[.!])?$",
    re.I,
)
_NUMBER_RE = re.compile(r"^\d+$")

# Expire pending clarifies after 10 minutes
_TTL_SEC = 600

_ATTACK_SUBTYPES = frozenset({"attack", "attack_weapon"})


@dataclass
class PendingClarify:
    subtype: str
    original_message: str
    created_at: float
    options: List[str] = field(default_factory=list)


_PENDING: Dict[str, PendingClarify] = {}


def set_pending_clarify(
    user_id: str,
    subtype: str,
    original_message: str,
    options: Optional[List[str]] = None,
) -> None:
    if not user_id:
        return
    _PENDING[user_id] = PendingClarify(
        subtype=subtype,
        original_message=(original_message or "").strip(),
        created_at=time.time(),
        options=list(options or []),
    )


def clear_pending_clarify(user_id: str) -> None:
    if user_id:
        _PENDING.pop(user_id, None)


def get_pending_clarify(user_id: str) -> Optional[PendingClarify]:
    if not user_id:
        return None
    pending = _PENDING.get(user_id)
    if not pending:
        return None
    if time.time() - pending.created_at > _TTL_SEC:
        _PENDING.pop(user_id, None)
        return None
    return pending


def looks_like_method_followup(text: str) -> bool:
    if not text or not text.strip():
        return False
    raw = text.strip()
    if _AFFIRM_RE.match(raw):
        return True
    if _NUMBER_RE.match(raw):
        return True
    if has_attack_method(raw):
        return True
    if _FOLLOWUP_METHOD_RE.search(raw):
        return True
    # Short answer naming a gear item: "Longsword", "the battleaxe"
    words = raw.split()
    if 1 <= len(words) <= 5 and not re.search(r"[?]", raw):
        return True
    return False


def merge_attack_followup(original: str, followup: str) -> str:
    """Combine prior vague attack with method follow-up into one AUTO-ready line."""
    orig = (original or "").strip().rstrip(".")
    follow = (followup or "").strip()
    # Avoid duplicating "attack" if follow-up already has a full sentence
    if re.search(r"\battack\b", follow, re.I) and _FOLLOWUP_METHOD_RE.search(follow):
        return follow
    return f"{orig} — {follow}"


def resolve_pending_followup(
    user_id: str,
    new_message: str,
) -> Optional[Tuple[str, IntentTier, str]]:
    """
    If this message answers a pending clarify, return
    (enriched_player_message, IntentTier.AUTO, subtype) and clear pending.
    """
    pending = get_pending_clarify(user_id)
    if not pending:
        return None

    raw = (new_message or "").strip()

    if pending.subtype in _ATTACK_SUBTYPES and looks_like_method_followup(raw):
        # Map "1" → concrete option name when we stored a list
        follow = raw
        if _NUMBER_RE.match(raw) and pending.options:
            idx = int(raw) - 1
            if 0 <= idx < len(pending.options):
                follow = pending.options[idx]
        enriched = merge_attack_followup(pending.original_message, follow)
        clear_pending_clarify(user_id)
        return enriched, IntentTier.AUTO, "attack_clear"

    if pending.subtype == "cast_unclear":
        spellish = raw
        if spellish and len(spellish.split()) <= 4:
            clear_pending_clarify(user_id)
            return f"I cast {spellish}", IntentTier.AUTO, "cast"

    # Other subtypes: affirmation or method-ish follow-up → enriched AUTO-ish clarify resolve
    if looks_like_method_followup(raw) or _AFFIRM_RE.match(raw):
        enriched = f"{pending.original_message} — {raw}"
        clear_pending_clarify(user_id)
        return enriched, IntentTier.AUTO, pending.subtype

    return None
