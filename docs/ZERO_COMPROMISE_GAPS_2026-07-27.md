# Zero-Compromise Gaps — 2026-07-27

**Audience:** Kyle and agents deciding what to build next.  
**North star:** Solo long-running D&D 5e with an AI DM and **zero compromises**.  
**Related:** [`chat_gpts_plan.md`](chat_gpts_plan.md), [`phase2_combat_rest_plan.md`](phase2_combat_rest_plan.md), [`SESSION_RECAP_2026-07-27.md`](SESSION_RECAP_2026-07-27.md), [`INTENT_CLASSIFIER_HANDOFF_2026-07-26.md`](INTENT_CLASSIFIER_HANDOFF_2026-07-26.md), [`superpowers/specs/2026-07-26-intent-classifier-design.md`](superpowers/specs/2026-07-26-intent-classifier-design.md)

`docs/` is gitignored; this file is local unless force-added.

---

## 1. Goal and definition of done

From [`chat_gpts_plan.md`](chat_gpts_plan.md): a persistent, stateful, AI-driven game engine — not a chatbot. The player creates a character, enters a campaign, acts in natural language, fights, progresses, leaves, and returns to the same world.

**Zero compromise** for this project means:

1. Play happens in the ASCII terminal via natural language (slash commands are shortcuts, not the only path).
2. Every mechanics-bearing utterance is classified, validated, and **resolved by the engine** — not hoped from narrator prose.
3. The AI narrates outcomes from tool/engine results. It does not invent hit, damage, slots, HP, XP, or conditions.
4. Rules-relevant state persists across sessions (character, world memory, and — when in a fight — the encounter itself).
5. Deferred 5e pieces (action economy, death saves, concentration, opportunity attacks, spell effects on targets) are treated as **open gaps**, not as "MVP done."

If the DM can soft-narrate around a missing rule and the save file never changes, that is a compromise.

---

## 2. What already clears a narrow bar

These pieces are real and file-backed. They are necessary; they are not sufficient for zero-compromise solo play.

| Area | What works | Evidence |
| :--- | :--- | :--- |
| Intent (Layer 1) | Embedding kNN + closed-set slots; attack/cast require margin **and** resolved slots; else `speak` | [`src/player_intent.py`](../src/player_intent.py), [`src/intent_classifier.py`](../src/intent_classifier.py), [`src/intent_slots.py`](../src/intent_slots.py), [`scripts/eval_intent.py`](../scripts/eval_intent.py) |
| Chat attacks | Object / named-NPC / in-combat attacks resolve before the DM LLM | [`src/intent_resolver.py`](../src/intent_resolver.py), [`src/attack_resolve.py`](../src/attack_resolve.py), [`src/game_actions.py`](../src/game_actions.py) `resolve_player_attack` |
| Combat engine MVP | Encounter create/add/begin/attack/next/end; d20+bonus vs AC; PC HP sync to DB | [`src/combat_system.py`](../src/combat_system.py), GameActions combat wrappers in [`src/game_actions.py`](../src/game_actions.py) |
| Spells (partial) | 319-spell DB; chat cast can validate and **consume a slot** | [`src/enhanced_spell_system.py`](../src/enhanced_spell_system.py), [`src/spell_integration.py`](../src/spell_integration.py), [`src/tool_executor.py`](../src/tool_executor.py) `_backend_cast_tools` |
| Equipment (partial) | Equip/unequip AC; inventory weapon chooser on attack | [`src/equipment_system.py`](../src/equipment_system.py), [`src/weapon_choose.py`](../src/weapon_choose.py) |
| Memory plumbing | Session summaries on end/start; world state table (location, NPC trust, plot threads); GameActions to update them | [`src/campaign_state_manager.py`](../src/campaign_state_manager.py), [`src/world_state_store.py`](../src/world_state_store.py), [`src/dynamic_dm.py`](../src/dynamic_dm.py) |
| Rest (slash) | `/rest short\|long` hits engine rest | [`src/ascii_ui/commands.py`](../src/ascii_ui/commands.py), [`src/spell_integration.py`](../src/spell_integration.py) `character_rest` |

**Not cleared:** live intent sign-off after the `i attack the table again` fix; full chat combat loop; spell *effects*; engine-owned rest/roll/use_item/move; XP from play; persisted encounters.

---

## 3. Gap catalog (ordered by how hard it breaks solo play)

For each gap: symptom, current code, compromise today, done when.

### P0 — Intent live trust + unfinished engine ownership

#### P0.1 Live intent sign-off and data loop

| | |
| :--- | :--- |
| **Symptom** | Offline eval can read 100% while live lines still misroute (`i attack the table again` → Mira narration, 2026-07-27). |
| **Current code** | Classifier + gates on master (`caad5e6`). Eval: [`tests/data/intent_eval.jsonl`](../tests/data/intent_eval.jsonl). Training: [`data/intent/examples.jsonl`](../data/intent/examples.jsonl). |
| **Compromise today** | Treating unit/eval green as "playable." Eval has no named-NPC attack row (hid one regression). `spell_names` is not passed from production, so cast "slot resolution" often means "name extractable," not "in spellbook." |
| **Done when** | Kyle signs off the smoke script after a clean server restart (embedding cache rebuild). Misses become labeled examples; [`scripts/eval_intent.py`](../scripts/eval_intent.py) + slow gates stay green. Production plumbs known/prepared spells into `parse_player_intent(..., spell_names=...)`. |

