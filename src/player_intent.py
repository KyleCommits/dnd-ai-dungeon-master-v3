# src/player_intent.py
"""Layer 1: structured player intent. An embedding kNN classifier picks the action and
closed-set matching fills the slots; the engine still owns every rule.

The small intent LLM is demoted to a comparison baseline behind INTENT_BACKEND=llm.
"""

from __future__ import annotations

import json
import logging
import os
import re
from dataclasses import asdict, dataclass
from typing import Any, Dict, Optional, Sequence

from .mechanics_claims import clarification_prompt
from .intent_classifier import classify
from .intent_config import intent_backend as _intent_backend
from .intent_config import mechanics_margin as _mechanics_margin
from .intent_slots import fill as fill_slots

logger = logging.getLogger(__name__)

_INTENT_JSON_RE = re.compile(r"\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}", re.DOTALL)

_VALID_ACTIONS = frozenset({
    "attack", "cast", "rest", "roll", "use_item", "move", "speak",
    "repeat_last", "unclear",
})
_VALID_METHODS = frozenset({"unarmed", "weapon", "improvised", "unknown"})

_UNARMED_ALIASES = frozenset({
    "fist", "fists", "punch", "kick", "slap", "smack", "headbutt",
    "elbow", "knee", "bare hands", "bare hand", "unarmed strike", "hands",
})

# Discourse framing (not attack-verb lists): player is speaking, not striking.
_SPEECH_ACT_RE = re.compile(
    r"^\s*i\s+(?:say|said|tell|told|ask|asked|whisper(?:s|ed)?|shout(?:s|ed)?|"
    r"reply|replied|answer(?:s|ed)?)\b",
    re.I,
)
_QUOTED_DIALOGUE_RE = re.compile(r'''["“][^"”]{2,}["”]''')


def is_speech_act(text: str) -> bool:
    """True when the utterance is framed as dialogue ('i say …' / quotes)."""
    raw = (text or "").strip()
    if not raw:
        return False
    return bool(_SPEECH_ACT_RE.search(raw) or _QUOTED_DIALOGUE_RE.search(raw))

@dataclass
class PlayerIntent:
    action: str = "unclear"
    target: Optional[str] = None
    method: Optional[str] = None  # unarmed | weapon | improvised | unknown
    weapon_hint: Optional[str] = None
    spell_name: Optional[str] = None
    needs_clarify: bool = False
    clarify_prompt: Optional[str] = None
    confidence: float = 0.0
    raw: str = ""
    # embed | speech_act | last_attack | intent_llm | rules | pending
    source: str = "intent_llm"

    def as_dict(self) -> Dict[str, Any]:
        return asdict(self)


def _rules_fallback_enabled() -> bool:
    try:
        from .config import settings

        return bool(getattr(settings, "INTENT_RULES_FALLBACK", False))
    except Exception:
        return os.environ.get("INTENT_RULES_FALLBACK", "").lower() in (
            "1", "true", "yes",
        )


def _normalize_method(
    method: Optional[str],
    weapon_hint: Optional[str],
) -> Optional[str]:
    if method:
        m = method.strip().lower()
        if m in ("", "null", "none"):
            method = None
        elif m in _VALID_METHODS:
            return m
        elif m in _UNARMED_ALIASES:
            return "unarmed"
        else:
            # Unknown token from model → treat as weapon hint path
            return "weapon"

    if weapon_hint:
        h = weapon_hint.strip().lower()
        if h in _UNARMED_ALIASES or h == "unarmed":
            return "unarmed"
        return "weapon"
    return None


def _apply_attack_clarify_policy(intent: PlayerIntent) -> PlayerIntent:
    """method=unknown always clarifies; bare attack with no target/method clarifies."""
    if intent.action != "attack":
        return intent

    if intent.method == "unknown":
        intent.needs_clarify = True
        intent.clarify_prompt = intent.clarify_prompt or clarification_prompt("attack")
        return intent

    if not intent.target and not intent.method and not intent.weapon_hint:
        intent.needs_clarify = True
        intent.clarify_prompt = intent.clarify_prompt or clarification_prompt("attack")
    return intent


