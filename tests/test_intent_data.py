import json

import pytest

from src.intent_data import (
    EVAL_PATH,
    EXAMPLES_PATH,
    VALID_ACTIONS,
    load_examples,
)


def test_examples_load_and_are_valid():
    examples = load_examples(EXAMPLES_PATH)
    assert len(examples) >= 100
    for ex in examples:
        assert ex.text.strip(), "empty text"
        assert ex.action in VALID_ACTIONS, ex.action


def test_eval_set_loads():
    rows = load_examples(EVAL_PATH)
    assert len(rows) >= 40


def test_train_and_eval_are_disjoint():
    train = {ex.text.strip().lower() for ex in load_examples(EXAMPLES_PATH)}
    holdout = {ex.text.strip().lower() for ex in load_examples(EVAL_PATH)}
    overlap = train & holdout
    assert not overlap, f"eval leaks into training: {sorted(overlap)[:5]}"


def test_speak_and_attack_both_well_represented():
    counts = {}
    for ex in load_examples(EXAMPLES_PATH):
        counts[ex.action] = counts.get(ex.action, 0) + 1
    assert counts.get("speak", 0) >= 30
    assert counts.get("attack", 0) >= 25


def test_unclear_is_not_a_label():
    assert "unclear" not in VALID_ACTIONS


def test_malformed_line_raises(tmp_path):
    bad = tmp_path / "bad.jsonl"
    bad.write_text('{"text": "hi", "action": "nonsense"}\n', encoding="utf-8")
    with pytest.raises(ValueError, match="nonsense"):
        load_examples(bad)


def test_missing_file_raises(tmp_path):
    with pytest.raises(FileNotFoundError):
        load_examples(tmp_path / "nope.jsonl")
