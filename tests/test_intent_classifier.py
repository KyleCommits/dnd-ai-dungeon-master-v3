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


def test_non_positive_k_still_returns_one_neighbor():
    """k=0 must not produce an empty vote and an IndexError on ranked[0]."""
    for k in (0, -3):
        out = ic.classify("SPEAK hello", k=k)
        assert len(out.neighbors) == 1
        assert out.action == "speak"


def test_all_negative_similarities_do_not_invert_the_vote(monkeypatch):
    """Negative similarities clamp to zero, so an opposing neighbor cannot vote."""
    monkeypatch.setattr(
        ic.embedder, "encode", lambda texts: np.array([[-1.0, 0.0]], dtype=np.float32)
    )
    out = ic.classify("anything", k=3)
    assert out.margin == 0.0
    assert out.top_score == 0.0
    assert all(sim <= 0.0 for _t, _a, sim in out.neighbors)


def test_blank_input_never_invokes_the_model(monkeypatch):
    """The blank short circuit must come before encoding, or a stray keystroke
    pays a full model load."""
    def boom(texts):
        raise AssertionError("the embedder must not run for blank input")

    monkeypatch.setattr(ic.embedder, "encode", boom)
    assert ic.classify("").action == "speak"
    assert ic.classify("   \n\t ").action == "speak"


def test_reset_cache_forces_a_matrix_rebuild(monkeypatch):
    """The autouse fixture replaces _load_examples_cached, so the real caching in it
    is otherwise never exercised. Stub one level lower to reach it."""
    monkeypatch.undo()

    builds = {"n": 0}
    examples = [Example("hello", "speak"), Example("i attack the table", "attack")]
    matrix = np.array([[1.0, 0.0], [0.0, 1.0]], dtype=np.float32)

    def counting_build(exs, emb, cache_path):
        builds["n"] += 1
        return matrix

    monkeypatch.setattr(ic, "load_examples", lambda path: examples)
    monkeypatch.setattr(ic, "build_matrix", counting_build)
    monkeypatch.setattr(
        ic.embedder, "encode", lambda texts: np.array([[1.0, 0.0]], dtype=np.float32)
    )

    ic.reset_cache()
    ic.classify("hello")
    ic.classify("hello")
    assert builds["n"] == 1, "the matrix should be built once and then cached"

    ic.reset_cache()
    ic.classify("hello")
    assert builds["n"] == 2, "reset_cache must force a rebuild"


# --- Regression gate. These load the real model, hence the slow marker. ---------
# Never lower a threshold here to make a run pass. Add labeled examples to
# data/intent/examples.jsonl and re-run scripts/eval_intent.py instead.

MECHANICS = ("attack", "cast")


def _gated_action(text: str, margin: float) -> str:
    out = ic.classify(text)
    return out.action if out.margin >= margin else "speak"


@pytest.mark.slow
def test_eval_set_has_zero_speech_to_mechanics_leaks(monkeypatch):
    """The catastrophic failure: in-character speech resolving as an attack or cast."""
    monkeypatch.undo()  # use the real classifier, not the stub fixture
    ic.reset_cache()

    from src.intent_config import mechanics_margin
    from src.intent_data import EVAL_PATH, load_examples

    margin = mechanics_margin()
    leaks = [
        (ex.text, _gated_action(ex.text, margin))
        for ex in load_examples(EVAL_PATH)
        if ex.action == "speak" and _gated_action(ex.text, margin) in MECHANICS
    ]
    assert not leaks, f"speech leaked into mechanics: {leaks}"


@pytest.mark.slow
def test_non_speech_rarely_leaks_into_mechanics(monkeypatch):
    """use_item / roll / move / rest misrouting to mechanics is wrong but recoverable.

    Held to a budget rather than zero, since these do not corrupt state the way
    misrouted speech does.
    """
    monkeypatch.undo()
    ic.reset_cache()

    from src.intent_config import mechanics_margin
    from src.intent_data import EVAL_PATH, load_examples

    margin = mechanics_margin()
    leaks = [
        (ex.text, ex.action, _gated_action(ex.text, margin))
        for ex in load_examples(EVAL_PATH)
        if ex.action not in MECHANICS
        and ex.action != "speak"
        and _gated_action(ex.text, margin) in MECHANICS
    ]
    assert len(leaks) <= 2, f"too many non-speech leaks into mechanics: {leaks}"


@pytest.mark.slow
def test_playtest_regressions_route_correctly(monkeypatch):
    """Every line from the broken 2026-07-26 session."""
    monkeypatch.undo()
    ic.reset_cache()

    cases = [
        ("hello!", "speak"),
        ("i say hello", "speak"),
        ("im sorry that i destroyed your tables. will 1000 gold cover the damage?", "speak"),
        ('i say "sorry about the tables"', "speak"),
        ("i attack the table", "attack"),
        # Playtest 2026-07-27: "again" was outvoted by past-tense table speak examples.
        ("i attack the table again", "attack"),
        ("i attack Mira", "attack"),
    ]
    failures = [
        (text, want, ic.classify(text).action)
        for text, want in cases
        if ic.classify(text).action != want
    ]
    assert not failures, f"playtest regressions: {failures}"


@pytest.mark.slow
def test_eval_accuracy_floor(monkeypatch):
    monkeypatch.undo()
    ic.reset_cache()

    from src.intent_data import EVAL_PATH, load_examples

    rows = load_examples(EVAL_PATH)
    correct = sum(1 for ex in rows if ic.classify(ex.text).action == ex.action)
    accuracy = correct / len(rows)
    # Measured 100% on 2026-07-27 after the calibration data rounds. The floor sits
    # well below that so normal variation does not fail the build, while a real
    # regression does.
    assert accuracy >= 0.93, f"accuracy regressed to {accuracy:.1%}"


@pytest.mark.slow
def test_real_mechanics_survive_the_gate(monkeypatch):
    """The gate's cost side. A margin tuned only for safety silently stops play."""
    monkeypatch.undo()
    ic.reset_cache()

    from src.intent_config import mechanics_margin
    from src.intent_data import EVAL_PATH, load_examples

    margin = mechanics_margin()
    rows = [ex for ex in load_examples(EVAL_PATH) if ex.action in MECHANICS]
    kept = [ex for ex in rows if _gated_action(ex.text, margin) == ex.action]
    recall = len(kept) / len(rows)
    lost = [ex.text for ex in rows if _gated_action(ex.text, margin) != ex.action]
    assert recall >= 0.90, f"gate downgraded too many real actions ({recall:.1%}): {lost}"
