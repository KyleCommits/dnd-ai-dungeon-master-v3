# scripts/eval_intent.py
"""Score an intent backend against the held-out eval set.

Usage:
  python scripts/eval_intent.py
  python scripts/eval_intent.py --margin 0.15
  python scripts/eval_intent.py --backend llm --limit 20

Both backends are scored raw, without the is_speech_act pre-pass that runs ahead of
them in parse_player_intent. That pre-pass is backend-independent, so including it
would flatter whichever backend is worse at quoted dialogue rather than measuring the
backends themselves.
"""

from __future__ import annotations

import argparse
import asyncio
import statistics
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import List, Sequence, Tuple

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.intent_classifier import classify  # noqa: E402
from src.intent_config import mechanics_margin  # noqa: E402
from src.intent_data import EVAL_PATH, VALID_ACTIONS, Example, load_examples  # noqa: E402

MECHANICS = ("attack", "cast")

SWEEP_STEP = 0.02
SWEEP_MAX = 0.40


@dataclass
class Scored:
    action: str
    margin: float


Result = Tuple[Example, Scored]
Gated = Tuple[Example, str]


# Two failure severities, deliberately counted apart. Merging them hides the only
# number that matters: speech mutating game state is catastrophic, while
# use_item misread as attack is merely wrong.
def _speech_to_mechanics(rows: Sequence[Gated]) -> List[Gated]:
    return [(ex, g) for ex, g in rows if ex.action == "speak" and g in MECHANICS]


def _other_to_mechanics(rows: Sequence[Gated]) -> List[Gated]:
    return [
        (ex, g)
        for ex, g in rows
        if ex.action not in MECHANICS and ex.action != "speak" and g in MECHANICS
    ]


def _score_embed(text: str, k: int) -> Scored:
    out = classify(text, k=k)
    return Scored(action=out.action, margin=out.margin)


async def _score_llm_all(texts: Sequence[str]) -> List[Scored]:
    """Legacy Qwen backend. Its self-reported confidence stands in for a margin.

    That confidence is not comparable to an embedding margin -- the model emits it
    freehand and it clusters at 0.9 -- so read the llm sweep as a rough shape, not as
    a threshold you could adopt.
    """
    from src.intent_llm import intent_llm
    from src.player_intent import parse_intent_json

    scored: List[Scored] = []
    for i, text in enumerate(texts, 1):
        try:
            blob = await intent_llm.generate_intent_json(text)
            parsed = parse_intent_json(blob or "", text)
        except Exception as exc:  # a dead backend should not abort the run
            print(f"  [{i}/{len(texts)}] ERROR: {exc}")
            scored.append(Scored(action="unclear", margin=0.0))
            continue
        if parsed is None:
            scored.append(Scored(action="unclear", margin=0.0))
        else:
            scored.append(Scored(action=parsed.action, margin=parsed.confidence))
        if i % 10 == 0:
            print(f"  scored {i}/{len(texts)} ...")
    return scored


def _collect(rows: Sequence[Example], backend: str, k: int) -> Tuple[List[Result], List[float]]:
    results: List[Result] = []
    latencies: List[float] = []

    if backend == "embed":
        for ex in rows:
            t0 = time.perf_counter()
            out = _score_embed(ex.text, k)
            latencies.append((time.perf_counter() - t0) * 1000.0)
            results.append((ex, out))
        return results, latencies

    t0 = time.perf_counter()
    scored = asyncio.run(_score_llm_all([ex.text for ex in rows]))
    elapsed_ms = (time.perf_counter() - t0) * 1000.0
    # The llm path is timed in bulk; per-row timing would mostly measure model warmup.
    per_row = elapsed_ms / max(1, len(rows))
    latencies = [per_row] * len(rows)
    return list(zip(rows, scored)), latencies


def _report_accuracy(results: Sequence[Result], latencies: Sequence[float]) -> None:
    correct = sum(1 for ex, out in results if out.action == ex.action)
    print(f"Accuracy: {correct}/{len(results)} = {correct / len(results):.1%}")
    print(f"Latency p50: {statistics.median(latencies):.1f}ms")
    ordered = sorted(latencies)
    p95 = ordered[max(0, int(len(ordered) * 0.95) - 1)]
    print(f"Latency p95: {p95:.1f}ms\n")


def _report_per_class(results: Sequence[Result]) -> None:
    print("Per-class precision / recall:")
    for action in sorted(VALID_ACTIONS):
        tp = sum(1 for ex, o in results if o.action == action and ex.action == action)
        fp = sum(1 for ex, o in results if o.action == action and ex.action != action)
        fn = sum(1 for ex, o in results if o.action != action and ex.action == action)
        if tp + fn == 0:
            continue
        prec = tp / (tp + fp) if (tp + fp) else 0.0
        rec = tp / (tp + fn)
        print(f"  {action:12s} precision={prec:6.1%} recall={rec:6.1%} (n={tp + fn})")

    misses = [(ex, o) for ex, o in results if o.action != ex.action]
    print(f"\nMisclassifications ({len(misses)}):")
    for ex, out in misses:
        print(
            f"  {ex.text[:58]:58s} want={ex.action:10s} got={out.action:10s} "
            f"margin={out.margin:.3f}"
        )


def _gate(results: Sequence[Result], margin: float) -> List[Gated]:
    return [(ex, out.action if out.margin >= margin else "speak") for ex, out in results]


