# Design: Embedding-Based Intent Classification

**Date:** 2026-07-26
**Status:** Approved, pending implementation plan
**Replaces:** Free-form JSON generation by Qwen2.5-1.5B in `src/intent_llm.py`
**Related:** `docs/SESSION_RECAP_2026-07-26.md`, `docs/LATENCY_EVAL_2026-07-26.md`

---

## 1. Problem

Layer 1 of the four-layer spine (intent, validate, resolve, narrate) is unreliable, and it
is the only layer blocking playable D&D. In the 2026-07-26 playtest, `hello!` produced an
attack clarify prompt, and `i say "...destroyed your tables..."` resolved as a Longsword
attack on the tables.

Three root causes, all in the intent layer:

1. **Wrong tool for the job.** A 1.5B model generates free-form JSON to answer what is
   mostly a nine-way classification question. Every turn risks unparseable output, and the
   only repair mechanism is prompt tweaking.
2. **Malformed few-shot prompt.** The examples in `build_intent_prompt` are written
   output-first (`{"action":"speak"} // hello!`). The model never sees an input-to-output
   mapping, so the examples teach the wrong pattern.
3. **Fictional confidence.** `player_intent.py` gates mechanics on a `confidence` float
   that the 1.5B self-reports. This number is uncalibrated, so the `< 0.35` threshold fires
   arbitrarily.

Compounding all three: there is no eval set, so every fix has been unmeasurable, producing
the whack-a-mole the session recap warns about.

## 2. Goals

- Correctly route the failing playtest utterances, verified by a repeatable score.
- Never misroute speech into a mechanics action. This is the catastrophic failure: it
  corrupts persisted game state. Target rate is zero on the eval set.
- Stay free and fully local, permanently. No API dependency in the default path.
- Make future intent changes measurements rather than debates.
- Keep intent latency well under the 1-3s the latency eval budgets for it.

## 3. Non-goals

- Narrator latency work (Phase L1/L2 in the latency eval). Orthogonal.
- Fine-tuning a classifier. Documented as a future upgrade in section 11, not built now.
- Changing the four-layer spine, `PlayerIntent`, or anything downstream of
  `parse_player_intent`.
- Growing verb or keyword lists as the primary brain. Explicitly rejected.

## 4. Architecture

`parse_player_intent()` keeps its exact signature and return type. It has one production
caller (`src/tool_executor.py:374`), and everything downstream consumes the `PlayerIntent`
dataclass. The change is entirely internal to the function and its two new helpers.

The single generative call is replaced by two independent steps:

```
player text
  -> structural pre-pass       (quoted dialogue only)
  -> intent_classifier.classify()   embedding kNN -> action + margin
  -> intent_slots.fill()            closed-set match -> target / weapon / spell
  -> decision policy                mechanics gate -> PlayerIntent
```

Separating classification from slot filling is the core insight. Classification is a
semantic judgment that embeddings handle well. Slot filling is a lookup against closed
sets that already exist in the database, which needs no model at all.

## 5. Components

### 5.1 `src/intent_classifier.py` (new)

Owns action classification.

```python
@dataclass(frozen=True)
class Classification:
    action: str          # one of the 8 semantic actions, never "unclear"
    margin: float        # top1 class score minus top2 class score
    top_score: float     # similarity-weighted score of the winning class
    neighbors: list[tuple[str, str, float]]   # (example_text, action, similarity)

def classify(text: str) -> Classification
```

Implementation notes:

- Embeds with `sentence-transformers/all-MiniLM-L6-v2` loaded through
  `transformers.AutoModel` plus mean pooling and L2 normalization. It does **not** use the
  `sentence-transformers` package: version 2.2.2 is installed but broken in `llama_env_311`
  (it imports `cached_download`, removed in `huggingface_hub` 0.35.0), and upgrading it
  risks the pinned `llama-index` 0.10.20 chain that RAG depends on. Mean pooling over
  `AutoModel` is what `sentence-transformers` does internally for this model.
- Model loads lazily on first call and is held as a module-level singleton, matching the
  existing `intent_llm.py` pattern. Measured load time is 4.3s, once per process.
- k = 5 nearest neighbors by cosine similarity, votes weighted by similarity and summed
  per action class. `margin` is the gap between the winning class total and the runner-up.
- Example embeddings are precomputed and cached to `data/intent/embeddings.npz`, keyed by a
  SHA-256 of the examples file. A changed examples file invalidates the cache automatically.
- Classification classes are the eight semantic actions: `attack`, `cast`, `rest`, `roll`,
  `use_item`, `move`, `speak`, `repeat_last`. `unclear` is deliberately excluded, because it
  is not a semantic category a player expresses. It is an output of the decision policy in
  section 7.