#### P0.2 Classified intents that never hit the engine

| | |
| :--- | :--- |
| **Symptom** | Player says "I take a long rest" / "I drink a potion" / "I roll Insight" / "I walk upstairs." Classifier may label correctly; game state often does not change unless the LLM emits the right tool. |
| **Current code** | [`src/intent_data.py`](../src/intent_data.py) `VALID_ACTIONS` includes `rest`, `roll`, `use_item`, `move`. [`src/intent_resolver.py`](../src/intent_resolver.py) engine-handles **attack** and **cast** only; everything else falls through to DM/tools. Legacy clarify for dash/hide/etc. still lives in [`src/mechanics_claims.py`](../src/mechanics_claims.py) + [`src/tool_executor.py`](../src/tool_executor.py). |
| **Compromise today** | Soft RP and tool luck stand in for rules. |
| **Done when** | `resolve_intent` (or equivalent) executes rest, skill/ability/save rolls, use_item, and movement/location updates the same way attack/cast do — before narration. |

---

### P1 — Rules that look present but do not resolve from chat

#### P1.1 Spell effects (chat cast is slot theater)

| | |
| :--- | :--- |
| **Symptom** | "I cast fireball" can consume a slot and get flavor text. Targets do not take damage; saves are not rolled; concentration is not started. |
| **Current code** | Chat path: lookup + `consume_spell_slot` ([`src/tool_executor.py`](../src/tool_executor.py), [`src/intent_resolver.py`](../src/intent_resolver.py) `_resolve_cast`). Effect dice helpers exist in [`src/spell_integration.py`](../src/spell_integration.py) `_calculate_spell_effects` but are not applied on the chat spine. `concentration_spell` on combatants is cleared, not set on cast. |
| **Compromise today** | Narrator invents or omits spell outcomes. |
| **Done when** | Cast resolves: legality → slot/cantrip → attack roll or save → damage/heal/condition → concentration flag → mechanics summary → narration from results only. |

#### P1.2 Combat as 5e from natural language

| | |
| :--- | :--- |
| **Symptom** | A fight can be orchestrated via REST/GameActions. From chat alone: no reliable enemy turns, no action economy, no OA, no death saves in the encounter, no concentration checks; restart wipes the fight. |
| **Current code** | MVP in [`src/combat_system.py`](../src/combat_system.py). Explicitly deferred in [`phase2_combat_rest_plan.md`](phase2_combat_rest_plan.md): action economy, death saves in combat, concentration auto-checks, grid, UI, **DB-persisted encounters**, real enemy AI. Death-save helpers exist on characters but are not combat GameActions. Enemy turns require the AI to call tools; no automated monster-turn helper. |
| **Compromise today** | Lab combat / DM improvisation instead of enforced initiative combat. |
| **Done when** | Chat can start and finish a fight where: initiative runs; PC and monster turns enforce action economy; attacks/OA/death saves/concentration use the engine; monster turns run without hoping the LLM remembers; encounter state survives process restart (or is explicitly checkpointed). |

---

### P2 — World proof, progression, items

#### P2.1 Scene / target validation

| | |
| :--- | :--- |
| **Symptom** | Any unmatched noun becomes an attackable `object`. Furniture HP is in-memory and dies on restart. |
| **Current code** | [`src/target_resolve.py`](../src/target_resolve.py) defaults unknown → `kind="object"`. [`src/scene_objects.py`](../src/scene_objects.py) profiles (table, door, …); docstring: lost on restart. NPCs resolve from `npc_relationships` world state. |
| **Compromise today** | Phantom objects; no real scene graph. |
| **Done when** | Attacks require a closed-set hit (NPC, registered scene object, or in-combat combatant). Scene objects persist with the campaign/session. |

#### P2.2 XP and leveling outside the play loop

| | |
| :--- | :--- |
| **Symptom** | Player never gets XP from defeating a goblin or finishing a beat unless an admin hits REST. |
| **Current code** | Math + API: [`src/level_progression.py`](../src/level_progression.py), [`src/enhanced_character_api.py`](../src/enhanced_character_api.py) award-xp / level-up. No GameAction / DynamicDM tool for XP. Combat end does not grant XP. |
| **Compromise today** | Progression is manual/out-of-band. |
| **Done when** | Engine awards XP on defined triggers; level-up is offered and applied through the same spine as other mechanics. |

#### P2.3 Equipment beyond weapon + AC

| | |
| :--- | :--- |
| **Symptom** | "I drink a healing potion" / "I use the crowbar" classify as `use_item` but do not run an item-effect pipeline. |
| **Current code** | Intent label exists; no `resolve_intent` branch. Equip path updates AC ([`src/game_actions.py`](../src/game_actions.py) `equip_item`). Consumables/treasure economy not a closed loop. |
| **Compromise today** | Slash/Gemini or pure narration for items. |
| **Done when** | `use_item` resolves against inventory, applies effects (heal, tool use, consumable spend), updates inventory. |

