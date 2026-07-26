# src/tool_executor.py
"""
Parse TOOL_CALL blocks from local LLM output and execute GameActions.
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any, Dict, List, Optional, Set

from .game_actions import game_actions
from .mechanics_claims import (
    IntentTier,
    clarification_prompt,
    classify_player_intent,
    extract_cast_spell_name,
    prose_claims_mechanics,
)
from .last_attack import (
    extract_method_from_followup,
    get_last_attack,
    is_method_only_followup,
    rewrite_from_last_attack,
)
from .pending_clarify import (
    resolve_pending_followup,
    set_pending_clarify,
)

logger = logging.getLogger(__name__)

TOOL_CALL_RE = re.compile(
    r"TOOL_CALL\s*\n+\s*(.*?)\s*\n+\s*END_TOOL_CALL",
    re.DOTALL | re.IGNORECASE,
)

FORCE_RETRY_NUDGE = (
    "SYSTEM: Mechanics were required but you emitted no valid TOOL_CALL. "
    "Emit the required TOOL_CALL / END_TOOL_CALL block(s) now using available "
    "functions, or explicitly say that no game state changes. Do not invent numbers."
)

CAST_FORCE_NUDGE = (
    "SYSTEM: The player attempted to CAST A SPELL. You MUST emit TOOL_CALL blocks now: "
    "lookup_spell then consume_spell_slot with spell_name and the active character_id. "
    "If tools return an error (e.g. Fighter cannot cast), narrate the failure — "
    "do NOT describe a successful spell."
)

NONBINDING_NOTE = (
    "[system] No tools ran; treat narrative numbers as non-binding."
)


def _normalize_tool_json(raw: str) -> str:
    """Strip fences and light-repair trailing commas before json.loads."""
    s = (raw or "").strip()
    if s.startswith("```"):
        s = re.sub(r"^```(?:json)?\s*", "", s, flags=re.IGNORECASE)
        s = re.sub(r"\s*```\s*$", "", s)
    s = s.strip()
    s = re.sub(r",\s*}", "}", s)
    s = re.sub(r",\s*]", "]", s)
    return s.strip()


def count_tool_call_markers(text: str) -> int:
    """Count TOOL_CALL open markers (for detecting failed parse attempts)."""
    if not text:
        return 0
    return len(re.findall(r"\bTOOL_CALL\b", text, flags=re.IGNORECASE))


def extract_tool_calls(text: str) -> List[Dict[str, Any]]:
    """Extract {name, arguments} dicts from TOOL_CALL ... END_TOOL_CALL blocks."""
    calls: List[Dict[str, Any]] = []
    if not text:
        return calls

    for match in TOOL_CALL_RE.finditer(text):
        raw = match.group(1).strip()
        normalized = _normalize_tool_json(raw)
        try:
            payload = json.loads(normalized)
        except json.JSONDecodeError as e:
            logger.warning(
                "Invalid TOOL_CALL JSON (unparseable block): %s (%s)",
                raw[:200],
                e,
            )
            continue

        name = payload.get("name")
        arguments = payload.get("arguments", {})
        if not name or not isinstance(name, str):
            logger.warning("TOOL_CALL missing name: %s", payload)
            continue
        if arguments is None:
            arguments = {}
        if not isinstance(arguments, dict):
            logger.warning("TOOL_CALL arguments must be an object: %s", payload)
            continue
        calls.append({"name": name, "arguments": arguments})

    markers = count_tool_call_markers(text)
    if markers and not calls:
        logger.warning(
            "TOOL_CALL markers present (%d) but no valid blocks parsed",
            markers,
        )

    return calls


def strip_tool_calls(text: str) -> str:
    """Remove TOOL_CALL blocks from player-facing text."""
    if not text:
        return ""
    cleaned = TOOL_CALL_RE.sub("", text)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned).strip()
    return cleaned


def format_mechanics_summary(results: List[Dict[str, Any]]) -> str:
    """Short mechanics summary for narration prompts / fallback replies."""
    if not results:
        return ""
    lines = ["Mechanics:"]
    for item in results:
        name = item.get("name", "?")
        if item.get("error"):
            lines.append(f"- {name}: ERROR {item['error']}")
            continue
        result = item.get("result") or {}
        msg = result.get("message") if isinstance(result, dict) else None
        if msg:
            lines.append(f"- {name}: {msg}")
        else:
            lines.append(f"- {name}: {json.dumps(result)[:200]}")
    return "\n".join(lines)


async def execute_tool_calls(
    calls: List[Dict[str, Any]],
    allowed_names: Optional[Set[str]] = None,
) -> List[Dict[str, Any]]:
    """
    Execute allowlisted GameActions methods.
    Returns list of {name, arguments, result} or {name, arguments, error}.
    """
    results: List[Dict[str, Any]] = []
    for call in calls:
        name = call["name"]
        arguments = call.get("arguments") or {}

        if allowed_names is not None and name not in allowed_names:
            results.append({
                "name": name,
                "arguments": arguments,
                "error": f"unknown or disallowed tool: {name}",
            })
            continue

        method = getattr(game_actions, name, None)
        if method is None or not callable(method):
            results.append({
                "name": name,
                "arguments": arguments,
                "error": f"no GameActions method named {name}",
            })
            continue

        try:
            result = await method(**arguments)
            results.append({
                "name": name,
                "arguments": arguments,
                "result": result,
            })
        except TypeError as e:
            results.append({
                "name": name,
                "arguments": arguments,
                "error": f"bad arguments: {e}",
            })
        except Exception as e:
            logger.exception("Tool execution failed for %s", name)
            results.append({
                "name": name,
                "arguments": arguments,
                "error": str(e),
            })

    return results


def _should_force_tool_retry(
    text: str,
    calls: List[Dict[str, Any]],
    player_message: Optional[str] = None,
    intent_tier: Optional[IntentTier] = None,
) -> bool:
    """Force a re-ask if prose invents mechanics, markers failed, or AUTO intent needs tools."""
    if calls:
        return False
    if intent_tier == IntentTier.AUTO:
        return True
    if intent_tier == IntentTier.CLARIFY:
        return False
    if prose_claims_mechanics(text):
        return True
    if count_tool_call_markers(text) > 0:
        return True
    return False


async def _backend_cast_tools(
    player_message: str,
    character_id: str,
    allowed: Set[str],
) -> List[Dict[str, Any]]:
    """When the LLM skips tools on a cast attempt, run lookup + consume ourselves."""
    spell_name = extract_cast_spell_name(player_message)
    if not spell_name or not character_id:
        return []
    if "lookup_spell" not in allowed and "consume_spell_slot" not in allowed:
        return []

    results: List[Dict[str, Any]] = []
    if "lookup_spell" in allowed:
        results = await execute_tool_calls(
            [{"name": "lookup_spell", "arguments": {"spell_name": spell_name}}],
            allowed_names=allowed,
        )

    spell_level = 1
    lookup_ok = False
    for item in results:
        res = item.get("result") or {}
        if item.get("name") == "lookup_spell" and res.get("success"):
            lookup_ok = True
            try:
                spell_level = int(res.get("level") if res.get("level") is not None else 1)
            except (TypeError, ValueError):
                spell_level = 1

    if not lookup_ok and results:
        return results  # unknown spell — surface lookup error

    if spell_level == 0:
        legality = await game_actions._validate_spell_cast(str(character_id), spell_name)
        results.append({
            "name": "consume_spell_slot",
            "arguments": {"character_id": str(character_id), "spell_name": spell_name},
            "result": legality if not legality.get("success") else {
                "success": True,
                "message": f"Cantrip {spell_name} allowed (no slot spent).",
            },
        })
        return results

    if "consume_spell_slot" in allowed:
        consume_results = await execute_tool_calls(
            [{
                "name": "consume_spell_slot",
                "arguments": {
                    "character_id": str(character_id),
                    "slot_level": max(spell_level, 1),
                    "spell_name": spell_name,
                },
            }],
            allowed_names=allowed,
        )
        results.extend(consume_results)

    return results


async def _backend_resolve_attack_reply(
    working_message: str,
    character_id: str,
    allowed: Set[str],
    user_id: Optional[str] = None,
) -> Optional[str]:
    """Full attack resolve without calling the LLM (solo default)."""
    from .attack_resolve import format_attack_reply, parse_attack_utterance

    target_name, method = parse_attack_utterance(working_message)
    if not target_name:
        target_name = "object"
    # Empty method → inventory chooser (equipped / clarify). Do NOT default to unarmed.
    method = method or ""

    args = {
        "character_id": str(character_id),
        "target_name": target_name,
        "method": method,
        "target_kind": "object",
    }

    def _handle_result(res: Dict[str, Any]) -> Optional[str]:
        if res.get("success"):
            return format_attack_reply(res)
        if res.get("needs_clarify"):
            prompt = res.get("message") or res.get("prompt") or "Which weapon?"
            if user_id:
                set_pending_clarify(
                    user_id,
                    "attack_weapon",
                    working_message,
                    options=res.get("options") or [],
                )
            return prompt
        if res.get("error"):
            return f"ERROR: {res['error']}"
        return None

    if "resolve_player_attack" in allowed:
        auto_results = await execute_tool_calls(
            [{"name": "resolve_player_attack", "arguments": args}],
            allowed_names=allowed,
        )
        res = (auto_results[0].get("result") if auto_results else None) or {}
        handled = _handle_result(res)
        if handled:
            return handled
        if auto_results and auto_results[0].get("error"):
            return f"ERROR: {auto_results[0]['error']}"
        return None

    res = await game_actions.resolve_player_attack(**args)
    handled = _handle_result(res)
    if handled:
        return handled
    return f"ERROR: {res.get('error') or res.get('message') or 'attack failed'}"


async def run_tool_loop(
    initial_prompt: str,
    available_functions: List[Dict[str, Any]],
    generate_fn,
    max_rounds: int = 2,
    max_new_tokens: int = 160,
    max_narration_tokens: int = 140,
    max_force_retries: int = 1,
    player_message: Optional[str] = None,
    character_id: Optional[str] = None,
    user_id: Optional[str] = None,
    weapon_names: Optional[List[str]] = None,
) -> str:
    """
    Layer 1 intent → resolve attack/cast on engine → else DM generate/tools.

    LLM narration never decides hit/damage/slots; resolve_intent is authority.
    """
    from . import player_intent as player_intent_mod
    from .intent_resolver import resolve_intent

    allowed = {f["name"] for f in available_functions}
    working_message = player_message or ""
    uid = user_id or "player1"

    # Answer to a prior clarifying question (e.g. "i use my sword" after "how do you attack?")
    resolved = resolve_pending_followup(uid, working_message)
    if resolved:
        working_message, intent_tier, intent_subtype = resolved
        player_intent = player_intent_mod.intent_from_rules(working_message)
        player_intent.source = "pending"
    else:
        intent_tier, intent_subtype = classify_player_intent(working_message)
        # Natural language → IntentLLM (primary). repeat_last hydrates from memory.
        player_intent = await player_intent_mod.parse_player_intent(
            working_message,
            weapon_names=weapon_names,
            use_intent_llm=True,
        )
        if player_intent.action == "repeat_last":
            hydrated = player_intent_mod.intent_from_last_attack_memory(
                uid, working_message
            )
            if hydrated:
                player_intent = hydrated
            # else resolve_intent will ask for a fresh attack
        elif (
            player_intent.action == "attack"
            and not player_intent.target
            and get_last_attack(uid)
        ):
            # Method-only follow-up from IntentLLM: reuse last target
            player_intent.target = get_last_attack(uid).target
            player_intent.source = "last_attack"
        elif player_intent.action == "speak":
            # Thin bridge if IntentLLM misses try-again / method-only phrasing
            rewritten = rewrite_from_last_attack(uid, working_message)
            if rewritten:
                logger.info(
                    "Last-attack rewrite (IntentLLM spoke): %r → %r",
                    working_message,
                    rewritten,
                )
                player_intent = player_intent_mod.intent_from_rules(rewritten)
                player_intent.source = "last_attack"
            elif is_method_only_followup(working_message) and get_last_attack(uid):
                method = extract_method_from_followup(working_message)
                hydrated = player_intent_mod.intent_from_last_attack_memory(
                    uid, working_message, weapon_override=method
                )
                if hydrated:
                    player_intent = hydrated

    cast_spell = player_intent.spell_name or extract_cast_spell_name(working_message)

    # Soft RP / speak: short GPU narrate WITHOUT the ~8k-char tool schema (was causing
    # ~4k-token prefills and 90s timeouts on "hello").
    if (
        player_intent.action == "speak"
        and not player_intent.needs_clarify
        and not cast_spell
    ):
        narrate = initial_prompt
        marker = "FUNCTION CALLING INSTRUCTIONS:"
        if marker in narrate:
            narrate = narrate.split(marker)[0].rstrip()
        narrate = (
            f"{narrate}\n\n"
            f'Player says: "{working_message}"\n'
            f"Respond as DM in 2-4 sentences of in-world narration only. "
            f"Do NOT emit TOOL_CALL. Do NOT invent dice, HP, damage, or spell effects. "
            f"Do NOT give yourself stage directions or tell the player what to type next."
        )
        try:
            text = await generate_fn(
                narrate,
                max_new_tokens=max_narration_tokens,
                available_functions=[],
            )
            cleaned = strip_tool_calls(text or "") or (
                "The scene holds for a moment as you take in your surroundings."
            )
            if prose_claims_mechanics(cleaned):
                last = get_last_attack(uid)
                # Never tell a greeter/speaker to name a weapon. Only offer
                # "try again" when we already have a last attack AND this isn't dialogue.
                if (
                    last
                    and not player_intent_mod.is_speech_act(working_message)
                ):
                    return (
                        f"Attack again with {last.weapon or 'your weapon'} against "
                        f"the {last.target}? Say \"try again\" or name the weapon."
                    )
                logger.warning(
                    "Speak narration claimed mechanics; using safe fallback"
                )
                return (
                    "The moment hangs in the air. Conversation continues around you — "
                    "no dice were rolled."
                )
            return cleaned
        except Exception:
            logger.exception("speak narration failed")
            return "The DM pauses, then nods for you to continue."

    # Layer 2–3: attack / cast / clarify via resolve_intent (before DM LLM)
    if (
        player_intent.action in ("attack", "cast", "unclear", "repeat_last")
        or player_intent.needs_clarify
    ):
        outcome = await resolve_intent(
            player_intent, character_id, allowed, user_id=uid
        )
        if outcome.handled:
            # Successful cast: optional short narration from tool results only
            if (
                player_intent.action == "cast"
                and outcome.results
                and "cast blocked" not in (outcome.reply or "")
                and character_id
            ):
                mechanics = outcome.reply
                narr_prompt = (
                    f"{initial_prompt}\n\n"
                    f"The player cast a spell. REAL tool results:\n{mechanics}\n\n"
                    f"Write 2-4 sentences of DM narration using ONLY these results. "
                    f"Do NOT emit TOOL_CALL blocks."
                )
                try:
                    narr = await generate_fn(
                        narr_prompt,
                        max_new_tokens=max_narration_tokens,
                        available_functions=[],
                    )
                    cleaned = strip_tool_calls(narr or "")
                    if cleaned and "cast blocked" not in cleaned.lower():
                        return f"{cleaned}\n\n{mechanics}".strip()
                except Exception:
                    logger.exception("cast narration failed; returning mechanics")
                return mechanics
            return outcome.reply

    # Legacy tier clarify (dash/hide/etc. not yet on PlayerIntent actions)
    if intent_tier == IntentTier.CLARIFY and player_intent.action == "speak":
        set_pending_clarify(uid, intent_subtype, working_message)
        return clarification_prompt(intent_subtype)

    prompt = initial_prompt
    if resolved:
        prompt = (
            f"{initial_prompt}\n\n"
            f"CLARIFICATION RESOLVED — the player's full action is now:\n"
            f"\"{working_message}\"\n"
            f"Resolve THIS with TOOL_CALL (e.g. roll_dice_for_character for an attack/smash). "
            f"Do not change the subject to unrelated tavern banter."
        )
    last_text = ""
    force_retries_used = 0
    funcs_for_gen = available_functions
    pending_mechanics = ""
    pending_results: List[Dict[str, Any]] = []
    base_prompt = prompt

    def _cast_failed(results: List[Dict[str, Any]]) -> Optional[str]:
        """Human message if lookup/consume rejected the cast."""
        for item in results:
            name = item.get("name")
            if name not in ("consume_spell_slot", "lookup_spell"):
                continue
            if item.get("error"):
                return str(item["error"])
            res = item.get("result") or {}
            if res.get("success") is False:
                return res.get("message") or res.get("error") or "Casting failed."
        return None

    def _hard_cast_refusal(results: List[Dict[str, Any]], mechanics: str) -> str:
        """Do not trust the LLM to honor a failed cast — return a fixed refusal."""
        err = _cast_failed(results) or "Casting failed."
        spell = cast_spell or "that spell"
        # Keep player-facing text short; full JSON dumps confuse the log.
        return (
            f"You begin the gestures for {spell}, but nothing happens. {err} "
            f"No spell effect takes place.\n\n[mechanics] cast blocked: {err}"
        )

    for round_idx in range(max_rounds):
        text = await generate_fn(
            prompt,
            max_new_tokens=max_new_tokens,
            available_functions=funcs_for_gen,
        )
        last_text = text or ""
        calls = extract_tool_calls(last_text)

        # Force re-ask when AUTO intent / claims / broken markers and no tools
        if (
            round_idx == 0
            and force_retries_used < max_force_retries
            and funcs_for_gen
            and _should_force_tool_retry(
                last_text, calls, player_message=player_message, intent_tier=intent_tier
            )
        ):
            force_retries_used += 1
            nudge = CAST_FORCE_NUDGE if cast_spell else FORCE_RETRY_NUDGE
            if intent_subtype == "attack_clear":
                nudge = (
                    "SYSTEM: The player is attacking with a stated method. "
                    "Emit roll_dice_for_character (or resolve_attack if in combat) NOW. "
                    "Do not invent hit/damage without a tool; do not ignore the attack."
                )
            prompt = (
                f"{base_prompt}\n\n"
                f"Your previous reply (invalid for mechanics):\n{strip_tool_calls(last_text) or last_text}\n\n"
                f"{nudge}"
            )
            text = await generate_fn(
                prompt,
                max_new_tokens=max_new_tokens,
                available_functions=funcs_for_gen,
            )
            last_text = text or ""
            calls = extract_tool_calls(last_text)

        if not calls:
            # Narration round after tools already ran — keep mechanics, never NONBINDING
            if pending_mechanics:
                cleaned = strip_tool_calls(last_text)
                if cast_spell and _cast_failed(pending_results):
                    return _hard_cast_refusal(pending_results, pending_mechanics)
                if cleaned:
                    return f"{cleaned}\n\n{pending_mechanics}".strip()
                return pending_mechanics

            # Backend safety net for AUTO cast attempts the model soft-narrated past
            if (
                intent_tier == IntentTier.AUTO
                and cast_spell
                and character_id
                and funcs_for_gen
            ):
                auto_results = await _backend_cast_tools(
                    working_message, str(character_id), allowed
                )
                if auto_results:
                    mechanics = format_mechanics_summary(auto_results)
                    if _cast_failed(auto_results):
                        return _hard_cast_refusal(auto_results, mechanics)
                    narr_prompt = (
                        f"{base_prompt}\n\n"
                        f"The player tried to cast a spell. Here are the REAL tool results "
                        f"(backend-enforced because you skipped TOOL_CALL):\n{mechanics}\n\n"
                        f"Write 2-4 sentences of DM narration using ONLY these results. "
                        f"If casting failed, the spell does not happen. "
                        f"Ignore any earlier chat where a spell seemed to work without tools. "
                        f"Do NOT emit TOOL_CALL blocks."
                    )
                    narr = await generate_fn(
                        narr_prompt,
                        max_new_tokens=max_narration_tokens,
                        available_functions=[],
                    )
                    cleaned = strip_tool_calls(narr or "")
                    return f"{cleaned}\n\n{mechanics}".strip() if cleaned else mechanics

            # Fallback if early attack resolve was skipped (no character_id earlier)
            if (
                intent_tier == IntentTier.AUTO
                and intent_subtype == "attack_clear"
                and character_id
            ):
                reply = await _backend_resolve_attack_reply(
                    working_message, str(character_id), allowed, user_id=uid
                )
                if reply:
                    return reply

            cleaned = strip_tool_calls(last_text)
            # NONBINDING only when prose invents numbers, or AUTO still has no tools
            if prose_claims_mechanics(cleaned) or (
                intent_tier == IntentTier.AUTO
                and _should_force_tool_retry(
                    last_text, calls, player_message=working_message, intent_tier=intent_tier
                )
            ):
                if cleaned:
                    return f"{cleaned}\n\n{NONBINDING_NOTE}".strip()
                return NONBINDING_NOTE
            return cleaned

        results = await execute_tool_calls(calls, allowed_names=allowed)
        mechanics = format_mechanics_summary(results)
        cleaned = strip_tool_calls(last_text)
        pending_mechanics = mechanics
        pending_results = results

        # Failed cast: do not ask the LLM to narrate (it will invent explosions from history)
        if cast_spell and _cast_failed(results):
            return _hard_cast_refusal(results, mechanics)

        if round_idx >= max_rounds - 1:
            if cleaned:
                return f"{cleaned}\n\n{mechanics}".strip()
            return mechanics

        prompt = (
            f"{base_prompt}\n\n"
            f"You previously requested tool calls. Here are the REAL results:\n"
            f"{mechanics}\n\n"
            f"Your draft (tool blocks removed):\n{cleaned or '(none)'}\n\n"
            f"Write the final DM narration for the player using these results. "
            f"If a cast/attack FAILED, that action did not happen — do not continue a prior "
            f"invented scene. Do NOT emit TOOL_CALL blocks. Keep it concise (2-4 sentences)."
        )
        funcs_for_gen = []
        max_new_tokens = max_narration_tokens

    if pending_mechanics:
        return f"{strip_tool_calls(last_text)}\n\n{pending_mechanics}".strip()
    return strip_tool_calls(last_text)
