"""Intent settings. Reads os.environ first because src/config.py is gitignored and
declares fields explicitly, so undeclared keys never reach pydantic Settings."""

from __future__ import annotations

import logging
import os

logger = logging.getLogger(__name__)

FALLBACK_EMBED_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
FALLBACK_K = 5
FALLBACK_MECHANICS_MARGIN = 0.10
FALLBACK_BACKEND = "embed"

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
    value = _raw("INTENT_MECHANICS_MARGIN")
    if value is None:
        return FALLBACK_MECHANICS_MARGIN
    try:
        return float(value)
    except ValueError:
        logger.warning(
            "INTENT_MECHANICS_MARGIN=%r is not a number; using %.2f",
            value,
            FALLBACK_MECHANICS_MARGIN,
        )
        return FALLBACK_MECHANICS_MARGIN


def intent_backend() -> str:
    return (_raw("INTENT_BACKEND") or FALLBACK_BACKEND).lower()
