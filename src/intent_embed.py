# src/intent_embed.py
"""MiniLM embeddings via plain transformers. Deliberately avoids sentence-transformers."""

from __future__ import annotations

import hashlib
import logging
import os
from pathlib import Path
from typing import List, Optional, Sequence

import numpy as np

from .intent_data import Example

logger = logging.getLogger(__name__)

FALLBACK_MODEL = "sentence-transformers/all-MiniLM-L6-v2"


def _configured_model() -> str:
    try:
        from .config import settings

        return str(getattr(settings, "INTENT_EMBED_MODEL", "") or FALLBACK_MODEL)
    except Exception:
        return os.environ.get("INTENT_EMBED_MODEL", FALLBACK_MODEL)


class Embedder:
    """Mean-pooled MiniLM. Loads lazily and stays resident for the process."""

    def __init__(self, model_name: Optional[str] = None) -> None:
        model_name = model_name or _configured_model()
        self.model_name = model_name
        self._tokenizer = None
        self._model = None

    def load(self) -> None:
        if self._model is not None:
            return
        from transformers import AutoModel, AutoTokenizer

        logger.info("Loading intent embedding model %s ...", self.model_name)
        self._tokenizer = AutoTokenizer.from_pretrained(self.model_name)
        self._model = AutoModel.from_pretrained(self.model_name)
        self._model.eval()
        logger.info("Intent embedder ready (CPU) model=%s", self.model_name)

    def encode(self, texts: Sequence[str]) -> np.ndarray:
        """Return an L2-normalized float32 array of shape (len(texts), dim)."""
        import torch

        self.load()
        batch = self._tokenizer(
            list(texts),
            padding=True,
            truncation=True,
            max_length=64,
            return_tensors="pt",
        )
        with torch.no_grad():
            hidden = self._model(**batch).last_hidden_state
        mask = batch["attention_mask"].unsqueeze(-1).float()
        pooled = (hidden * mask).sum(1) / mask.sum(1).clamp(min=1e-9)
        pooled = torch.nn.functional.normalize(pooled, p=2, dim=1)
        return pooled.cpu().numpy().astype(np.float32)


embedder = Embedder()


def examples_fingerprint(examples: Sequence[Example]) -> str:
    """Stable hash of the example set, used as the cache key."""
    h = hashlib.sha256()
    for ex in examples:
        h.update(ex.text.encode("utf-8"))
        h.update(b"\x00")
        h.update(ex.action.encode("utf-8"))
        h.update(b"\x01")
    return h.hexdigest()


def build_matrix(
    examples: Sequence[Example],
    emb: Embedder,
    cache_path: Path,
) -> np.ndarray:
    """Embed every example, reusing a disk cache keyed by the example fingerprint."""
    cache_path = Path(cache_path)
    fingerprint = examples_fingerprint(examples)

    if cache_path.exists():
        try:
            cached = np.load(cache_path, allow_pickle=False)
            if str(cached["fingerprint"]) == fingerprint:
                return cached["matrix"].astype(np.float32)
            logger.info("Intent embedding cache stale; rebuilding.")
        except Exception:
            logger.warning("Intent embedding cache unreadable; rebuilding.")

    matrix = emb.encode([ex.text for ex in examples])
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        np.savez(cache_path, matrix=matrix, fingerprint=np.array(fingerprint))
    except Exception:
        logger.warning("Could not write intent embedding cache to %s", cache_path)
    return matrix