def intent_from_rules(text: str) -> PlayerIntent:
    """
    Legacy keyword mapper — test helper / optional debug fallback only.
    Not the live primary path when INTENT_RULES_FALLBACK is false.
    """
    from .attack_resolve import parse_attack_utterance
    from .mechanics_claims import (
        IntentTier,
        classify_player_intent,
        extract_cast_spell_name,
    )

    raw = (text or "").strip()
    if not raw:
        return PlayerIntent(action="speak", raw=raw, confidence=1.0, source="rules")

    tier, subtype = classify_player_intent(raw)

    if tier == IntentTier.CLARIFY:
        if subtype == "cast_unclear":
            action = "cast"
        elif subtype == "attack":
            action = "attack"
        else:
            action = "unclear"
        return PlayerIntent(
            action=action,
            needs_clarify=True,
            clarify_prompt=clarification_prompt(subtype),
            confidence=0.9,
            raw=raw,
            source="rules",
        )

    if tier == IntentTier.AUTO and subtype == "cast":
        spell = extract_cast_spell_name(raw)
        return PlayerIntent(
            action="cast",
            spell_name=spell,
            needs_clarify=not bool(spell),
            clarify_prompt="Which spell are you casting, exactly?" if not spell else None,
            confidence=0.95,
            raw=raw,
            source="rules",
        )

    if tier == IntentTier.AUTO and subtype == "rest":
        return PlayerIntent(action="rest", confidence=0.95, raw=raw, source="rules")

    if tier == IntentTier.AUTO and subtype in ("roll", "death_save", "initiative"):
        return PlayerIntent(action="roll", confidence=0.9, raw=raw, source="rules")

    if tier == IntentTier.AUTO and subtype == "attack_clear":
        target, method = parse_attack_utterance(raw)
        method_norm = None
        weapon_hint = None
        if method:
            ml = method.strip().lower()
            if ml in _UNARMED_ALIASES or ml == "unarmed":
                method_norm = "unarmed"
            else:
                method_norm = "weapon"
                weapon_hint = method
        return _apply_attack_clarify_policy(
            PlayerIntent(
                action="attack",
                target=target,
                method=method_norm,
                weapon_hint=weapon_hint,
                needs_clarify=False,
                confidence=0.9,
                raw=raw,
                source="rules",
            )
        )

    return PlayerIntent(
        action="speak",
        confidence=0.7,
        raw=raw,
        source="rules",
    )


def parse_intent_json(blob: str, raw: str) -> Optional[PlayerIntent]:
    """Parse model JSON into PlayerIntent; None if invalid."""
    if not blob or not blob.strip():
        return None
    text = blob.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.I)
    text = re.sub(r"\s*```$", "", text)
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        m = _INTENT_JSON_RE.search(text)
        if not m:
            return None
        try:
            data = json.loads(m.group(0))
        except json.JSONDecodeError:
            return None

    if not isinstance(data, dict):
        return None

    # ChatGPT-style "intent" alias
    action = str(data.get("action") or data.get("intent") or "unclear").strip().lower()
    if action not in _VALID_ACTIONS:
        action = "unclear"

    method = data.get("method")
    if method is not None:
        method = str(method).strip().lower()
        if method in ("", "null", "none"):
            method = None

    weapon_hint = data.get("weapon_hint") or data.get("weapon")
    if weapon_hint is not None:
        weapon_hint = str(weapon_hint).strip() or None

    spell_name = data.get("spell_name")
    if spell_name is not None:
        spell_name = str(spell_name).strip() or None
        if spell_name:
            spell_name = " ".join(p.capitalize() for p in spell_name.split())

    target = data.get("target")
    if target is not None:
        target = str(target).strip() or None

    needs = bool(data.get("needs_clarify"))
    prompt = data.get("clarify_prompt")
    if prompt is not None:
        prompt = str(prompt).strip() or None

    try:
        conf = float(data.get("confidence", 0.6))
    except (TypeError, ValueError):
        conf = 0.6

    if method == "unknown":
        method_norm: Optional[str] = "unknown"
    else:
        method_norm = _normalize_method(method, weapon_hint)

    if action == "cast" and not spell_name:
        needs = True
        prompt = prompt or "Which spell are you casting, exactly?"

    if needs and not prompt:
        prompt = clarification_prompt("action")

    intent = PlayerIntent(
        action=action,
        target=target,
        method=method_norm,
        weapon_hint=weapon_hint,
        spell_name=spell_name,
        needs_clarify=needs,
        clarify_prompt=prompt,
        confidence=max(0.0, min(1.0, conf)),
        raw=raw,
        source="intent_llm",
    )
    return _apply_attack_clarify_policy(intent)


def fail_closed_clarify(raw: str, reason: str = "parse") -> PlayerIntent:
    logger.info("Intent fail-closed (%s): %s", reason, (raw or "")[:80])
    return PlayerIntent(
        action="unclear",
        needs_clarify=True,
        clarify_prompt=clarification_prompt("action"),
        confidence=0.0,
        raw=(raw or "").strip(),
        source="intent_llm",
    )


def normalize_intent_post_llm(intent: PlayerIntent) -> PlayerIntent:
    """Retained for the demoted llm backend; _parse_via_llm is the only caller."""
    if intent.action == "repeat_last":
        intent.needs_clarify = False
        intent.clarify_prompt = None
        return intent
    if intent.action == "attack":
        return _apply_attack_clarify_policy(intent)
    return intent


def intent_from_last_attack_memory(
    user_id: str,
    raw: str = "",
    *,
    weapon_override: Optional[str] = None,
) -> Optional[PlayerIntent]:
    """Build an attack intent from the last resolved attack (repeat_last / follow-up)."""
    from .last_attack import get_last_attack

    last = get_last_attack(user_id)
    if not last:
        return None
    weapon = (weapon_override if weapon_override is not None else last.weapon) or ""
    weapon = weapon.strip()
    unarmed = weapon.lower() == "unarmed"
    return PlayerIntent(
        action="attack",
        target=last.target,
        method="unarmed" if unarmed else ("weapon" if weapon else None),
        weapon_hint=None if unarmed else (weapon or None),
        confidence=1.0,
        raw=raw or last.raw,
        source="last_attack",
    )


