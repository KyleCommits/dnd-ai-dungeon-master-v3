# src/last_attack.py
"""In-memory last resolved attack so 'try again' / 'use my sword' can continue."""

from __future__ import annotations

import re
import time
from dataclasses import dataclass
from typing import Dict, Optional

_TTL_SEC = 600

_TRY_AGAIN_RE = re.compile(
    r"^(?:(?:and|once)\s+)?(?:i\s+)?(?:try\s+again|go\s+again|again|once\s+more)"
    r"(?:\s*[.!])?$",
    re.I,
)

# Weapon/method-only follow-up without a new target sentence
_METHOD_ONLY_RE = re.compile(
    r"^(?:this\s+time\s+)?(?:i\s+)?(?:use|using|with|wield|grab)\s+"
    r"(?:my\s+|the\s+)?[\w\-]+(?:\s*[.!])?$",
    re.I,
)


@dataclass
class LastAttack:
    target: str
    weapon: str
    raw: str
    created_at: float


_LAST: Dict[str, LastAttack] = {}


def set_last_attack(
    user_id: str,
    target: str,
    weapon: str,
    raw: str = "",
) -> None:
    if not user_id:
        return
    _LAST[user_id] = LastAttack(
        target=(target or "object").strip(),
        weapon=(weapon or "").strip(),
        raw=(raw or "").strip(),
        created_at=time.time(),
    )


def clear_last_attack(user_id: str) -> None:
    if user_id:
        _LAST.pop(user_id, None)


def get_last_attack(user_id: str) -> Optional[LastAttack]:
    if not user_id:
        return None
    last = _LAST.get(user_id)
    if not last:
        return None
    if time.time() - last.created_at > _TTL_SEC:
        _LAST.pop(user_id, None)
        return None
    return last


def is_try_again(text: str) -> bool:
    return bool(text and _TRY_AGAIN_RE.match(text.strip()))


def is_method_only_followup(text: str) -> bool:
    return bool(text and _METHOD_ONLY_RE.match(text.strip()))


def extract_method_from_followup(text: str) -> str:
    """Best-effort weapon phrase from 'i use my sword' / 'with my longsword'."""
    raw = (text or "").strip()
    m = re.search(
        r"(?:use|using|with|wield|grab)\s+(?:my\s+|the\s+)?(.+?)\s*$",
        raw,
        re.I,
    )
    if not m:
        return raw
    return m.group(1).strip(" .,!")


def rewrite_from_last_attack(user_id: str, new_message: str) -> Optional[str]:
    """
    If this is a continuation of the last attack, return a concrete attack line.
    """
    last = get_last_attack(user_id)
    if not last:
        return None
    raw = (new_message or "").strip()
    if is_try_again(raw):
        weapon = last.weapon or "equipped weapon"
        return f"I attack the {last.target} with {weapon}"
    if is_method_only_followup(raw):
        method = extract_method_from_followup(raw) or last.weapon
        return f"I attack the {last.target} with {method}"
    return None
