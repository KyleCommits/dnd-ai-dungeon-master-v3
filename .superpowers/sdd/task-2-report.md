# Task 2 Report: Embedding backend with disk cache

## What was implemented

Created `src/intent_embed.py` with:

- **`Embedder`** — lazy-loading MiniLM via `transformers.AutoModel` + mean pooling (no `sentence_transformers`). Returns L2-normalized float32 vectors of shape `(n, 384)`.
- **`embedder`** — module-level singleton for Task 3.
- **`examples_fingerprint(examples)`** — SHA-256 hash over example text/action pairs for cache invalidation.
- **`build_matrix(examples, emb, cache_path)`** — embeds all example texts, reads/writes an `.npz` cache keyed by fingerprint, handles stale and corrupt caches gracefully.

Also:

- Added `tests/test_intent_embed.py` with `FakeEmbedder` for fast unit tests plus two `@pytest.mark.slow` integration tests.
- Appended `pytest_configure` slow marker registration to `tests/conftest.py`.
- Appended `data/intent/embeddings.npz` to `.gitignore`.

## Test results

### Fast selection (`-m "not slow"`)

```
.....                                                                    [100%]
5 passed, 2 deselected in 0.21s
```

### Slow selection (`-m "slow"`)

```
..                                                                       [100%]
2 passed, 5 deselected, 1 warning in 5.15s
```

The slow run emitted the expected harmless `torchvision` image-extension warning on Windows. Model downloaded and loaded successfully on first run (~5s total after cache warm).

## TDD Evidence

### RED

Command:
```powershell
.\llama_env_311\Scripts\python.exe -m pytest tests/test_intent_embed.py -q -m "not slow"
```

Output:
```
E   ModuleNotFoundError: No module named 'src.intent_embed'
!!!!!!!!!!!!!!!!!!! Interrupted: 1 error during collection !!!!!!!!!!!!!!!!!!!!
1 error in 0.16s
```

Expected failure: test file imports `src.intent_embed` before the module existed.

### GREEN (fast)

Command:
```powershell
.\llama_env_311\Scripts\python.exe -m pytest tests/test_intent_embed.py -q -m "not slow"
```

Output:
```
5 passed, 2 deselected in 0.21s
```

### GREEN (slow)

Command:
```powershell
.\llama_env_311\Scripts\python.exe -m pytest tests/test_intent_embed.py -q -m "slow"
```

Output:
```
2 passed, 5 deselected, 1 warning in 5.15s
```

## Files changed

| File | Change |
|------|--------|
| `src/intent_embed.py` | Created |
| `tests/test_intent_embed.py` | Created |
| `tests/conftest.py` | Appended `pytest_configure` slow marker |
| `.gitignore` | Appended `data/intent/embeddings.npz` |

## Self-review

- **Completeness vs brief:** Implementation transcribed verbatim from the brief. All interfaces match: `Embedder.encode`, `embedder`, `build_matrix`, `examples_fingerprint`.
- **Naming:** Matches brief and Task 1 conventions (`Example` from `intent_data`).
- **YAGNI:** No extra abstractions; cache logic is inline in `build_matrix` as specified.
- **Test quality:** Fast tests verify fingerprint stability, cache hit/miss/invalidation, and corrupt-cache recovery via `FakeEmbedder` without loading a model. Slow tests verify real L2 normalization and speech-vs-attack separation — behavioral checks, not implementation restatement.
- **Constraints:** No `sentence_transformers` import; no new dependencies; `player_intent.py` untouched.

## Concerns

- None blocking. The `torchvision` warning during slow tests is pre-existing environment noise and does not affect embedding behavior.
- `_configured_model()` tries `src.config.settings.INTENT_EMBED_MODEL` first; that setting does not exist yet, so it falls back to `FALLBACK_MODEL` as designed.

## Fix pass 1

### Findings addressed

1. **Cache key omitted model identity:** `build_matrix` now writes the embedder's
   `model_name` into cache metadata and requires both the examples fingerprint and
   model name to match before accepting a cache hit. This prevents vectors from one
   model's latent space being reused by another model. The existing
   `examples_fingerprint` behavior was left unchanged. Covered by
   `tests/test_intent_embed.py::test_cache_invalidated_when_model_changes` and the
   existing fingerprint/cache tests.
2. **Readable malformed caches were accepted:** cached matrices are now required to
   be two-dimensional, have one row per example, contain only finite values, and
   have approximately unit-norm rows. Invalid matrices are logged and rebuilt.
   Covered by
   `tests/test_intent_embed.py::test_malformed_cache_matrix_is_rebuilt`.
3. **Unused import:** removed the unused `typing.List` import from
   `src/intent_embed.py`; the remaining imports are used.

### TDD RED

Command:
```powershell
.\llama_env_311\Scripts\python.exe -m pytest tests/test_intent_embed.py -q -m "not slow"
```

Output:
```text
....FF.                                                                  [100%]
FAILED tests/test_intent_embed.py::test_cache_invalidated_when_model_changes
FAILED tests/test_intent_embed.py::test_malformed_cache_matrix_is_rebuilt - A...
2 failed, 5 passed, 2 deselected in 0.24s
```

Both new tests failed for the expected reason: the second embedder was never called
after a model-name change, and a wrong-row-count matrix was returned without a
rebuild.

### Final verification

Command:
```powershell
.\llama_env_311\Scripts\python.exe -m pytest tests/test_intent_embed.py -q -m "not slow"
```

Output:
```text
.......                                                                  [100%]
7 passed, 2 deselected in 0.22s
```

Command:
```powershell
.\llama_env_311\Scripts\python.exe -m pytest tests/test_intent_embed.py -q -m "slow"
```

