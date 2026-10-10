# Latency Evaluation — 2026-07-26

**Status:** Evaluation + **L1 implementation started (2026-07-26)**  
**Hardware:** Alienware M18 R2 — i9-14900HX, 32GB RAM, RTX 4080 mobile 12GB  
**Related:** [`SESSION_RECAP_2026-07-25.md`](SESSION_RECAP_2026-07-25.md), [`chat_gpts_plan.md`](chat_gpts_plan.md)  
**Code cited:** `src/llm_manager.py`, `src/intent_llm.py`, `src/tool_executor.py`, `src/dynamic_dm.py`

### L1 defaults now in code / `.env`

| Knob | Value |
| :--- | :--- |
| Narrator | `mistralai/Mistral-7B-Instruct-v0.3` |
| Quantization | 4-bit nf4 (`LOCAL_LOAD_IN_4BIT=true`, `LOCAL_QUANTIZATION=4bit`) |
| CPU offload | Off for DM path |
| Soft-RP tokens | Cap 180; tool loop defaults 160 / narration 140 |
| Context | History 4×250 chars; summaries last 3; campaign excerpt 1800 chars |
| Logs | Each DM generate logs `prompt_tokens`, `max_new_tokens`, `generate_ms`, `model_name` |

Next implement pass after measuring soft-RP: **Phase L2** (Ollama/llama.cpp).

---

## 1. Problem statement

### UX bar

Waiting **a full few minutes** for a DM reply is a failure, not an acceptable “local LLM tax.”

| Bar | Target (soft RP / narration path) |
| :--- | :--- |
| First useful text | A few seconds (streaming later helps perceived latency) |
| Full soft-RP reply | **Under ~15–20s** wall time on this machine when the 8B (or successor) runs |
| Attack / clarify / hard-refuse | Sub-second to a few seconds — **engine templates**, no narrator required |

Documented expectation in README / prior recap (~30–90s) already exceeds good play feel; multi-minute turns mean the stack is mis-tuned for interactive D&D.

### Why it feels slow today (architecture facts)

| Piece | Reality |
| :--- | :--- |
| DM narrator | Llama 3.1 8B Instruct via Hugging Face Transformers + **8-bit** BitsAndBytes, CUDA, `device_map="auto"` |
| Intent | Qwen 2.5 **1.5B** Instruct on **CPU** (upgraded from 0.5B) — JSON job; still **not** the multi-minute bottleneck |
| Hot path | Intent → validate/resolve → often **skip** GPU narration (attacks, clarify, cast refuse); soft RP / successful cast hit the 8B |
| Generate caps | `max_new_tokens` clamped to **256**; asyncio timeout **90s** |
| Offload risk | `llm_int8_enable_fp32_cpu_offload=True` can push layers to CPU and destroy decode speed |
| KV / stream | **No** cross-turn KV cache; **no** token streaming to ASCII; every call re-encodes the full prompt |
| Context | Campaign excerpt + recent history in `_build_massive_context`; vector RAG is **not** on the web chat hot path |
| Tool loop | Up to **2** DM generate rounds per turn when TOOL_CALL path runs |

Likely drivers of multi-minute replies: large prompt re-prefills every turn, 8-bit Transformers decode on 12GB mobile (with possible CPU offload), and double generates in the tool loop — not the 1.5B intent model.

### Companions multiply the budget

Beast Master companions already exist as **game state** (`animal_companion_manager`, ASCII `/companion`). Down the road some LLM must voice companion actions/dialogue.

Assumption for planning: **more than one narrative speaker per turn** (DM + companion). We cannot spend the entire GPU budget on one fat 8B decode with a huge prompt, then do it again for the wolf. Latency work must leave headroom for a second short narrative beat (or one shared multi-speaker call).

### Architecture keepers (non-negotiable)

Four-layer spine stays:

