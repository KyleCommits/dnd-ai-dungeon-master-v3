"""Layer 1 slot filling: match nouns against closed sets the database can prove exist.

Runs only after the classifier has decided the action, so the extraction regexes in
attack_resolve are answering "which target" rather than "is this an attack".
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Optional, Sequence

logger = logging.getLogger(__name__)

_PRONOUNS = frozenset({
    "you", "yourself", "u", "me", "myself", "self", "her", "him", "them", "it",
    "player", "pc", "character", "they", "he", "she",
})


@dataclass(frozen=True)
class Slots:
    target: Optional[str] = None
    weapon_hint: Optional[str] = None
    method: Optional[str] = None
    spell_name: Optional[str] = None
    resolved: bool = True


def _match_closed_set(value: str, candidates: Sequence[str]) -> Optional[str]:
    """Case-insensitive exact match, then containment. Returns the canonical name."""
    needle = (value or "").strip().lower()
    if not needle:
        return None
    for cand in candidates or ():
        if needle == str(cand).strip().lower():
            return str(cand)
    for cand in candidates or ():
        cand_l = str(cand).strip().lower()
        if needle in cand_l.split() or cand_l.startswith(needle):
            return str(cand)
    return None


def _fill_attack(
    text: str,
    weapon_names: Sequence[str],
    npc_names: Sequence[str],
) -> Slots:
    from .attack_resolve import parse_attack_utterance
    from .player_intent import _UNARMED_ALIASES

    target, method_raw = parse_attack_utterance(text)

    if not target or target.strip().lower() in _PRONOUNS:
        return Slots(resolved=False)

    canonical = _match_closed_set(target, npc_names)
    target_out = canonical or target.strip()

    method: Optional[str] = None
    weapon_hint: Optional[str] = None
    if method_raw:
        raw_l = method_raw.strip().lower()
        if raw_l in _UNARMED_ALIASES or raw_l == "unarmed":
            method = "unarmed"
        else:
            matched = _match_closed_set(method_raw, weapon_names)
            if matched:
                weapon_hint = matched
                method = "weapon"
            else:
                logger.info("Weapon %r not in inventory; deferring choice", method_raw)

    return Slots(
        target=target_out,
        weapon_hint=weapon_hint,
        method=method,
        resolved=True,
    )


def _fill_cast(text: str, spell_names: Optional[Sequence[str]]) -> Slots:
    from .mechanics_claims import extract_cast_spell_name

    named = extract_cast_spell_name(text)
    if not named:
        return Slots(resolved=False)

    # No spell list supplied: the caller has no spellbook handy, so trust the extracted
    # name and let intent_resolver._resolve_cast run the real legality check. Treating
    # this as unresolved would silently downgrade every cast to narration.
    if spell_names is None:
        return Slots(spell_name=named, resolved=True)

    canonical = _match_closed_set(named, spell_names)
    if not canonical:
        logger.info("Spell %r not available to this character", named)
        return Slots(spell_name=named, resolved=False)
    return Slots(spell_name=canonical, resolved=True)


def fill(
    text: str,
    action: str,
    *,
    weapon_names: Optional[Sequence[str]] = None,
    npc_names: Optional[Sequence[str]] = None,
    spell_names: Optional[Sequence[str]] = None,
) -> Slots:
    """Extract slots for mechanics actions. Non-mechanics actions need no slots."""
    if action == "attack":
        return _fill_attack(text, weapon_names or (), npc_names or ())
    if action == "cast":
        # Pass spell_names through untouched: None means "no list available", which is
        # different from an empty list meaning "this character knows no spells".
        return _fill_cast(text, spell_names)
    return Slots(resolved=True)