---

### P3 — Continuity quality and codebase hygiene

#### P3.1 Memory quality (plumbing without grounding)

| | |
| :--- | :--- |
| **Symptom** | "Last time on…" recaps are generic; location sticks on `"Starting Location"`; long arcs collapse to last few summaries/messages. |
| **Current code** | Summaries on session end/start ([`src/ascii_ui/commands.py`](../src/ascii_ui/commands.py), [`src/dynamic_dm.py`](../src/dynamic_dm.py)). World tools exist but are soft-enforced. Adaptive hooks / major_decisions largely unused. |
| **Compromise today** | Continuity theater. |
| **Done when** | Recaps are structured (location, NPCs, open threads, last combat); location/NPC trust update whenever the fiction moves; context budget preserves arc-critical facts. |

#### P3.2 Campaign manager duplication

| | |
| :--- | :--- |
| **Symptom** | Three layers (persist/RAG, play state, generation) confuse agents and risk double writes. |
| **Current code** | [`src/campaign_manager.py`](../src/campaign_manager.py), [`src/campaign_state_manager.py`](../src/campaign_state_manager.py), [`src/campaign_generation/`](../src/campaign_generation/). Backlog in [`chat_gpts_plan.md`](chat_gpts_plan.md). |
| **Compromise today** | Developer confusion more than immediate play break. |
| **Done when** | One documented ownership map (or merge); generators seed play state on load. |

---

## 4. Plan claim inflation

| Claim in plans | Reality |
| :--- | :--- |
| Phase 2 combat "DONE for MVP" ([`chat_gpts_plan.md`](chat_gpts_plan.md)) | Engine + REST/GameActions exist. Not a zero-compromise chat fight. Phase 2 plan itself correctly defers OA, death saves, concentration, persistence, enemy AI. |
| Phase 3 rules "DONE for MVP" | Offline `rules.db` / `spells.db` lookups work. Chat does not fully *apply* spell or monster rules. |
| Phase 4 memory "DONE for MVP" | Postgres + tools + session summaries exist. Recap quality and grounding are thin. |
| Success criterion "Gain items, XP, and progress" | Leveling API exists; AI play loop does not award XP or resolve most item uses. |
| Intent redesign "complete" after merge | Merged to master; live sign-off and data loop still open ([`SESSION_RECAP_2026-07-27.md`](SESSION_RECAP_2026-07-27.md)). |

**Rule for future docs:** mark DONE only when the ASCII chat path enforces the behavior without narrator invention.

---

## 5. Recommended build order

Do not start with campaign-manager unification. Order by play-blocking severity:

1. **Finish P0.1** — live smoke sign-off; plumb `spell_names`; keep the labeled-example loop.
2. **P0.2** — engine-resolve `rest`, `roll`, `use_item` (minimum potion/heal), then `move`/location.
3. **P1.1** — chat cast applies effects + concentration.
4. **P1.2 / Combat 2b** — chat-driven encounter loop: enemy turns, action economy, death saves, concentration checks; then encounter persistence.
5. **P2** — scene object registry + persistence; XP GameAction + combat/quest awards; consumable pipeline.
6. **P3** — structured recaps / grounding; campaign layer cleanup last.

Existing plans to extend (do not reinvent):

- Intent: [`superpowers/plans/2026-07-26-intent-classifier.md`](superpowers/plans/2026-07-26-intent-classifier.md) (maintenance = data, not new regex brains).
- Combat MVP baseline: [`phase2_combat_rest_plan.md`](phase2_combat_rest_plan.md) — next doc should be **Combat 2b (chat, no deferred 5e)** removing that plan's locked compromises.
- North star: [`chat_gpts_plan.md`](chat_gpts_plan.md) — update DONE language when gaps close.

---

## 6. One-page scoreboard

| Capability | From ASCII chat today |
| :--- | :--- |
| Speak / apology without mutating state | Strong (intent gate); live sign-off still required |
| Attack furniture / named NPC | MVP playable |
| Full initiative combat with enemy turns | Not zero-compromise |
| Cast with real effects | Slot only |
| Rest | Slash yes; chat soft |
| Use item / drink potion | Missing resolver |
| XP / level from play | REST only |
| World memory | Plumbing yes; grounding thin |
| Survive process restart mid-fight | No (encounter in-memory) |

---

## 7. Bottom line

The stack is a **stateful engine with a safer front door**, not yet a zero-compromise solo DM.

Intent redesign stopped the worst class of corruption (speech → Longsword). Phase 2 combat and Phase 4 memory built rails that chat still under-uses. Until classified intents resolve in the engine, spells change targets, and combat enforces 5e without narrator fudge, every session still cuts corners.

Next honest milestone: **P0 closed + one complete chat combat (goblin fight) with engine-owned turns and HP**, no invented numbers.
