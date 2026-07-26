# src/target_resolve.py
"""Resolve attack targets against world state — not English keyword lists."""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional


@dataclass
class TargetRef:
    kind: str  # npc | object | unknown
    name: str
    npc_key: Optional[str] = None


def list_known_npc_names() -> List[str]:
    """NPC display names from campaign world memory (hints for IntentLLM)."""
    try:
        from .campaign_state_manager import campaign_state_manager

        state = campaign_state_manager.current_state
        if not state or not getattr(state, "npc_relationships", None):
            return []
        names: List[str] = []
        for key, rel in state.npc_relationships.items():
            label = getattr(rel, "name", None) or key
            label = str(label).replace("_", " ").strip()
            if label:
                names.append(label)
        return names
    except Exception:
        return []


def resolve_attack_target(target: Optional[str]) -> TargetRef:
    """
    Map a free-text target to npc | object | unknown using world memory.
    Unknown → caller should clarify (do not invent pronoun furniture).
    """
    raw = (target or "").strip()
    if not raw:
        return TargetRef(kind="unknown", name="")

    lower = raw.lower()
    # Pure pronouns / self — not world entities
    if lower in {
        "you", "yourself", "u", "me", "myself", "self", "her", "him", "them",
        "player", "pc", "character",
    }:
        return TargetRef(kind="unknown", name=raw)

    try:
        from .campaign_state_manager import campaign_state_manager

        state = campaign_state_manager.current_state
        if state and getattr(state, "npc_relationships", None):
            for key, rel in state.npc_relationships.items():
                name = str(getattr(rel, "name", None) or key).replace("_", " ").strip()
                key_norm = str(key).replace("_", " ").strip().lower()
                if lower == name.lower() or lower == key_norm:
                    return TargetRef(kind="npc", name=name or raw, npc_key=str(key))
    except Exception:
        pass

    # Default: treat as scene object (table, door, …)
    return TargetRef(kind="object", name=raw)