LLM_MIN_CONFIDENCE = 0.35


async def _parse_via_llm(
    raw: str,
    weapon_names: Optional[Sequence[str]],
    npc_names: Optional[Sequence[str]],
) -> PlayerIntent:
    """Legacy Qwen2.5-1.5B JSON path. Reachable only via INTENT_BACKEND=llm.

    This is not the pre-redesign live path. It keeps the JSON parse, the attack
    clarify policy, and the low-confidence clarify gate, but the old
    is_social_dialogue override is gone for good: it was a keyword list, and
    replacing keyword lists with labeled data is the point of the redesign. So an
    apology this model reads as an attack now reaches the resolver, where world
    validation is the only thing stopping it. Treat this backend as a measurement
    baseline, not as something safe to ship.
    """
    try:
        from .intent_llm import intent_llm
        from .target_resolve import list_known_npc_names

        npcs = list(npc_names) if npc_names is not None else list_known_npc_names()
        out = await intent_llm.generate_intent_json(
            raw, weapon_names=weapon_names, npc_names=npcs
        )
        parsed = parse_intent_json(out or "", raw)
        if parsed is None:
            return fail_closed_clarify(raw, "bad_json")
        parsed = normalize_intent_post_llm(parsed)
        # This model's self-reported confidence is noisy, but a number it labels
        # low is still the only uncertainty signal the JSON path has.
        if parsed.confidence < LLM_MIN_CONFIDENCE and parsed.action not in (
            "speak",
            "repeat_last",
        ):
            parsed.needs_clarify = True
            parsed.clarify_prompt = parsed.clarify_prompt or clarification_prompt(
                "action"
            )
        return parsed
    except Exception as exc:
        logger.warning("Intent LLM failed: %s", exc)
        return fail_closed_clarify(raw, "timeout_or_error")


async def parse_player_intent(
    text: str,
    *,
    weapon_names: Optional[Sequence[str]] = None,
    npc_names: Optional[Sequence[str]] = None,
    spell_names: Optional[Sequence[str]] = None,
    use_intent_llm: bool = True,
    force_rules: bool = False,
) -> PlayerIntent:
    """
    Embedding classifier decides the action; closed sets fill the slots.

    Mechanics actions must clear both the margin gate and slot resolution.
    Everything else becomes speak, which cannot corrupt game state.

    spell_names has no production caller yet: run_tool_loop does not forward one,
    so live casts take the "no list available" branch in intent_slots._fill_cast
    and intent_resolver._resolve_cast remains the only legality check. Tests and
    the eval harness pass it to exercise the closed-set path.

    use_intent_llm is accepted for signature compatibility and ignored. The
    backend is chosen by INTENT_BACKEND, not per call.
    """
    raw = (text or "").strip()
    if not raw:
        return PlayerIntent(action="speak", raw=raw, confidence=1.0, source="rules")

    # Structural dialogue framing — punctuation and syntax, not a verb list.
    if is_speech_act(raw) and not force_rules:
        return PlayerIntent(
            action="speak", confidence=1.0, raw=raw, source="speech_act"
        )

    if force_rules or _rules_fallback_enabled():
        return intent_from_rules(raw)

    if _intent_backend() == "llm":
        return await _parse_via_llm(raw, weapon_names, npc_names)

    try:
        result = classify(raw)
    except Exception as exc:
        logger.warning("Intent classifier failed, narrating instead: %s", exc)
        return PlayerIntent(action="speak", confidence=0.0, raw=raw, source="embed")

    action = result.action

    if action not in ("attack", "cast"):
        return PlayerIntent(
            action=action,
            confidence=result.margin,
            raw=raw,
            source="embed",
        )

    try:
        from .target_resolve import list_known_npc_names

        npcs = list(npc_names) if npc_names is not None else list_known_npc_names()
        slots = fill_slots(
            raw,
            action,
            weapon_names=weapon_names,
            npc_names=npcs,
            spell_names=spell_names,
        )
    except Exception as exc:
        logger.warning("Slot filling failed, narrating instead: %s", exc)
        return PlayerIntent(action="speak", confidence=0.0, raw=raw, source="embed")

    margin_ok = result.margin >= _mechanics_margin()
    if not margin_ok or not slots.resolved:
        logger.info(
            "Mechanics downgraded to speak: action=%s margin=%.3f resolved=%s raw=%r",
            action,
            result.margin,
            slots.resolved,
            raw[:80],
        )
        return PlayerIntent(
            action="speak", confidence=result.margin, raw=raw, source="embed"
        )

    return PlayerIntent(
        action=action,
        target=slots.target,
        method=slots.method,
        weapon_hint=slots.weapon_hint,
        spell_name=slots.spell_name,
        needs_clarify=False,
        confidence=result.margin,
        raw=raw,
        source="embed",
    )