1. IntentLLM parses player text → structured intent  
2. Engine validates (gear, spells, targets)  
3. Engine resolves (dice, HP, slots)  
4. LLM narrates **results only** — never invents hit/miss/damage/slots  

Reject any advice that re-expands verb regex as the primary brain, or that starts the narrator before intent/resolve finishes.

---

## 2. ChatGPT idea scorecard

Ratings: **adopt** (do soon) / **later** (after L1–L2) / **reject** (wrong for this repo).

| Idea | Rating | Why for *this* repo |
| :--- | :--- | :--- |
| Swap narrator (Mistral 7B / Phi-3 Mini / Gemma 2 9B) | **adopt** (L1) | Llama 3.1 8B Instruct is quality-heavy; env-selectable faster 7B/Mini is the highest-ROI Transformers change. Prefer Mistral 7B for quality/speed balance; Phi-3 Mini for “fast mode.” |
| Quantization GGUF Q4_K_M / Q5_K_M via llama.cpp or Ollama | **adopt** (L2) | Real win for VRAM + decode; not a config flip — needs a thin adapter behind `LLMManager.generate()`. |
| Pipeline: start narrator prefill before intent resolves | **reject** | Breaks Intent → Resolve → Narrate. Attacks often skip the 8B; prefill wastes GPU and races mechanics. |
| Replace Intent with Phi-3 Mini on GPU | **reject** | Still oversized for JSON; keep Qwen 1.5B on CPU (0.5B was too weak at social vs attack). |
| Replace Intent with regex + few-shot hybrid as primary | **reject** | Explicit anti-pattern (mole-whacking). Rules fallback stays demoted (`INTENT_RULES_FALLBACK=false`). |
| KV cache reuse across turns | **adopt** (L2) | Conversation-shaped workload; Transformers pipeline today does full re-encode. Ollama/llama.cpp/vLLM unlock this. |
| Speculative decoding (draft Phi-3 → target Mistral) | **later** | Huge upside but needs vLLM/TensorRT-class stack; defer until L2 measured and still insufficient. |
| Smarter context (last 2–3 turns, scene, summarize rest) | **adopt** (L1) | Smaller prompt = faster prefill. Already partially capped; tighten further and **log token counts**. |
| ExLlamaV2 / Flash Attention / FP16 on 4080 | **later** | Strong on this GPU; another rewrite of the loader. Prefer Ollama/llama.cpp first for ops simplicity on Windows. |
| Aggressive mode: Phi-3 Mini narrator + rules-only intent | **later** (fast mode only) | Acceptable as an optional “turbo” profile after L1 env switch; not the default quality path; do not drop IntentLLM. |
| Parallel RAG with intent | **reject** (for hot path) | Web DM does not call RAG in the hot path today; optimizing it does not fix multi-minute chat. |
| Unused vLLM env knobs as “already supported” | **reject** | `VLLM_*` in `.env.example` has **no** Python consumers — dead config. |

**Bottom line on ChatGPT’s list:** model choice + context size + inference runtime are the real levers. Pipeline parallelism-before-intent and “bigger intent model” are noise for this architecture.

---

## 3. Companion-aware latency model

### Recommendation: one shared narrator, role-tagged output

| Approach | Latency | Complexity | Verdict |
| :--- | :--- | :--- | :--- |
| One GPU call: DM paragraph + optional `Companion:` line | Best | Low | **Default** |
| Second short generate for companion only | 2× GPU if naive | Medium | Only if shared-call quality fails |
| Separate always-on companion model on GPU | VRAM fight on 12GB | High | Avoid while DM is also local GPU |

**Per-turn budget (target shape):**

```
IntentLLM (CPU, ~1–3s)     → structured intent
Engine resolve (ms–low s)  → mechanics / templates
Narrator (GPU, short)      → one reply covering scene + optional companion beat
```

Rules:

- Companion **mechanics** (HP, attack rolls) stay in GameActions / combat engine — same as the PC.  
- Companion **voice** is flavor after resolve, not a second full campaign-context essay.  
- Prefer templates for pure combat companion swings; LLM for social / exploratory beats.  
- Never N full 8B passes with the full campaign excerpt each.

