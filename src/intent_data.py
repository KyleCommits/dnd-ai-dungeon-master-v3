"""Labeled intent examples. Data, not keyword lists — the classifier's whole brain."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import List

_REPO_ROOT = Path(__file__).resolve().parent.parent
EXAMPLES_PATH = _REPO_ROOT / "data" / "intent" / "examples.jsonl"
EVAL_PATH = _REPO_ROOT / "tests" / "data" / "intent_eval.jsonl"

# The eight semantic actions a player can express. "unclear" is deliberately absent:
# it is a decision-policy outcome, not something a player says.
VALID_ACTIONS = frozenset({
    "attack", "cast", "rest", "roll", "use_item", "move", "speak", "repeat_last",
})


@dataclass(frozen=True)
class Example:
    text: str
    action: str


def load_examples(path: Path) -> List[Example]:
    """Parse a JSONL file of {"text", "action"}. Raises on anything malformed."""
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"intent example file missing: {path}")

    out: List[Example] = []
    for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        line = line.strip()
        if not line or line.startswith("//"):
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"{path}:{lineno} is not valid JSON: {exc}") from exc

        text = str(row.get("text", "")).strip()
        action = str(row.get("action", "")).strip().lower()
        if not text:
            raise ValueError(f"{path}:{lineno} has empty text")
        if action not in VALID_ACTIONS:
            raise ValueError(f"{path}:{lineno} has unknown action {action!r}")
        out.append(Example(text=text, action=action))

    if not out:
        raise ValueError(f"{path} contains no examples")
    return out