### 5.2 `src/intent_slots.py` (new)

Owns slot filling against closed sets. No model, no verb lists.

```python
@dataclass(frozen=True)
class Slots:
    target: str | None
    weapon_hint: str | None
    method: str | None       # unarmed | weapon | improvised | None
    spell_name: str | None
    resolved: bool           # True when the action's required slot matched world state

def fill(text: str, action: str, *, weapon_names, npc_names, spell_names) -> Slots
```

Each slot is matched against a closed set supplied by the caller:

| Slot | Closed set | Source |
| :--- | :--- | :--- |
| target | known NPCs plus scene objects | `target_resolve.list_known_npc_names()`, world state |
| weapon_hint | character inventory | `weapon_names`, already passed into `parse_player_intent` |
| spell_name | character's known/prepared spells | spell integration |
| method | `unarmed` aliases | existing `_UNARMED_ALIASES` frozenset, retained |

Matching is case-insensitive exact match first, then a token-overlap fuzzy match. `resolved`
is False when an action that requires a slot found no candidate, which is a factual,
explainable reason to ask the player a question.

Two scope corrections found while planning:

- **There is no scene-object registry.** `resolve_attack_target` maps any unmatched noun to
  `kind="object"` (`src/target_resolve.py:66-67`), so only NPC names and pronouns can be
  validated against a real closed set. Attacks on objects require an extracted target noun
  but cannot verify it exists. A scene-object registry is future work, not part of this
  change.
- **Extraction reuses `attack_resolve.parse_attack_utterance`.** That function already pulls
  target and weapon out of an attack line and is already tested. Its verb regexes were an
  anti-pattern when they decided *whether* a line was an attack; running them only after the
  classifier has labeled the line, to determine *which* target, is a different and safe job.
  Rewriting extraction from scratch would duplicate tested code.

### 5.3 `src/player_intent.py` (modified)

`parse_player_intent` becomes an orchestrator. Deleted from this module:

- `_SOCIAL_DIALOGUE_RE` and `is_social_dialogue`. The apology and gold-offer cases move
  into labeled examples. The prototype confirms embeddings already classify the exact
  failing line as `speak`.
- The `confidence < 0.35` mechanics gate, replaced by the margin gate in section 7.
- `normalize_intent_post_llm`'s discourse override branch, which exists only to repair the
  1.5B's invented attacks.

Retained:

- `_QUOTED_DIALOGUE_RE` and `is_speech_act` as a structural pre-pass. Quoted text and
  `i say` framing are punctuation and syntax, not a verb list, and they are reliable enough
  to short-circuit before embedding. This is a deliberate, bounded exception to the
  no-regex rule.
- `intent_from_rules` as a test helper behind `INTENT_RULES_FALLBACK`, unchanged.
- `PlayerIntent`, `parse_intent_json`, and `intent_from_last_attack_memory`, unchanged.

`PlayerIntent.confidence` is retained for API compatibility and populated with the
classifier margin. `PlayerIntent.source` gains the value `embed`. The existing `speech_act`
source value is kept unchanged for the structural pre-pass, because
`tests/test_player_intent.py` already asserts it.

### 5.4 `src/intent_llm.py` (demoted, not deleted)

Kept and reachable via `INTENT_BACKEND=llm` so the eval harness can score it against the
embedding backend on identical data. Its reversed few-shot examples are fixed to
input-then-output form so the comparison is fair rather than a straw man.

## 6. Configuration

| Variable | Default | Meaning |
| :--- | :--- | :--- |
| `INTENT_BACKEND` | `embed` | `embed`, `llm`, or `hosted` |
| `INTENT_EMBED_MODEL` | `sentence-transformers/all-MiniLM-L6-v2` | Embedding model id |
| `INTENT_EMBED_K` | `5` | Neighbor count |
| `INTENT_MECHANICS_MARGIN` | `0.10` provisional | Minimum margin to allow attack or cast. Replaced by the section 10.1 sweep result once the eval set exists. |

Existing `INTENT_*` variables keep their meanings and apply only to the `llm` backend.
`hosted` is a documented placeholder for a future Gemini backend; it raises a clear
`NotImplementedError` until built, so the enum is honest about what exists.

## 7. Decision policy

This implements the asymmetry decision: misrouting speech into mechanics corrupts state,
while misrouting mechanics into speech merely produces narration.

1. If the structural pre-pass detects quoted dialogue or `i say` framing, return `speak`
   immediately with `source="speech_act"`.
2. Classify. If the action is not `attack` or `cast`, accept it.
3. If the action is `attack` or `cast`, it must clear **both** gates:
   - `margin >= INTENT_MECHANICS_MARGIN`
   - `Slots.resolved is True`