def _report_sweep(results: Sequence[Result]) -> None:
    print("\nMargin sweep (pick the LOWEST margin with zero speech leaks):")
    header = f"  {'margin':>8s} {'speech->mech':>13s} {'other->mech':>12s} {'mech recall':>12s}"
    print(header)
    steps = int(round(SWEEP_MAX / SWEEP_STEP)) + 1
    for i in range(steps):
        candidate = round(SWEEP_STEP * i, 2)
        gated = _gate(results, candidate)
        speech_leaks = len(_speech_to_mechanics(gated))
        other_leaks = len(_other_to_mechanics(gated))
        mech_total = sum(1 for ex, _ in gated if ex.action in MECHANICS)
        mech_kept = sum(1 for ex, g in gated if ex.action in MECHANICS and g == ex.action)
        recall = mech_kept / mech_total if mech_total else 0.0
        flag = "  <- no speech leaks" if speech_leaks == 0 else ""
        print(
            f"  {candidate:8.2f} {speech_leaks:13d} {other_leaks:12d} {recall:11.1%}{flag}"
        )


def _downgraded_mechanics(results: Sequence[Result], margin: float) -> List[Result]:
    """Correctly classified attacks/casts the gate would turn into narration.

    This is the cost side of the threshold. Reporting only the leak count makes a
    margin of 1.0 look perfect, when it would mean no attack ever rolls dice.
    """
    return [
        (ex, out)
        for ex, out in results
        if ex.action in MECHANICS and out.action == ex.action and out.margin < margin
    ]


def _report_mechanics_headroom(results: Sequence[Result]) -> None:
    """Correct attacks/casts nearest the cut, and wrong ones furthest above it.

    These two lists are what a threshold choice actually trades off, and they name
    the utterances to add examples for when the gate cannot be raised for free.
    """
    correct = sorted(
        (
            (ex, out) for ex, out in results
            if ex.action in MECHANICS and out.action == ex.action
        ),
        key=lambda pair: pair[1].margin,
    )
    print("\nCorrect mechanics rows nearest the cut (raise these with more examples):")
    for ex, out in correct[:6]:
        print(f"  {out.margin:6.3f}  {ex.action:6s} {ex.text[:56]}")

    wrong = sorted(
        (
            (ex, out) for ex, out in results
            if ex.action not in MECHANICS and out.action in MECHANICS
        ),
        key=lambda pair: -pair[1].margin,
    )
    print("Non-mechanics rows the classifier called mechanics:")
    if not wrong:
        print("  (none)")
    for ex, out in wrong[:6]:
        print(f"  {out.margin:6.3f}  want={ex.action:9s} {ex.text[:50]}")


def _recommend(results: Sequence[Result]) -> None:
    steps = int(round(SWEEP_MAX / SWEEP_STEP)) + 1
    candidates = [round(SWEEP_STEP * i, 2) for i in range(steps)]

    clean = [c for c in candidates if not _speech_to_mechanics(_gate(results, c))]
    if not clean:
        print(
            f"\nNo margin up to {SWEEP_MAX:.2f} eliminates speech leaks. Add labeled "
            f"examples for the leaking lines instead of raising the threshold."
        )
        return

    print(f"\nLowest margin with zero speech-to-mechanics leaks: {clean[0]:.2f}")

    # When the eval set has no leaks at any threshold the sweep cannot pick a value,
    # and the lowest is 0.00, which disables the gate. The gate exists for utterances
    # the eval set does not contain, so take the most protection that is measurably
    # free: the highest margin still costing no mechanics recall.
    free = [c for c in clean if not _downgraded_mechanics(results, c)]
    if free:
        print(
            f"Highest margin that downgrades no correct mechanics action: {max(free):.2f}"
        )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--k", type=int, default=5)
    parser.add_argument(
        "--margin",
        type=float,
        default=None,
        help="gate to report on; defaults to the live INTENT_MECHANICS_MARGIN",
    )
    parser.add_argument("--backend", choices=("embed", "llm"), default="embed")
    parser.add_argument(
        "--limit",
        type=int,
        default=0,
        help="score only the first N rows (the llm backend is slow)",
    )
    args = parser.parse_args()

    margin = mechanics_margin() if args.margin is None else args.margin

    rows = load_examples(EVAL_PATH)
    if args.limit > 0:
        rows = rows[: args.limit]

    print(
        f"Scoring {len(rows)} held-out utterances "
        f"(backend={args.backend}, k={args.k}, margin={margin:.2f})\n"
    )

    results, latencies = _collect(rows, args.backend, args.k)

    _report_accuracy(results, latencies)
    _report_per_class(results)
    _report_sweep(results)
    _report_mechanics_headroom(results)
    _recommend(results)

    gated = _gate(results, margin)
    speech_leaks = _speech_to_mechanics(gated)
    other_leaks = _other_to_mechanics(gated)
    print(f"\nAt margin {margin:.2f}:")
    print(f"  speech -> mechanics: {len(speech_leaks)} (must be zero)")
    for ex, g in speech_leaks:
        print(f"    {ex.text[:58]:58s} -> {g}")
    print(f"  other non-mechanics -> mechanics: {len(other_leaks)} (should be low)")
    for ex, g in other_leaks:
        print(f"    {ex.text[:58]:58s} want={ex.action:9s} -> {g}")

    downgraded = _downgraded_mechanics(results, margin)
    print(f"  correct mechanics lost to the gate: {len(downgraded)} (the cost side)")
    for ex, out in downgraded:
        print(f"    {ex.text[:58]:58s} {ex.action:9s} margin={out.margin:.3f}")

    if speech_leaks:
        print(
            "\nERROR: speech is leaking into mechanics. Add examples covering these "
            "lines to data/intent/examples.jsonl."
        )
        return 1
    print("\n[OK] no speech-to-mechanics errors")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
