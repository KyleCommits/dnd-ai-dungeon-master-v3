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

logger = logging.getLogger(__name__)

TOOL_CALL_RE = re.compile(
    r"TOOL_CALL\s*\n\s*(\{.*?\})\s*\n\s*END_TOOL_CALL",
    re.DOTALL | re.IGNORECASE,
)


def extract_tool_calls(text: str) -> List[Dict[str, Any]]:
    """Extract {name, arguments} dicts from TOOL_CALL ... END_TOOL_CALL blocks."""
    calls: List[Dict[str, Any]] = []
    if not text:
        return calls

    for match in TOOL_CALL_RE.finditer(text):
        raw = match.group(1).strip()
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError as e:
            logger.warning("Invalid TOOL_CALL JSON: %s (%s)", raw, e)
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

    return calls


def strip_tool_calls(text: str) -> str:
    """Remove TOOL_CALL blocks from player-facing text."""
    if not text:
        return ""
    cleaned = TOOL_CALL_RE.sub("", text)
    # collapse excess blank lines
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


async def run_tool_loop(
    initial_prompt: str,
    available_functions: List[Dict[str, Any]],
    generate_fn,
    max_rounds: int = 2,
    max_new_tokens: int = 250,
    max_narration_tokens: int = 200,
) -> str:
    """
    Generate → parse tools → execute → (optional) second generate with results.

    generate_fn(prompt, max_new_tokens=, available_functions=) -> str
    """
    allowed = {f["name"] for f in available_functions}
    prompt = initial_prompt
    last_text = ""

    for round_idx in range(max_rounds):
        text = await generate_fn(
            prompt,
            max_new_tokens=max_new_tokens,
            available_functions=available_functions,
        )
        last_text = text or ""
        calls = extract_tool_calls(last_text)

        if not calls:
            return strip_tool_calls(last_text)

        results = await execute_tool_calls(calls, allowed_names=allowed)
        mechanics = format_mechanics_summary(results)
        cleaned = strip_tool_calls(last_text)

        # Final round or prepare follow-up narration
        if round_idx >= max_rounds - 1:
            if cleaned:
                return f"{cleaned}\n\n{mechanics}".strip()
            return mechanics

        prompt = (
            f"{initial_prompt}\n\n"
            f"You previously requested tool calls. Here are the REAL results:\n"
            f"{mechanics}\n\n"
            f"Your draft (tool blocks removed):\n{cleaned or '(none)'}\n\n"
            f"Write the final DM narration for the player using these results. "
            f"Do NOT emit TOOL_CALL blocks this time. Keep it concise (2-4 sentences)."
        )
        # Next iteration: generate without tools so we get clean narration
        available_functions = []  # no tools on follow-up
        max_new_tokens = max_narration_tokens

    return strip_tool_calls(last_text)
