# tests/test_intent_classifier.py
import numpy as np
import pytest

import src.intent_classifier as ic
from src.intent_data import Example


@pytest.fixture(autouse=True)
def stub_backend(monkeypatch):
    """Two orthogonal axes: 'speak' on axis 0, 'attack' on axis 1."""
    examples = [
        Example("hello", "speak"),
        Example("hi there", "speak"),
        Example("good evening", "speak"),
        Example("i attack the table", "attack"),
        Example("i hit the goblin", "attack"),
        Example("i punch the guard", "attack"),
    ]
    matrix = np.array(
        [[1.0, 0.0], [1.0, 0.0], [1.0, 0.0], [0.0, 1.0], [0.0, 1.0], [0.0, 1.0]],
        dtype=np.float32,
    )

    def fake_encode(texts):
        out = []
        for t in texts:
            if t == "AMBIGUOUS":
                out.append([0.707, 0.707])
            elif t.startswith("SPEAK"):
                out.append([1.0, 0.0])
            else:
                out.append([0.0, 1.0])
        return np.array(out, dtype=np.float32)

    monkeypatch.setattr(ic, "_load_examples_cached", lambda: (examples, matrix))
    monkeypatch.setattr(ic.embedder, "encode", fake_encode)
    ic.reset_cache()
    yield
    ic.reset_cache()


def test_classifies_speech():
    out = ic.classify("SPEAK hello")
    assert out.action == "speak"
    assert out.margin > 0.5


def test_classifies_attack():
    out = ic.classify("ATTACK the table")
    assert out.action == "attack"
    assert out.margin > 0.5


def test_ambiguous_input_produces_low_margin():
    # k=6 spans the whole 3-speak/3-attack corpus, so a midpoint query ties exactly.
    out = ic.classify("AMBIGUOUS", k=6)
    assert out.margin < 0.01


def test_neighbors_are_returned_for_debugging():
    out = ic.classify("SPEAK hello", k=3)
    assert len(out.neighbors) == 3
    for text, action, sim in out.neighbors:
        assert isinstance(text, str) and isinstance(action, str)
        assert -1.0 <= sim <= 1.0


def test_empty_text_is_speak_with_zero_margin():
    out = ic.classify("   ")
    assert out.action == "speak"
    assert out.margin == 0.0


def test_k_larger_than_corpus_is_clamped():
    out = ic.classify("SPEAK hello", k=999)
    assert len(out.neighbors) == 6
    assert out.action == "speak"