4. If either gate fails, downgrade to `speak`. The narrator handles it, and no game state
   changes.
5. `needs_clarify` is set only by slot failure at layer 2, where `resolve_intent` already
   asks a specific question via `resolve_attack_target`. It is never set by a similarity
   score.

Downgrades log the action, margin, and failing gate, so live misses are diagnosable and
can be converted into labeled examples.

## 8. Data

### 8.1 Training examples: `data/intent/examples.jsonl`

```json
{"text": "hello there", "action": "speak"}
{"text": "i attack the table", "action": "attack"}
```

Seeded at roughly 150 lines drawn from the 2026-07-26 playtest log and common D&D phrasing,
weighted toward the `speak` versus `attack` boundary where the failures cluster. Kyle
reviews and corrects labels before the set is considered valid.

### 8.2 Eval set: `tests/data/intent_eval.jsonl`

Identical format, held out. The harness asserts the two files share no `text` values, so a
passing score cannot come from memorization.

## 9. Error handling

| Failure | Behavior |
| :--- | :--- |
| Embedding model fails to load | Log the exception, fall back to `speak` for all input. Play continues as pure narration rather than crashing. |
| Examples file missing or malformed | Raise at startup, not per-turn. A silently empty classifier is worse than a loud failure. Validating the file only reads and parses JSONL, so it happens eagerly at startup even though the model itself loads lazily. |
| Cache file corrupt or stale | Recompute from source and overwrite. Never fatal. |
| Embedding call raises mid-session | Catch, log, return `speak`. |
| Action requires a slot that did not resolve | Downgrade to `speak` per policy step 4, or clarify at layer 2 where a specific question exists. |

The consistent principle: every failure path degrades to narration, which cannot corrupt
game state.

## 10. Testing

### 10.1 Eval harness: `scripts/eval_intent.py`

Runs a backend over the eval set and reports overall accuracy, per-class precision and
recall, a confusion matrix, p50 and p95 latency, and the speech-to-mechanics false positive
count. Takes `--backend` so `embed` and `llm` are scored identically.

It also emits a threshold sweep over candidate `INTENT_MECHANICS_MARGIN` values, showing
mechanics recall against speech-to-mechanics false positives at each. The default is chosen
from that sweep as the highest recall with zero false positives. This matters concretely:
in the prototype, correct answers landed at similarity 0.47 and 0.71, so a guessed 0.5
cutoff would have rejected two correct classifications.

### 10.2 Regression gate: `tests/test_intent_classifier.py`

- Speech-to-mechanics false positives on the eval set equal zero. Hard failure.
- Overall accuracy at or above a floor set from the first measured run.
- Every line from the 2026-07-26 playtest log classifies correctly, as named cases.
- Training and eval sets are disjoint.
- Slot filling rejects pronoun targets and attacks with no target noun. NPC names snap to
  their canonical form; weapons absent from inventory are dropped rather than passed
  through. Arbitrary object nouns are accepted, per the registry limitation in section 5.2.
- Every failure path in section 9 returns `speak` rather than raising.

Unit tests stub the embedding call for speed. The eval harness is the only component that
loads the real model, keeping the suite near its current sub-second runtime.

## 11. Risks and limits

**Coverage is bounded by the examples.** Phrasing far from any labeled line will miss. This
is the real tradeoff against a generative model. It is acceptable because a miss is fixed by
adding a labeled line, which is permanent, measurable, and cannot regress another case
silently the way a new regex can. The downgrade logging in section 7 turns live misses into
example candidates.

**Threshold calibration is load-bearing.** A wrong margin either lets speech through to
mechanics or makes attacks unusable. Section 10.1's sweep, rerun whenever the example set
changes materially, is the control.

**Genuinely ambiguous input exists.** "I go for the table" has no correct mechanical
reading. Policy sends it to `speak` with a low margin, and the DM asks naturally. That is
better play than a stiff engine clarify prompt.

**Upgrade path.** Once the labeled set exceeds roughly 500 lines, fine-tuning a small
encoder classifier on the same data would beat kNN on accuracy at similar latency. The data
format and the `INTENT_BACKEND` switch are designed so this is a new backend scored against
the same eval set, not a rewrite.

## 12. Success criteria

1. `scripts/eval_intent.py --backend embed` reports zero speech-to-mechanics false
   positives on the held-out eval set.
2. Overall accuracy exceeds the `llm` backend on the same set, measured rather than assumed.
3. p95 intent latency under 50ms, against 1-3s today.
4. Every 2026-07-26 playtest line routes correctly in the regression test.
5. Kyle completes a live ASCII session and confirms play feels correct. Per the standing
   rule in the session recap, no claim of a working loop before this.
