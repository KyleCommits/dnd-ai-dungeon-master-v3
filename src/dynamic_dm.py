# src/dynamic_dm.py
import logging
import re
from typing import Dict, List, Any, Optional
from .campaign_state_manager import campaign_state_manager
from .llm_manager import llm_manager
from .rag_manager import rag_manager
from .database import async_session_scope, get_conversation_history, get_session_summaries, get_chat_session_with_campaign, get_campaign_by_name
from .models import ChatMessage, SessionSummary
from .game_actions import game_actions
from .character_manager import character_manager
from .tool_executor import run_tool_loop

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class DynamicDM:
    def __init__(self):
        self.base_dm_prompt = """You are an experienced Dungeon Master running a D&D 5e campaign. Generate immersive, rule-compliant responses that maintain player agency."""

        # define available functions for local LLM tool calling
        self.available_functions = [
            {
                "name": "modify_hp",
                "description": "modify character hp for damage or healing",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "character_id": {
                            "type": "string",
                            "description": "the character id to modify"
                        },
                        "change": {
                            "type": "integer",
                            "description": "hp change (negative for damage, positive for healing)"
                        },
                        "reason": {
                            "type": "string",
                            "description": "reason for the change (e.g. 'goblin sword attack', 'healing potion')"
                        }
                    },
                    "required": ["character_id", "change"]
                }
            },
            {
                "name": "roll_dice_for_character",
                "description": "roll dice for damage, attacks, or checks",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "dice_string": {
                            "type": "string",
                            "description": "dice notation like '1d20', '2d6+3', etc"
                        },
                        "character_id": {
                            "type": "string",
                            "description": "character making the roll (optional)"
                        },
                        "advantage": {
                            "type": "string",
                            "enum": ["normal", "advantage", "disadvantage"],
                            "description": "type of roll"
                        },
                        "description": {
                            "type": "string",
                            "description": "what the roll is for"
                        }
                    },
                    "required": ["dice_string"]
                }
            },
            {
                "name": "apply_condition",
                "description": "apply a condition to a character",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "character_id": {
                            "type": "string",
                            "description": "character to apply condition to"
                        },
                        "condition": {
                            "type": "string",
                            "description": "condition name (poisoned, charmed, etc)"
                        },
                        "duration_rounds": {
                            "type": "integer",
                            "description": "duration in rounds (optional)"
                        },
                        "reason": {
                            "type": "string",
                            "description": "reason for condition"
                        }
                    },
                    "required": ["character_id", "condition"]
                }
            },
            {
                "name": "consume_spell_slot",
                "description": (
                    "Consume a spell slot when a character casts a leveled spell. "
                    "Always pass spell_name; illegals (non-caster / not known) return an error — narrate the failure."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "character_id": {
                            "type": "string",
                            "description": "character casting the spell"
                        },
                        "slot_level": {
                            "type": "integer",
                            "description": "spell slot level to consume"
                        },
                        "spell_name": {
                            "type": "string",
                            "description": "exact spell name (required for legality check)"
                        },
                        "reason": {
                            "type": "string",
                            "description": "optional note"
                        }
                    },
                    "required": ["character_id", "slot_level", "spell_name"]
                }
            },
            {
                "name": "get_character_status",
                "description": "get current character status and stats",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "character_id": {
                            "type": "string",
                            "description": "character to check"
                        }
                    },
                    "required": ["character_id"]
                }
            },
            {
                "name": "trigger_rest",
                "description": "trigger a short or long rest for a character (restores HP/slots)",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "character_id": {"type": "string", "description": "character resting"},
                        "rest_type": {"type": "string", "enum": ["short", "long"], "description": "type of rest"},
                        "reason": {"type": "string", "description": "why they are resting"}
                    },
                    "required": ["character_id", "rest_type"]
                }
            },
            {
                "name": "update_inventory",
                "description": "add or remove items from character inventory",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "character_id": {"type": "string"},
                        "item": {"type": "string", "description": "item name"},
                        "quantity": {"type": "integer", "description": "positive to add, negative to remove"},
                        "reason": {"type": "string"}
                    },
                    "required": ["character_id", "item"]
                }
            },
            {
                "name": "equip_item",
                "description": "equip an item from inventory and recalculate AC",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "character_id": {"type": "string"},
                        "item": {"type": "string"},
                        "equipped": {"type": "boolean", "description": "true to equip, false to unequip"},
                        "reason": {"type": "string"}
                    },
                    "required": ["character_id", "item"]
                }
            },
            {
                "name": "unequip_item",
                "description": "unequip an item and recalculate AC",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "character_id": {"type": "string"},
                        "item": {"type": "string"},
                        "reason": {"type": "string"}
                    },
                    "required": ["character_id", "item"]
                }
            },
            {
                "name": "lookup_spell",
                "description": "look up a spell from the local spell database (do not invent spell stats)",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "spell_name": {"type": "string"}
                    },
                    "required": ["spell_name"]
                }
            },
            {
                "name": "lookup_monster",
                "description": "look up a monster from the local rules database (do not invent HP/AC/damage)",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "monster_name": {"type": "string"}
                    },
                    "required": ["monster_name"]
                }
            },
            {
                "name": "lookup_item",
                "description": "look up a weapon/armor/gear item from the local rules database",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "item_name": {"type": "string"}
                    },
                    "required": ["item_name"]
                }
            },
            {
                "name": "update_npc_relationship",
                "description": "change NPC trust after a social/story beat (backend memory; do not invent trust numbers in narration)",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "npc_name": {"type": "string"},
                        "trust_delta": {"type": "integer", "description": "change in trust (-100..100 scale)"},
                        "note": {"type": "string"},
                        "reason": {"type": "string"}
                    },
                    "required": ["npc_name"]
                }
            },
            {
                "name": "update_plot_thread",
                "description": "update a plot thread status (active/completed/failed/dormant) or add a note",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "thread_id": {"type": "string"},
                        "status": {"type": "string"},
                        "note": {"type": "string"},
                        "name": {"type": "string"},
                        "create_if_missing": {"type": "boolean"}
                    },
                    "required": ["thread_id"]
                }
            },
            {
                "name": "set_location",
                "description": "set the party's current location in world memory",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "location": {"type": "string"},
                        "reason": {"type": "string"}
                    },
                    "required": ["location"]
                }
            },
            {
                "name": "record_plot_event",
                "description": "record a meaningful story/player action against active plot threads",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "event": {"type": "string"},
                        "location": {"type": "string"}
                    },
                    "required": ["event"]
                }
            },
            {
                "name": "start_combat_encounter",
                "description": "create a combat encounter (add combatants then begin_combat)",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "campaign_id": {"type": "string"},
                        "encounter_name": {"type": "string"}
                    },
                    "required": ["campaign_id", "encounter_name"]
                }
            },
            {
                "name": "add_monster_to_encounter",
                "description": "add a catalog monster to an encounter by name (e.g. goblin)",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "encounter_id": {"type": "string"},
                        "monster_name": {"type": "string"}
                    },
                    "required": ["encounter_id", "monster_name"]
                }
            },
            {
                "name": "add_character_to_encounter",
                "description": "add a player character to an encounter",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "encounter_id": {"type": "string"},
                        "character_id": {"type": "string"}
                    },
                    "required": ["encounter_id", "character_id"]
                }
            },
            {
                "name": "begin_combat",
                "description": "roll initiative and start combat after combatants are added",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "encounter_id": {"type": "string"}
                    },
                    "required": ["encounter_id"]
                }
            },
            {
                "name": "get_combat_status",
                "description": "get initiative order, HP, and whose turn it is",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "encounter_id": {"type": "string"}
                    },
                    "required": ["encounter_id"]
                }
            },
            {
                "name": "resolve_attack",
                "description": "resolve an attack roll vs AC and apply damage on hit",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "encounter_id": {"type": "string"},
                        "attacker_id": {"type": "string"},
                        "target_id": {"type": "string"}
                    },
                    "required": ["encounter_id", "attacker_id", "target_id"]
                }
            },
            {
                "name": "resolve_player_attack",
                "description": (
                    "Resolve a PC attack against an object or creature: rolls attack+damage, "
                    "applies object HP. Use for 'I attack the table with my sword' style actions."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "character_id": {"type": "string"},
                        "target_name": {"type": "string", "description": "e.g. table, goblin"},
                        "method": {"type": "string", "description": "weapon or unarmed"},
                        "target_kind": {
                            "type": "string",
                            "description": "object or creature (optional)",
                        },
                    },
                    "required": ["character_id", "target_name", "method"],
                },
            },
            {
                "name": "next_combat_turn",
                "description": "advance to the next combatant's turn",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "encounter_id": {"type": "string"}
                    },
                    "required": ["encounter_id"]
                }
            },
            {
                "name": "end_combat",
                "description": "end combat and remove the encounter",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "encounter_id": {"type": "string"}
                    },
                    "required": ["encounter_id"]
                }
            }
        ]

    async def generate_response(
        self, player_message: str, session_id: str, user_id: str = "player1"
    ) -> str:
        if not campaign_state_manager.current_state:
            return "Please load a campaign first."

        try:
            short_term_history: List[ChatMessage] = []
            long_term_summaries: List[SessionSummary] = []
            campaign_id: Optional[int] = None

            async with async_session_scope() as db_session:
                short_term_history = await get_conversation_history(db_session, session_id, limit=15)
                chat_session = await get_chat_session_with_campaign(db_session, session_id)
                if chat_session and chat_session.campaign:
                    long_term_summaries = await get_session_summaries(db_session, chat_session.campaign.id)
                    campaign_id = chat_session.campaign.id

                if campaign_id is None and campaign_state_manager.current_state:
                    campaign = await get_campaign_by_name(
                        db_session, campaign_state_manager.current_state.campaign_name
                    )
                    if campaign:
                        campaign_id = campaign.id

            campaign_context = campaign_state_manager.get_campaign_context()

            dm_response = await self._generate_contextual_response(
                player_message,
                user_id,
                campaign_context,
                short_term_history,
                long_term_summaries,
                user_id=user_id,
                campaign_id=campaign_id,
            )

            return dm_response

        except Exception as e:
            logging.error(f"Error generating dynamic DM response: {e}", exc_info=True)
            return "The DM pauses thoughtfully, considering the situation..."

    async def _generate_contextual_response(
        self,
        player_message: str,
        player_name: str,
        campaign_context: str,
        conversation_history: List[ChatMessage],
        session_summaries: List[SessionSummary],
        user_id: str = "player1",
        campaign_id: Optional[int] = None,
    ) -> str:

        summary_context = self._format_session_summaries(session_summaries)

        if not session_summaries and len(conversation_history) <= 1:
            session_instructions = "This is Session 0. Begin with a captivating introduction to the campaign. Set the scene and establish the starting situation."
        elif not session_summaries:
            session_instructions = "You have just introduced the campaign. The player is now responding. Continue the scene naturally based on their action. Do not repeat the introduction."
        elif len(conversation_history) <= 1:
            session_instructions = "This is the start of a new session. Begin with 'Last time on [Campaign Name]...' followed by a brief 1-2 sentence recap from the most recent session summary, then describe the current scene."
        else:
            session_instructions = "Continue the scene naturally based on the player's action."

        response_prompt = f"""{self.base_dm_prompt}
{summary_context}

INSTRUCTIONS: {session_instructions}

CURRENT CAMPAIGN STATE:
{campaign_context}

PLAYER ACTION: {player_name} says/does: \"{player_message}\"

RESPONSE RULES:
- Keep responses CONCISE (2-4 sentences max unless combat/complex scene).
- Use markdown formatting: **bold** for emphasis, *italics* for NPC speech.
- Format: "NPC Name: *'dialogue'*" for character speech.
- Narrate the scene and outcomes naturally.
- CRITICAL: Do NOT ask \"what do you do?\". Let the scene progress.
- CRITICAL: Do NOT reveal hidden information (emotions, motives) without an ability check.
"""

        try:
            massive_context_prompt = await self._build_massive_context(
                response_prompt, conversation_history, session_summaries
            )

            active_character_info = await self._get_active_character_info(user_id, campaign_id)
            active_character_id = await self._get_active_character_id(user_id, campaign_id)

            function_prompt = f"""{massive_context_prompt}

ACTIVE CHARACTER INFO:
{active_character_info}

FUNCTION CALLING INSTRUCTIONS:
- To change game state you MUST emit TOOL_CALL / END_TOOL_CALL blocks (see protocol in system tools section).
- Never narrate damage/HP/dice numbers unless a tool result provided them.
- Incomplete actions (vague attack, dash, sneak without detail): ask ONE clarifying question; do not resolve hit/damage/success yet.
- Never continue a prior invented disaster if tools or clarification say otherwise.
- Examples:
  (1) Attack with a clear weapon/target: emit resolve_player_attack (objects) or resolve_attack (combat) before saying hit/miss/damage.
  (2) Cast: lookup_spell then consume_spell_slot with spell_name (and character_id, slot_level).
  (3) Illegal cast (e.g. Fighter Fireball): call the tools; if they error, narrate the failure — do not invent a fireball.
- Use modify_hp when characters take damage or heal outside structured combat
- Use roll_dice_for_character for ability checks and saving throws
- Use apply_condition for status effects
- Use consume_spell_slot when characters cast leveled spells (always include spell_name)
- Use trigger_rest for short/long rests
- Use update_inventory / equip_item / unequip_item for gear
- Use lookup_spell / lookup_monster / lookup_item before inventing stats (local DB only)
- Use update_npc_relationship when trust/attitude changes; use set_location when the party moves
- Use update_plot_thread / record_plot_event for story beats (backend remembers; do not invent trust)
- Use get_character_status to check stats
- COMBAT: start_combat_encounter → add_character_to_encounter / add_monster_to_encounter → begin_combat → resolve_attack → next_combat_turn → end_combat
- Prefer resolve_attack over narrating hit/miss without rolls
- Use the active character ID from ACTIVE CHARACTER INFO above
- Never invent dice, HP, AC, damage, or trust numbers when a tool can supply them
"""

            async def _gen(prompt, max_new_tokens=160, available_functions=None):
                return await llm_manager.generate(
                    prompt,
                    max_new_tokens=max_new_tokens,
                    use_massive_context=True,
                    available_functions=available_functions,
                )

            weapon_names = await self._get_active_weapon_names(user_id, campaign_id)

            dm_response = await run_tool_loop(
                function_prompt,
                self.available_functions,
                _gen,
                max_rounds=2,
                max_new_tokens=160,
                max_narration_tokens=140,
                player_message=player_message,
                character_id=str(active_character_id) if active_character_id else None,
                user_id=user_id,
                weapon_names=weapon_names,
            )
            return self._clean_response(dm_response)
        except Exception as e:
            logging.error(f"Error generating contextual response: {e}", exc_info=True)
            return "The DM stumbles, momentarily losing the thread of the story."

    async def _resolve_active_character(self, user_id: str, campaign_id: Optional[int]):
        if campaign_id is None:
            return None
        from sqlalchemy import select
        from sqlalchemy.orm import selectinload

        from .character_models import Character

        async with async_session_scope() as db:
            character = await character_manager.get_active_character(db, user_id, campaign_id)
            if not character:
                chars = await character_manager.get_user_characters(db, user_id, campaign_id)
                character = chars[0] if chars else None
            if not character:
                return None
            # Re-fetch with equipment eagerly loaded (session expire_on_commit=False)
            result = await db.execute(
                select(Character)
                .where(Character.id == character.id)
                .options(selectinload(Character.equipment))
            )
            return result.scalar_one_or_none()

    async def _get_active_character_id(
        self, user_id: str = "player1", campaign_id: Optional[int] = None
    ) -> Optional[int]:
        try:
            character = await self._resolve_active_character(user_id, campaign_id)
            return character.id if character else None
        except Exception as e:
            print(f"ERROR: error getting active character id: {e}")
            return None

    async def _get_active_character_info(
        self, user_id: str = "player1", campaign_id: Optional[int] = None
    ) -> str:
        """Load active character for the user/campaign for tool calling."""
        try:
            if campaign_id is None:
                return "No active character (no campaign id). Tool calls needing character_id will fail until one is selected."

            character = await self._resolve_active_character(user_id, campaign_id)
            if not character:
                return (
                    f"No active character for user={user_id} campaign_id={campaign_id}. "
                    "Ask the player to select a character before combat/tool actions."
                )

            return (
                f"Active Character: {character.name} (ID: {character.id}) - "
                f"Level {character.level} {character.race} {character.class_name} - "
                f"HP: {character.current_hp}/{character.max_hp} - AC: {character.armor_class}"
            )
        except Exception as e:
            print(f"ERROR: error getting active character info: {e}")
            return f"Error getting character info: {e}"

    async def _get_active_weapon_names(
        self, user_id: str = "player1", campaign_id: Optional[int] = None
    ) -> List[str]:
        """Inventory weapon names for Layer-1 intent hints (engine still validates ownership)."""
        if campaign_id is None:
            return []
        try:
            from sqlalchemy import select
            from sqlalchemy.orm import selectinload

            from .character_models import Character
            from .weapon_choose import is_inventory_weapon

            async with async_session_scope() as db:
                character = await character_manager.get_active_character(
                    db, user_id, campaign_id
                )
                if not character:
                    chars = await character_manager.get_user_characters(
                        db, user_id, campaign_id
                    )
                    character = chars[0] if chars else None
                if not character:
                    return []
                result = await db.execute(
                    select(Character)
                    .where(Character.id == character.id)
                    .options(selectinload(Character.equipment))
                )
                character = result.scalar_one_or_none()
                if not character:
                    return []
                names: List[str] = []
                for eq in character.equipment or []:
                    name = getattr(eq, "item_name", None)
                    if name and is_inventory_weapon(name):
                        names.append(name)
                return names
        except Exception as e:
            print(f"ERROR: error getting weapon names: {e}")
            return []

    def _format_conversation_history(self, history: List[ChatMessage]) -> str:
        if not history:
            return "No recent conversation."
        return "\n".join([f"{'Player' if msg.message_type == 'player' else 'DM'}: {msg.content}" for msg in history])

    def _format_session_summaries(self, summaries: List[SessionSummary]) -> str:
        if not summaries:
            return "SESSION HISTORY: This is the very first session (Session 0)."
        
        formatted_summaries = ["PREVIOUS SESSION SUMMARIES (LONG-TERM MEMORY):"]
        for summary in summaries:
            formatted_summaries.append(f"- Session {summary.session_number}: {summary.summary}")
        return "\n".join(formatted_summaries)

    async def _build_massive_context(
        self, 
        base_prompt: str, 
        conversation_history: List[ChatMessage],
        session_summaries: List[SessionSummary]
    ) -> str:
        """
        Build DM context sized for a 12GB GPU local narrator (Mistral 7B / Llama 8B).
        Do NOT inject the full campaign markdown (that OOMs attention).
        """
        # Keep chat short; each message capped (L1 latency: smaller prefill)
        recent = conversation_history[-4:] if conversation_history else []
        history_lines = []
        for msg in recent:
            role = "Player" if msg.message_type == "player" else "DM"
            content = (msg.content or "")[:250]
            history_lines.append(f"{role}: {content}")
        history_str = "\n".join(history_lines) if history_lines else "No recent conversation."

        # Cap long-term memory
        summary_str = self._format_session_summaries(session_summaries[-3:])

        # Compact world state (location, NPC trust, plot) + short campaign excerpt
        world_state = campaign_state_manager.get_campaign_context()
        campaign_excerpt = await self._load_campaign_excerpt(max_chars=1800)

        return f"""
# campaign state (live memory)
{world_state}

# campaign excerpt (not the full book — look up details via tools if needed)
{campaign_excerpt}

# previous sessions
{summary_str}

# recent chat
{history_str}

# current situation
{base_prompt}

Stay in character as DM. Prefer tools for stats/trust. Keep replies concise.
"""

    async def _load_campaign_excerpt(self, max_chars: int = 3500) -> str:
        """Load a bounded campaign excerpt for local-GPU prompts."""
        try:
            if not campaign_state_manager.current_state or not campaign_state_manager.current_state.campaign_name:
                return "No active campaign loaded."
            campaign_name = campaign_state_manager.current_state.campaign_name
            from .config import settings
            import os
            campaign_file_path = os.path.join(settings.custom_campaign_path, f"{campaign_name}.md")
            if not os.path.exists(campaign_file_path):
                return f"Campaign file for '{campaign_name}' not found."
            with open(campaign_file_path, 'r', encoding='utf-8') as file:
                text = file.read()
            if len(text) <= max_chars:
                return text
            # Prefer head (setup) + mention of current location if present
            location = campaign_state_manager.current_state.location or ""
            head = text[: max_chars - 400]
            loc_bit = ""
            if location and location.lower() in text.lower():
                idx = text.lower().find(location.lower())
                start = max(0, idx - 200)
                loc_bit = "\n...\n" + text[start : start + 400]
            return head + loc_bit + "\n\n[campaign truncated for local GPU memory]"
        except Exception as e:
            logging.error(f"Error loading campaign excerpt: {e}")
            return f"Error loading campaign content: {str(e)}"

    async def _load_full_campaign_content(self) -> str:
        """Legacy helper — prefer _load_campaign_excerpt for chat prompts."""
        return await self._load_campaign_excerpt(max_chars=8000)

    def _clean_response(self, response: str) -> str:
        response = re.sub(r'(DM NOTE|NOTE TO DM|INSTRUCTION).*?\n', '', response, flags=re.IGNORECASE)
        response = re.sub(r'^(DM:\s*)+', '', response.strip())
        response = re.sub(r'\s{2,}', ' ', response).strip()
        return response

dynamic_dm = DynamicDM()
