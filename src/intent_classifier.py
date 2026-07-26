# src/intent_classifier.py
"""Layer 1 action classification: embedding kNN over labeled examples."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Tuple

import numpy as np

from .intent_config import embed_k
from .intent_data import EXAMPLES_PATH, Example, load_examples
from .intent_embed import build_matrix, embedder

logger = logging.getLogger(__name__)

CACHE_PATH = Path(EXAMPLES_PATH).parent / "embeddings.npz"

_cache: Optional[Tuple[List[Example], np.ndarray]] = None


@dataclass(frozen=True)
class Classification:
    action: str
    margin: float
    top_score: float
    neighbors: List[Tuple[str, str, float]]


def reset_cache() -> None:
    """Drop the in-process example/matrix cache. Used by tests."""
    global _cache
    _cache = None


def _load_examples_cached() -> Tuple[List[Example], np.ndarray]:
    global _cache
    if _cache is None:
        examples = load_examples(EXAMPLES_PATH)
        matrix = build_matrix(examples, embedder, CACHE_PATH)
        _cache = (examples, matrix)
    return _cache


def classify(text: str, *, k: Optional[int] = None) -> Classification:
    """Similarity-weighted vote over the k nearest labeled examples."""
    raw = (text or "").strip()
    if not raw:
        return Classification(action="speak", margin=0.0, top_score=0.0, neighbors=[])

    k = embed_k() if k is None else k
    examples, matrix = _load_examples_cached()
    query = embedder.encode([raw])[0]
    sims = matrix @ query

    k = max(1, min(k, len(examples)))
    top_idx = np.argsort(-sims)[:k]

    neighbors: List[Tuple[str, str, float]] = [
        (examples[i].text, examples[i].action, float(sims[i])) for i in top_idx
    ]

    # Similarity-weighted vote. Clamp negatives so an opposing neighbor cannot
    # subtract from a class total.
    scores: dict[str, float] = {}
    for i in top_idx:
        weight = max(0.0, float(sims[i]))
        scores[examples[i].action] = scores.get(examples[i].action, 0.0) + weight

    ranked = sorted(scores.items(), key=lambda kv: kv[1], reverse=True)
    best_action, best_score = ranked[0]
    runner_up = ranked[1][1] if len(ranked) > 1 else 0.0
    total = sum(scores.values()) or 1.0

    return Classification(
        action=best_action,
        margin=float((best_score - runner_up) / total),
        top_score=float(best_score / total),
        neighbors=neighbors,
    )