---

## 4. Phased recommendation (implementation backlog)

Do **not** implement in this eval pass. Default order: **L1 then L2**, then L3 for feel. Companions stay affordable on one 12GB GPU.

### Phase L1 — Transformers quick wins

Stay on Hugging Face; change knobs and load path in `llm_manager.py` / context builders.

1. **4-bit load path** (`BitsAndBytesConfig(load_in_4bit=True, ...)`) — cut VRAM/pressure vs 8-bit; revisit CPU offload (prefer full GPU residency).  
2. **Env-selectable narrator** — e.g. `LOCAL_MODEL_NAME` → Mistral 7B Instruct (primary) or Phi-3 Mini (fast profile); document download/auth.  
3. **Tighten prompts** — smaller campaign excerpt, fewer history turns/chars, shorter tool lists when not needed; keep attack paths template-only.  
4. **Lower default `max_new_tokens`** for soft RP (e.g. 120–180) unless TOOL_CALL needs more.  
5. **Instrument** — log `prompt_tokens`, `max_new_tokens`, `generate_ms` every DM call so we stop guessing.

### Phase L2 — Runtime adapter (KV + speed)

Keep `async def generate(...) -> str` as the app contract.

1. Adapter behind `LLMManager` to **Ollama or llama.cpp** serving GGUF **Q4_K_M** (or Q5_K_M) of the chosen narrator.  
2. Keep IntentLLM on Transformers CPU as today.  
3. Enable **session/prefix KV reuse** where the server supports it for follow-up turns.  
4. Retire reliance on BitsAndBytes for the DM path once the adapter is stable.

### Phase L3 — Feel + companions

1. **WebSocket token streaming** into `web/ascii_client` so the player sees text immediately.  
2. Companion lines: same-call multi-speaker format first; short second beat only if needed.  
3. Optional “turbo” profile (Phi-3 Mini narrator) for playtests.

### Defer until L2 is still too slow

- Speculative decoding / TensorRT-LLM  
- ExLlamaV2 (revisit if Ollama/llama.cpp plateau on this GPU)  
- Campaign Phase 5 unification (orthogonal)

---

## 5. Success metrics (for a later implement pass)

Measure on `/playtest` + soft-RP line (e.g. “I look around the tavern”) with models already warm.

| Metric | Pass criteria |
| :--- | :--- |
| Soft-RP wall time p50 | ≤ 15s |
| Soft-RP wall time p95 | ≤ 25s (stretch: ≤ 20s) |
| Attack template path | No DM generate; remains fast (intent + engine only) |
| Cast hard-refuse | Engine path; no long narration |
| VRAM | Fits 12GB with intent on CPU; no forced CPU offload of DM layers |
| Instrument logs | Every DM generate logs tokens + ms |
| Companion-ready | Design allows DM + companion in **one** short generate without doubling p50 |

Optional timing recipe (later):

```powershell
# Warm server, /playtest, /session start, then one look-around line.
# Watch backend logs for generate_ms / prompt_tokens once L1 instrumentation lands.
```

---

## 6. Explicit non-goals

- Phase 5 campaign manager / generator unification  
- Growing verb/keyword lists as the primary intent brain  
- Starting narrator generation before intent + resolve complete  
- Replacing Qwen 0.5B intent with a larger “smarter” model by default  
- Benchmarks and model downloads in *this* eval-only pass  
- Multiplayer session architecture  

---

## 7. Recommended next decision

After reviewing this doc, pick an **implementation** plan:

1. **Start L1** (recommended first) — 4-bit + model env switch + prompt/token logging.  
2. **Jump to L2** if you would rather invest in Ollama/llama.cpp immediately and skip polishing BitsAndBytes.

Default recommendation: **L1 then L2**, so companions remain one short GPU narration on a 12GB card.
