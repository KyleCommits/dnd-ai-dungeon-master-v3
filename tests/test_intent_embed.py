# tests/test_intent_embed.py
import numpy as np
import pytest

from src.intent_data import Example
from src.intent_embed import Embedder, build_matrix, examples_fingerprint


class FakeEmbedder:
    """Deterministic stand-in so unit tests never load a real model."""

    def __init__(self):
        self.calls = 0

    def encode(self, texts):
        self.calls += 1
        vecs = []
        for t in texts:
            v = np.zeros(4, dtype=np.float32)
            v[len(t) % 4] = 1.0
            vecs.append(v)
        return np.vstack(vecs)


EXAMPLES = [Example("hello", "speak"), Example("i attack the table", "attack")]


def test_fingerprint_changes_when_examples_change():
    a = examples_fingerprint(EXAMPLES)
    b = examples_fingerprint(EXAMPLES + [Example("hi", "speak")])
    assert a != b
    assert a == examples_fingerprint(EXAMPLES)


def test_build_matrix_shape_and_cache_write(tmp_path):
    cache = tmp_path / "emb.npz"
    fake = FakeEmbedder()
    m = build_matrix(EXAMPLES, fake, cache)
    assert m.shape == (2, 4)
    assert cache.exists()
    assert fake.calls == 1


def test_build_matrix_reuses_cache(tmp_path):
    cache = tmp_path / "emb.npz"
    fake = FakeEmbedder()
    build_matrix(EXAMPLES, fake, cache)
    m2 = build_matrix(EXAMPLES, fake, cache)
    assert fake.calls == 1, "second call should hit the cache"
    assert m2.shape == (2, 4)


def test_cache_invalidated_when_examples_change(tmp_path):
    cache = tmp_path / "emb.npz"
    fake = FakeEmbedder()
    build_matrix(EXAMPLES, fake, cache)
    build_matrix(EXAMPLES + [Example("hi", "speak")], fake, cache)
    assert fake.calls == 2, "changed examples must invalidate the cache"


def test_corrupt_cache_is_rebuilt(tmp_path):
    cache = tmp_path / "emb.npz"
    cache.write_bytes(b"not an npz file")
    fake = FakeEmbedder()
    m = build_matrix(EXAMPLES, fake, cache)
    assert m.shape == (2, 4)


@pytest.mark.slow
def test_real_embedder_returns_normalized_vectors():
    e = Embedder()
    m = e.encode(["hello there", "i attack the table"])
    assert m.shape == (2, 384)
    norms = np.linalg.norm(m, axis=1)
    assert np.allclose(norms, 1.0, atol=1e-4)


@pytest.mark.slow
def test_real_embedder_separates_speech_from_attack():
    e = Embedder()
    m = e.encode(["hello there", "hi barkeep", "i attack the table"])
    speech_sim = float(m[0] @ m[1])
    cross_sim = float(m[0] @ m[2])
    assert speech_sim > cross_sim
