# src/intent_embed.py
"""MiniLM embeddings via plain transformers. Deliberately avoids sentence-transformers."""

from __future__ import annotations

import hashlib
import logging
from pathlib import Path
from typing import Optional, Sequence

import numpy as np

from .intent_config import embed_model_name
from .intent_data import Example

logger = logging.getLogger(__name__)

class Embedder:
    """Mean-pooled MiniLM. Loads lazily and stays resident for the process."""

    def __init__(self, model_name: Optional[str] = None) -> None:
        model_name = model_name or embed_model_name()
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
        for value in (ex.text, ex.action):
            encoded = value.encode("utf-8")
            h.update(len(encoded).to_bytes(8, byteorder="big"))
            h.update(encoded)
    return h.hexdigest()


def _valid_cached_matrix(
    matrix: np.ndarray, expected_rows: int, expected_dim: int
) -> bool:
    if (
        matrix.ndim != 2
        or matrix.shape[0] != expected_rows
        or matrix.shape[1] != expected_dim
    ):
        return False
    if not np.all(np.isfinite(matrix)):
        return False
    return bool(np.allclose(np.linalg.norm(matrix, axis=1), 1.0, atol=1e-4))


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
            with np.load(cache_path, allow_pickle=False) as cached:
                if (
                    str(cached["fingerprint"]) == fingerprint
                    and str(cached["model_name"]) == emb.model_name
                ):
                    matrix = cached["matrix"].astype(np.float32)
                    embedding_dim = int(cached["embedding_dim"])
                    if _valid_cached_matrix(matrix, len(examples), embedding_dim):
                        return matrix
                    logger.warning("Intent embedding cache matrix invalid; rebuilding.")
                else:
                    logger.info("Intent embedding cache stale; rebuilding.")
        except Exception:
            logger.warning("Intent embedding cache unreadable; rebuilding.")

    matrix = emb.encode([ex.text for ex in examples])
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        np.savez(
            cache_path,
            matrix=matrix,
            fingerprint=np.array(fingerprint),
            model_name=np.array(emb.model_name),
            embedding_dim=np.array(matrix.shape[1]),
        )
    except Exception:
        logger.warning("Could not write intent embedding cache to %s", cache_path)
    return matrix
