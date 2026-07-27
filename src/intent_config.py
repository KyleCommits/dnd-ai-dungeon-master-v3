"""Intent settings. Reads os.environ first because src/config.py is gitignored and
declares fields explicitly, so undeclared keys never reach pydantic Settings."""

from __future__ import annotations

import logging
import os

logger = logging.getLogger(__name__)

FALLBACK_EMBED_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
FALLBACK_K = 5
# Calibrated with scripts/eval_intent.py, not guessed. On the 58-row held-out set the
# speech-to-mechanics count is zero at every threshold from 0.00 to 0.40, so the sweep
# cannot justify a high value, while each increment costs real mechanics recall
# (94.4% at 0.04, 88.9% at 0.10, 83.3% at 0.18). Adversarial probes showed why: speech
# the classifier misreads reaches margins as high as 1.000, so no threshold catches it -
# slot resolution is what actually stops it. 0.02 is the highest margin that downgrades
# no correct attack or cast, and it still rejects a true tie, where the margin is 0.
FALLBACK_MECHANICS_MARGIN = 0.02
FALLBACK_BACKEND = "embed"

IMPLEMENTED_BACKENDS = frozenset({"embed", "llm"})
PLANNED_BACKENDS = frozenset({"hosted"})

_dotenv_loaded = False


def _ensure_dotenv() -> None:
    """Load .env into os.environ once. Existing environment values win."""
    global _dotenv_loaded
    if _dotenv_loaded:
        return
    _dotenv_loaded = True
    try:
        from dotenv import load_dotenv

        load_dotenv(override=False)
    except Exception:
        logger.debug("python-dotenv unavailable; relying on os.environ only")


def _raw(name: str) -> str | None:
    _ensure_dotenv()
    value = os.environ.get(name)
    if value is not None and value.strip():
        return value.strip()
    try:
        from .config import settings

        attr = getattr(settings, name, None)
    except Exception:
        attr = None
    if attr is None or str(attr).strip() == "":
        return None
    return str(attr).strip()


def embed_model_name() -> str:
    return _raw("INTENT_EMBED_MODEL") or FALLBACK_EMBED_MODEL


def embed_k() -> int:
    value = _raw("INTENT_EMBED_K")
    if value is None:
        return FALLBACK_K
    try:
        return max(1, int(value))
    except ValueError:
        logger.warning("INTENT_EMBED_K=%r is not an integer; using %d", value, FALLBACK_K)
        return FALLBACK_K


def mechanics_margin() -> float:
    """Confidence margin an attack/cast must clear. Out-of-range values fall back.

    This is the one setting whose miscalibration corrupts game state, so it never
    accepts a value silently: a negative or above-1 margin is a typo, and 0
    disables the gate entirely, which is legal but loud.
    """
    value = _raw("INTENT_MECHANICS_MARGIN")
    if value is None:
        return FALLBACK_MECHANICS_MARGIN
    try:
        margin = float(value)
    except ValueError:
        logger.warning(
            "INTENT_MECHANICS_MARGIN=%r is not a number; using %.2f",
            value,
            FALLBACK_MECHANICS_MARGIN,
        )
        return FALLBACK_MECHANICS_MARGIN

    if not 0.0 <= margin <= 1.0:
        logger.warning(
            "INTENT_MECHANICS_MARGIN=%r is outside [0, 1]; using %.2f",
            value,
            FALLBACK_MECHANICS_MARGIN,
        )
        return FALLBACK_MECHANICS_MARGIN
    if margin == 0.0:
        logger.warning(
            "INTENT_MECHANICS_MARGIN=0: the mechanics confidence gate is disabled, "
            "so any attack/cast classification can change game state"
        )
    return margin


def intent_backend() -> str:
    """Selected Layer 1 backend. Raises for a named-but-unbuilt backend."""
    value = (_raw("INTENT_BACKEND") or FALLBACK_BACKEND).lower()
    if value in IMPLEMENTED_BACKENDS:
        return value
    if value in PLANNED_BACKENDS:
        raise NotImplementedError(
            f"INTENT_BACKEND={value!r} is designed but not built; "
            f"use one of {sorted(IMPLEMENTED_BACKENDS)}"
        )
    logger.warning(
        "INTENT_BACKEND=%r is not recognized; using %r",
        value,
        FALLBACK_BACKEND,
    )
    return FALLBACK_BACKEND
