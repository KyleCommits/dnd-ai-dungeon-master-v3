# src/dynamic_dm.py
import logging
import re
from typing import Dict, List, Any
from .campaign_state_manager import campaign_state_manager
from .llm_manager import llm_manager
from .rag_manager import rag_manager
from .database import get_db_session, get_conversation_history, get_session_summaries, get_chat_session_with_campaign
from .models import ChatMessage, SessionSummary
from .game_actions import game_actions

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class DynamicDM:
    def __init__(self):
        self.base_dm_prompt = """You are an experienced Dungeon Master running a D&D 5e campaign. Generate immersive, rule-compliant responses that maintain player agency."""

        # define available functions for gemini
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
                "description": "consume a spell slot for casting",
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
                        "reason": {
                            "type": "string",
                            "description": "spell being cast"
                        }
                    },
                    "required": ["character_id", "slot_level"]
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
            }
        ]

    async def generate_response(self, player_message: str, session_id: str) -> str:
        if not campaign_state_manager.current_state:
            return "Please load a campaign first."
        
        try:
            short_term_history: List[ChatMessage] = []
            long_term_summaries: List[SessionSummary] = []
            
            async for db_session in get_db_session():
                short_term_history = await get_conversation_history(db_session, session_id, limit=15)
                chat_session = await get_chat_session_with_campaign(db_session, session_id)
                if chat_session and chat_session.campaign:
                    long_term_summaries = await get_session_summaries(db_session, chat_session.campaign.id)

            campaign_context = campaign_state_manager.get_campaign_context()
            
            dm_response = await self._generate_contextual_response(
                player_message,
                "player1",  # player_name
                campaign_context,
                short_term_history,
                long_term_summaries
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
        session_summaries: List[SessionSummary]
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

            # get active character info for functions
            active_character_info = await self._get_active_character_info()

            # add function calling instructions to prompt
            function_prompt = f"""{massive_context_prompt}

ACTIVE CHARACTER INFO:
{active_character_info}

FUNCTION CALLING INSTRUCTIONS:
- You can directly modify game state using function calls
- Use modify_hp() when characters take damage or heal
- Use roll_dice_for_character() for attack rolls, damage rolls, saving throws
- Use apply_condition() when characters get status effects
- Use consume_spell_slot() when characters cast spells
- Use get_character_status() to check character stats
- Always include the actual function results in your response naturally
- Example: "The goblin swings and hits! *rolls damage* You take 6 slashing damage."
- Use the active character ID from the info above when calling functions
"""

            dm_response = await llm_manager.generate(
                function_prompt,
                max_new_tokens=150,
                use_massive_context=True,
                available_functions=self.available_functions
            )
            return self._clean_response(dm_response)
        except Exception as e:
            logging.error(f"Error generating contextual response: {e}", exc_info=True)
            return "The DM stumbles, momentarily losing the thread of the story."

    async def _get_active_character_info(self) -> str:
        """get active character info for function calling"""
        try:
            # for now just return a placeholder since we're having db relationship issues
            return "Active Character: Test Character (ID: 1) - Level 1 Human Fighter - HP: 10/10"

        except Exception as e:
            print(f"ERROR: error getting active character info: {e}")
            return "Error getting character info"

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
        history_str = self._format_conversation_history(conversation_history)
        summary_str = self._format_session_summaries(session_summaries)
        full_campaign_text = await self._load_full_campaign_content()

        massive_context = f"""
# campaign world info
{full_campaign_text}

# campaign history
{summary_str}

# recent chat
{history_str}

# current situation
{base_prompt}

REMEMBER: Use all the information above to provide a coherent, in-character response that respects the established history and current events.
"""
        return massive_context

    async def _load_full_campaign_content(self) -> str:
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
                return file.read()
        except Exception as e:
            logging.error(f"Error loading full campaign content: {e}")
            return f"Error loading campaign content: {str(e)}"

    def _clean_response(self, response: str) -> str:
        response = re.sub(r'(DM NOTE|NOTE TO DM|INSTRUCTION).*?\n', '', response, flags=re.IGNORECASE)
        response = re.sub(r'^(DM:\s*)+', '', response.strip())
        response = re.sub(r'\s{2,}', ' ', response).strip()
        return response

dynamic_dm = DynamicDM()
