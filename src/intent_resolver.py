# src/intent_resolver.py
"""Layer 2–3: validate structured intent and execute GameActions. Engine is authority."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set

from .attack_resolve import format_attack_reply
from .game_actions import game_actions
from .pending_clarify import set_pending_clarify
from .player_intent import PlayerIntent

logger = logging.getLogger(__name__)


@dataclass
class IntentOutcome:
    handled: bool
    reply: str = ""
    results: List[Dict[str, Any]] = field(default_factory=list)
    intent: Optional[PlayerIntent] = None


def _method_arg(intent: PlayerIntent) -> str:
    if intent.method == "unarmed":
        return "unarmed"
    if intent.method == "improvised":
        return "improvised"
    if intent.method == "unknown":
        return ""  # should not resolve — clarify first
    if intent.weapon_hint:
        return intent.weapon_hint
    if intent.method == "weapon":
        return ""  # chooser: equipped / clarify
    return intent.weapon_hint or ""


async def _resolve_attack(
    intent: PlayerIntent,
    character_id: str,
    allowed: Set[str],
    user_id: Optional[str],
) -> IntentOutcome:
    from .tool_executor import execute_tool_calls

    target = intent.target or "object"
    method = _method_arg(intent)
    args = {
        "character_id": str(character_id),
        "target_name": target,
        "method": method,
        "target_kind": "object",
    }

    if "resolve_player_attack" in allowed:
        auto_results = await execute_tool_calls(
            [{"name": "resolve_player_attack", "arguments": args}],
            allowed_names=allowed,
        )
        res = (auto_results[0].get("result") if auto_results else None) or {}
        if auto_results and auto_results[0].get("error"):
            return IntentOutcome(
                handled=True,
                reply=f"ERROR: {auto_results[0]['error']}",
                results=auto_results,
                intent=intent,
            )
    else:
        res = await game_actions.resolve_player_attack(**args)
        auto_results = [{"name": "resolve_player_attack", "arguments": args, "result": res}]

    if res.get("success"):
        return IntentOutcome(
            handled=True,
            reply=format_attack_reply(res),
            results=auto_results,
            intent=intent,
        )

    if res.get("needs_clarify"):
        prompt = res.get("message") or res.get("prompt") or "Which weapon?"
        if user_id:
            set_pending_clarify(
                user_id,
                "attack_weapon",
                intent.raw or f"I attack the {target}",
                options=res.get("options") or [],
            )
        return IntentOutcome(
            handled=True,
            reply=prompt,
            results=auto_results,
            intent=intent,
        )

    err = res.get("error") or res.get("message") or "attack failed"
    return IntentOutcome(
        handled=True,
        reply=f"ERROR: {err}",
        results=auto_results,
        intent=intent,
    )


async def _resolve_cast(
    intent: PlayerIntent,
    character_id: str,
    allowed: Set[str],
) -> IntentOutcome:
    from .tool_executor import _backend_cast_tools, format_mechanics_summary

    spell = intent.spell_name or "that spell"
    # Reuse backend cast tools with a synthetic message for extractors
    fake_msg = f"I cast {spell}"
    auto_results = await _backend_cast_tools(fake_msg, str(character_id), allowed)
    if not auto_results:
        # Direct validate path when tools not in allowlist
        legality = await game_actions._validate_spell_cast(str(character_id), spell)
        if not legality.get("success"):
            err = legality.get("message") or legality.get("error") or "Casting failed."
            return IntentOutcome(
                handled=True,
                reply=(
                    f"You begin the gestures for {spell}, but nothing happens. {err} "
                    f"No spell effect takes place.\n\n[mechanics] cast blocked: {err}"
                ),
                intent=intent,
            )
        return IntentOutcome(handled=False, intent=intent)

    mechanics = format_mechanics_summary(auto_results)
    failed = False
    err = "Casting failed."
    for item in auto_results:
        name = item.get("name")
        if name not in ("consume_spell_slot", "lookup_spell"):
            continue
        if item.get("error"):
            failed = True
            err = str(item["error"])
            break
        res = item.get("result") or {}
        if res.get("success") is False:
            failed = True
            err = res.get("message") or res.get("error") or err
            break

    if failed:
        return IntentOutcome(
            handled=True,
            reply=(
                f"You begin the gestures for {spell}, but nothing happens. {err} "
                f"No spell effect takes place.\n\n[mechanics] cast blocked: {err}"
            ),
            results=auto_results,
            intent=intent,
        )

    # Success: let caller narrate with mechanics, or return mechanics-only
    return IntentOutcome(
        handled=True,
        reply=mechanics,
        results=auto_results,
        intent=intent,
    )


async def resolve_intent(
    intent: PlayerIntent,
    character_id: Optional[str],
    allowed: Set[str],
    user_id: Optional[str] = None,
) -> IntentOutcome:
    """
    Validate + execute attack/cast intents. Other actions → handled=False (DM path).
    """
    # method=unknown always asks how (even if needs_clarify was missed)
    if intent.action == "attack" and intent.method == "unknown":
        intent.needs_clarify = True
        intent.clarify_prompt = intent.clarify_prompt or (
            "How are you attacking — which weapon or unarmed?"
        )

    if intent.needs_clarify:
        prompt = intent.clarify_prompt or "What exactly are you trying to do?"
        if user_id:
            subtype = "cast_unclear" if intent.action == "cast" else (
                "attack" if intent.action == "attack" else "action"
            )
            set_pending_clarify(user_id, subtype, intent.raw or "", options=[])
        return IntentOutcome(handled=True, reply=prompt, intent=intent)

    if not character_id and intent.action in ("attack", "cast"):
        return IntentOutcome(
            handled=True,
            reply="ERROR: no active character for that action.",
            intent=intent,
        )

    if intent.action == "attack":
        return await _resolve_attack(intent, str(character_id), allowed, user_id)

    if intent.action == "cast":
        return await _resolve_cast(intent, str(character_id), allowed)

    return IntentOutcome(handled=False, intent=intent)