Output:
```text
..                                                                       [100%]
============================== warnings summary ===============================
tests/test_intent_embed.py::test_real_embedder_returns_normalized_vectors
  C:\Users\kylej\Documents\Github\dungeon_master_discord_bot_v3\llama_env_311\Lib\site-packages\torchvision\io\image.py:13: UserWarning: Failed to load image Python extension: '[WinError 127] The specified procedure could not be found'If you don't plan on using image functionality from `torchvision.io`, you can ignore this warning. Otherwise, there might be something wrong with your environment. Did you have `libjpeg` or `libpng` installed before building `torchvision` from source?
    warn(

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
2 passed, 7 deselected, 1 warning in 5.01s
```

The slow run also printed the known Windows/torchvision fatal-exception stack
diagnostics during import; pytest still reached the passing summary above.

## Fix pass 2

### Findings addressed

1. **Environment configuration was inert:** created `src/intent_config.py`
   exactly as specified in Step 3b. It loads `.env` once without overriding
   existing environment values, checks `os.environ` before `settings`, and
   provides only `embed_model_name()`, `embed_k()`, `mechanics_margin()`, and
   `intent_backend()`. `src/intent_embed.py` now uses `embed_model_name()` and
   no longer has the broken local configuration helper. Covered by
   `tests/test_intent_embed.py::test_env_var_overrides_embed_model` and
   `tests/test_intent_embed.py::test_embed_model_falls_back_when_unset`.
2. **Wrong-width normalized caches were accepted:** cache writes now include
   `embedding_dim`, and cache reads require the matrix width to match that
   metadata before reuse. Missing or inconsistent metadata causes a rebuild.
   Covered by
   `tests/test_intent_embed.py::test_cache_with_wrong_embedding_width_is_rebuilt`.
3. **Fingerprint delimiters could collide:** replaced delimiter concatenation
   with eight-byte length-prefixed UTF-8 fields, preserving deterministic
   fingerprints while making field boundaries unambiguous. Covered by
   `tests/test_intent_embed.py::test_fingerprint_distinguishes_embedded_delimiters`
   and the existing fingerprint stability test.

### TDD RED

Command:
```powershell
.\llama_env_311\Scripts\python.exe -m pytest tests/test_intent_embed.py -q -m "not slow"
```

Output:
```text
.FFF.....F.                                                              [100%]
FAILED tests/test_intent_embed.py::test_fingerprint_distinguishes_embedded_delimiters
FAILED tests/test_intent_embed.py::test_env_var_overrides_embed_model
FAILED tests/test_intent_embed.py::test_embed_model_falls_back_when_unset
FAILED tests/test_intent_embed.py::test_cache_with_wrong_embedding_width_is_rebuilt
4 failed, 7 passed, 2 deselected in 0.29s
```

The failures demonstrated the delimiter collision, the missing shared config
module, and acceptance of the wrong-width cache.

### Final verification

Command:
```powershell
.\llama_env_311\Scripts\python.exe -m pytest tests/test_intent_embed.py -q -m "not slow"
```

Output:
```text
...........                                                              [100%]
11 passed, 2 deselected in 0.28s
```

Command:
```powershell
.\llama_env_311\Scripts\python.exe -m pytest tests/test_intent_embed.py -q -m "slow"
```

Output:
```text
..                                                                       [100%]
============================== warnings summary ===============================
tests/test_intent_embed.py::test_real_embedder_returns_normalized_vectors
  C:\Users\kylej\Documents\Github\dungeon_master_discord_bot_v3\llama_env_311\Lib\site-packages\torchvision\io\image.py:13: UserWarning: Failed to load image Python extension: '[WinError 127] The specified procedure could not be found'

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
2 passed, 11 deselected, 1 warning in 4.95s
```

The slow run also emitted the known Windows/torchvision fatal-exception
diagnostics, but pytest completed and printed the passing summary.

## Fix pass 3

### Finding addressed

`Embedder.embedding_dim` now loads the model if needed and reports
`self._model.config.hidden_size`, making the live model configuration the
authoritative output width. `build_matrix` accepts a cache only when both its
stored `embedding_dim` and matrix width agree with that authoritative value;
otherwise it logs and rebuilds. `tests/test_intent_embed.py` now gives
`FakeEmbedder` a matching dimension and covers a readable, normalized,
self-consistent wrong-width cache.

### TDD RED

Command:
```powershell
.\llama_env_311\Scripts\python.exe -m pytest tests/test_intent_embed.py::test_self_consistent_wrong_width_cache_is_rebuilt -q
```

Output:
```text
F                                                                        [100%]
E       AssertionError: cache width must match the live embedder dimension
E       assert 0 == 1
FAILED tests/test_intent_embed.py::test_self_consistent_wrong_width_cache_is_rebuilt
1 failed in 0.25s
```

The cache was incorrectly reused, so the fake embedder's call count remained
zero.

### Final verification

Command:
```powershell
.\llama_env_311\Scripts\python.exe -m pytest tests/test_intent_embed.py -q -m "not slow"
```

Output:
```text
............                                                             [100%]
12 passed, 2 deselected in 0.22s
```

Command:
```powershell
.\llama_env_311\Scripts\python.exe -m pytest tests/test_intent_embed.py -q -m "slow"
```

Output:
```text
Windows fatal exception: code 0xc0000139
...
..                                                                       [100%]
============================== warnings summary ===============================
tests/test_intent_embed.py::test_real_embedder_returns_normalized_vectors
  UserWarning: Failed to load image Python extension: '[WinError 127] The specified procedure could not be found'

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
2 passed, 12 deselected, 1 warning in 5.07s
```

The slow run printed the known Windows/torchvision import diagnostics but
completed with both selected tests passing.
