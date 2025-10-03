import os
import requests
from openai import OpenAI
from typing import Dict, List, Optional
import re
import json
from datetime import datetime
from .dice_roller import DiceRoller
from .dnd_rules_parser import DnDRulesManager  # Make sure this import path is correct

class AIDungeonMaster:
    def __init__(self, api_key: str, rules_manager: DnDRulesManager):
        """Initialize the AI Dungeon Master"""
        self.client = OpenAI(
            base_url="https://api.x.ai/v1",
            api_key=api_key
        )
        self.rules_manager = rules_manager
        self.conversation_history = []
        self.pending_roll_context = None
        self.pending_group_check = {
            'active': False,
            'context': None,
            'rolls': {},
            'check_type': None
        }
        # Initialize base rules from rules manager
        self.base_rules = self._create_base_rules_context()
        # Add current scene tracking
        self.current_scene = {
            'description': None,
            'characters': [],
            'objects': [],
            'context': None
        }

    def _create_base_rules_context(self):
        """Create the base rules context used across all interactions"""
        return {
            "core_rules": {
                "abilities": self.rules_manager.get_rules_section("Abilities"),
                "skill_checks": self._get_skill_rules(),
                "saving_throws": self._get_saving_throw_rules(),
                "difficulty_classes": {
                    "very_easy": 5,
                    "easy": 10,
                    "medium": 15,
                    "hard": 20,
                    "very_hard": 25,
                    "nearly_impossible": 30
                }
            }
        }

    def _get_skill_rules(self) -> dict:
        """Extract skill check rules from Abilities.md in Gameplay section"""
        gameplay_rules = self.rules_manager.get_rules_section("Abilities")
        if gameplay_rules:
            return {
                "description": "Skill checks test a character's abilities in specific areas",
                "abilities": {
                    "strength": ["Athletics"],
                    "dexterity": ["Acrobatics", "Sleight of Hand", "Stealth"],
                    "intelligence": ["Arcana", "History", "Investigation", "Nature", "Religion"],
                    "wisdom": ["Animal Handling", "Insight", "Medicine", "Perception", "Survival"],
                    "charisma": ["Deception", "Intimidation", "Performance", "Persuasion"]
                },
                "rules": gameplay_rules
            }
        return {}

    def _get_saving_throw_rules(self) -> dict:
        """Extract saving throw rules from Abilities.md in Gameplay section"""
        gameplay_rules = self.rules_manager.get_rules_section("Abilities")
        if gameplay_rules:
            return {
                "description": "Saving throws represent attempts to resist harmful effects",
                "abilities": ["Strength", "Dexterity", "Constitution", "Intelligence", "Wisdom", "Charisma"],
                "rules": gameplay_rules
            }
        return {}

    def get_relevant_context(self, action: str, max_tokens: int = 4000) -> str:
        """Get relevant rules context based on the action with token limit"""
        relevant_rules = self.rules_manager.get_relevant_rules(action, max_tokens)
        
        context = []
        context_length = 0
        
        # Add base context
        context.append("# D&D Rules Context")
        
        # Add relevant rules if found, with length check
        if relevant_rules and relevant_rules != "No relevant rules found.":
            # Truncate rules if too long
            if len(relevant_rules) > max_tokens:
                relevant_rules = relevant_rules[:max_tokens] + "\n[Content truncated due to length...]"
            context.append(relevant_rules)
        
        # Add recent conversation history (last 3 exchanges)
        if self.conversation_history:
            context.append("\n# Recent Conversation")
            recent = self.conversation_history[-3:]
            for msg in recent:
                context.append(f"{msg['role']}: {msg['content']}")
        
        return "\n\n".join(context)

    async def process_roll_result(self, roll_result: dict, roll_context: dict = None) -> dict:
        """Process a dice roll result with relevant rules context"""
        if not roll_context:
            return {'narrative': None}

        # Get specific rules based on roll type
        skill_name = roll_context.get('skill_name', '').lower()
        ability_score = roll_context.get('ability_score', '').lower()

        # Build context-specific rules
        rules_context = {
            "roll_type": roll_context['roll_type'],
            "relevant_rules": self._create_base_rules_context(),
            "skill_specific": self._get_specific_skill_rules(skill_name, ability_score)
        }

        messages = [
            {
                "role": "system",
                "content": (
                    "You are a D&D Game Master. Use these rules for context:\n"
                    f"{json.dumps(rules_context, indent=2)}\n\n"
                    f"This is a {skill_name} check using {ability_score}.\n"
                    "Narrate the outcome based on the roll and context."
                )
            },
            {
                "role": "user",
                "content": (
                    f"Roll Result: {roll_context['total']}\n"
                    f"Previous Context: {roll_context.get('previous_message', 'No context available')}"
                )
            }
        ]

        # Add scene context
        if self.current_scene:
            messages.append({
                "role": "system",
                "content": f"Current scene: {self.current_scene}"
            })

        # Add roll context
        if roll_context and roll_context.get('previous_message'):
            messages.append({
                "role": "system",
                "content": f"Player's action: {roll_context['previous_message']}"
            })

        # Add the roll result
        messages.append({
            "role": "user",
            "content": f"Player rolled a {roll_result['total']}"
        })

        # Add recent conversation history
        for hist in self.conversation_history[-3:]:
            messages.append(hist)

        try:
            completion = self.client.chat.completions.create(
                model="grok-3-mini",
                messages=messages,
                temperature=0.7
            )

            response = completion.choices[0].message.content

            # Store as part of conversation history
            self.conversation_history.append({
                "role": "assistant",
                "content": response
            })

            return {"narrative": response}

        except Exception as e:
            print(f"Error processing roll result: {e}")
            return {"narrative": "The DM considers the outcome..."}

    async def process_player_action(self, player_name: str, message: str) -> dict:
        """Process a player's action with improved context"""
        # Get relevant rules context
        rules_context = self.get_relevant_context(message)
        
        # Add scene state tracking
        current_scene_context = (
            f"Current Scene State:\n{self.current_scene['description']}\n" if self.current_scene['description'] 
            else "No current scene established."
        )
        
        # Add interaction type classification
        is_question = any(q in message.lower() for q in ['?', 'what', 'how', 'where', 'when', 'who', 'why'])
        is_action = not is_question and any(v in message.lower() for v in ['i', 'we', 'my', 'our'])
        
        messages = [
            {
                "role": "system",
                "content": (
                    "You are a D&D Game Master. IMPORTANT RULES:\n"
                    "1. NEVER ask 'what do you do next?' or similar prompting questions\n"
                    "2. NEVER end responses with 'what would you like to do?'\n"
                    "3. Instead, describe outcomes, consequences, and ongoing events\n"
                    "4. Focus on describing NPC reactions and environmental changes\n"
                    "5. If a player asks a question, answer directly\n"
                    "6. If a player takes an action, describe the result\n\n"
                    f"D&D Rules Context:\n{rules_context}\n\n"  # Added rules context
                    f"Scene Context: {current_scene_context}\n"
                    f"Interaction Type: {'Question' if is_question else 'Action' if is_action else 'Statement'}"
                )
            },
            {
                "role": "user",
                "content": f"{player_name}: {message}"
            }
        ]

        try:
            completion = self.client.chat.completions.create(
                model="grok-3-mini",
                messages=messages,
                temperature=0.7
            )
            
            response = completion.choices[0].message.content
            
            # Update scene tracking if description is given
            if not self.current_scene['description'] and len(response) > 50:
                self.current_scene['description'] = response[:200]  # Store first 200 chars as context
                
            return {
                'narrative': response,
                'commands': [],  # Add any generated commands
                'group_check': None  # Add group check if needed
            }
            
        except Exception as e:
            print(f"Error in AI response: {e}")
            return {
                'narrative': "Error generating response",
                'commands': [],
                'group_check': None
            }

    async def narrate_scene(self, scene_description: str) -> str:
        messages = [
            {
                "role": "system",
                "content": (
                    f"{self.base_rules}\n"
                    "Additional Scene Rules:\n"
                    "1. Paint vivid, atmospheric descriptions\n"
                    "2. Include sensory details\n"
                    "3. Describe NPC positions and actions\n"
                    "4. Set the mood and tone\n"
                    "5. End with environmental details"
                )
            }
        ]

        # Add current scene if available
        if self.current_scene:
            messages.append({
                "role": "system",
                "content": f"Current scene: {self.current_scene}"
            })

        # Add recent conversation history
        for hist in self.conversation_history[-3:]:
            messages.append(hist)

        # Add scene description
        messages.append({
            "role": "user",
            "content": f"Describe the scene: {scene_description}"
        })

        try:
            completion = self.client.chat.completions.create(
                model="grok-3-mini",
                messages=messages,
                temperature=0.7
            )

            response = completion.choices[0].message.content

            # Update conversation history
            self.conversation_history.append({
                "role": "assistant",
                "content": response
            })

            # Store current scene
            self.current_scene = response

            return response

        except Exception as e:
            print(f"Error narrating scene: {e}")
            return "The scene is shrouded in mystery..."

    async def handle_npc_action(self, npc_name: str, situation: str) -> Dict:
        """Handle NPC actions with proper rules context"""
        # Get relevant NPC and social interaction rules
        relevant_rules = self.rules_manager.get_relevant_rules(f"NPC {situation}")
        
        messages = [
            {
                "role": "system",
                "content": (
                    f"{self.base_rules}\n"
                    f"D&D Rules Context:\n{relevant_rules}\n"
                    "NPC Interaction Rules:\n"
                    "1. Follow D&D social interaction guidelines\n"
                    "2. Use appropriate DC thresholds for social checks\n"
                    "3. Consider NPC attitude and disposition"
                )
            }
        ]

        # Add current scene if available
        if self.current_scene:
            messages.append({
                "role": "system",
                "content": f"Current scene: {self.current_scene}"
            })

        # Add recent conversation history
        for hist in self.conversation_history[-3:]:
            messages.append(hist)

        # Add NPC action situation
        messages.append({
            "role": "user",
            "content": f"{npc_name} in {situation}"
        })

        try:
            completion = self.client.chat.completions.create(
                model="grok-3-mini",
                messages=messages,
                temperature=0.7
            )

            response = completion.choices[0].message.content

            # Update conversation history
            self.conversation_history.append({
                "role": "assistant",
                "content": response
            })

            return {
                "narrative": response,
                "npc_name": npc_name
            }

        except Exception as e:
            print(f"Error handling NPC action: {e}")
            return {
                "narrative": "The NPC's intentions are unclear...",
                "npc_name": npc_name
            }

    async def generate_summary(self, content: str) -> str:
        """Generate a summary of session messages"""
        messages = [
            {
                "role": "system",
                "content": (
                    "You are a D&D session note taker. Create concise summaries that:\n"
                    "1. Focus on key events and decisions\n"
                    "2. Track important NPC interactions\n"
                    "3. Note significant character developments\n"
                    "4. Record combat outcomes\n"
                    "5. Highlight quest progress\n"
                    "Format in clear bullet points."
                )
            },
            {
                "role": "user",
                "content": content
            }
        ]

        try:
            completion = self.client.chat.completions.create(
                model="grok-3-mini",
                messages=messages,
                temperature=0.7
            )
            return completion.choices[0].message.content
        except Exception as e:
            print(f"Error generating summary: {e}")
            return "Error generating summary"

    async def generate_character(self) -> Dict:
        """Generate a D&D character with stats, proficiencies, and equipment"""
        # Get relevant rules sections with length limits
        race_rules = self.rules_manager.get_rules_section('races', max_tokens=2000)
        class_rules = self.rules_manager.get_rules_section('classes', max_tokens=2000)
        equipment_rules = self.rules_manager.get_rules_section('equipment', max_tokens=1000)
        
        context = (
            "# Available Rules\n\n"
            f"## Races\n{race_rules}\n\n"
            f"## Classes\n{class_rules}\n\n"
            f"## Equipment\n{equipment_rules}"
        )
        
        # Truncate context if too long
        if len(context) > 5000:
            context = context[:5000] + "\n[Content truncated due to length...]"
        
        messages = [
            {
                "role": "system",
                "content": (
                    f"{context}\n\n"
                    "Generate a D&D character following these rules:\n"
                    "1. Use standard array (15,14,13,12,10,8)\n"
                    "2. Follow PHB race/class features\n"
                    "3. Include correct saving throw proficiencies for class\n"
                    "4. Include correct skill proficiencies based on class and background\n"
                    "5. Add starting equipment\n"
                    "Format response EXACTLY as this JSON:\n"
                    '{\n'
                    '    "name": "Character Name",\n'
                    '    "race": "Race Name",\n'
                    '    "class": "Class Name",\n'
                    '    "background": "Background Name",\n'
                    '    "hp": 10,\n'
                    '    "armor_class": 15,\n'
                    '    "stats": {\n'
                    '        "strength": 15,\n'
                    '        "dexterity": 14,\n'
                    '        "constitution": 13,\n'
                    '        "intelligence": 12,\n'
                    '        "wisdom": 10,\n'
                    '        "charisma": 8\n'
                    '    },\n'
                    '    "saving_throws": {\n'
                    '        "strength": false,\n'
                    '        "dexterity": false,\n'
                    '        "constitution": false,\n'
                    '        "intelligence": false,\n'
                    '        "wisdom": false,\n'
                    '        "charisma": false\n'
                    '    },\n'
                    '    "skills": {\n'
                    '        "acrobatics": false,\n'
                    '        "animal_handling": false,\n'
                    '        "arcana": false,\n'
                    '        "athletics": false,\n'
                    '        "deception": false,\n'
                    '        "history": false,\n'
                    '        "insight": false,\n'
                    '        "intimidation": false,\n'
                    '        "investigation": false,\n'
                    '        "medicine": false,\n'
                    '        "nature": false,\n'
                    '        "perception": false,\n'
                    '        "performance": false,\n'
                    '        "persuasion": false,\n'
                    '        "religion": false,\n'
                    '        "sleight_of_hand": false,\n'
                    '        "stealth": false,\n'
                    '        "survival": false\n'
                    '    },\n'
                    '    "equipment": [\n'
                    '        {\n'
                    '            "name": "Item Name",\n'
                    '            "type": "weapon/armor/gear",\n'
                    '            "description": "Item description"\n'
                    '        }\n'
                    '    ]\n'
                    '}'
                )
            },
            {
                "role": "user",
                "content": "Generate a random level 1 D&D character with appropriate saving throw and skill proficiencies for their class."
            }
        ]

        try:
            completion = self.client.chat.completions.create(
                model="grok-3-mini",
                messages=messages,
                temperature=0.7
            )

            # Extract JSON from response
            response = completion.choices[0].message.content
            # Find JSON block between curly braces
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if not json_match:
                raise ValueError("No JSON found in response")
                
            char_data = json.loads(json_match.group())

            # Validate required fields
            required_fields = ['name', 'race', 'class', 'hp', 'armor_class', 'stats', 
                             'saving_throws', 'skills', 'equipment']
            missing_fields = [field for field in required_fields if field not in char_data]
            if missing_fields:
                raise ValueError(f"Missing required fields: {', '.join(missing_fields)}")

            return char_data

        except json.JSONDecodeError as e:
            print(f"JSON parsing error: {e}")
            print(f"Raw response: {response}")
            return self._generate_fallback_character()
        except Exception as e:
            print(f"Error generating character: {e}")
            return self._generate_fallback_character()

    def _generate_fallback_character(self) -> Dict:
        """Generate a basic fighter as fallback"""
        return {
            'name': 'Generic Fighter',
            'race': 'Human',
            'class': 'Fighter',
            'background': 'Soldier',
            'hp': 10,
            'armor_class': 16,
            'stats': {
                'strength': 15,
                'dexterity': 14,
                'constitution': 13,
                'intelligence': 12,
                'wisdom': 10,
                'charisma': 8
            },
            'saving_throws': {
                'strength': True,
                'constitution': True,
                'dexterity': False,
                'intelligence': False,
                'wisdom': False,
                'charisma': False
            },
            'skills': {
                'acrobatics': False,
                'animal_handling': False,
                'arcana': False,
                'athletics': True,  # Fighter skill
                'deception': False,
                'history': False,
                'insight': False,
                'intimidation': True,  # Background skill
                'investigation': False,
                'medicine': False,
                'nature': False,
                'perception': False,
                'performance': False,
                'persuasion': False,
                'religion': False,
                'sleight_of_hand': False,
                'stealth': False,
                'survival': False
            },
            'equipment': [
                {'name': 'Longsword', 'type': 'weapon', 'description': 'Martial melee weapon'},
                {'name': 'Chain Mail', 'type': 'armor', 'description': 'Heavy armor'},
                {'name': 'Shield', 'type': 'armor', 'description': 'AC +2'},
                {'name': "Explorer's Pack", 'type': 'gear', 'description': 'Basic adventuring gear'}
            ]
        }

    def _compress_conversation_history(self):
        """Compress conversation history to prevent token limits"""
        if len(self.conversation_history) > self.max_history_length:
            # Keep the first message (system context) and last 5 messages
            summary = self._generate_conversation_summary(
                self.conversation_history[1:-5]
            )
            self.conversation_history = [
                self.conversation_history[0],  # Keep initial system message
                {"role": "system", "content": f"Previous conversation summary: {summary}"},
                *self.conversation_history[-5:]  # Keep last 5 messages
            ]

    async def refresh_rules_context(self):
        """Refresh the base rules context"""
        self.base_rules = self._create_base_rules_context()
        return {"status": "Rules context refreshed"}

    def determine_check_type(self, action: str) -> str:
        """
        Determine if an action requires an ability check and what type.
        Returns None if no check needed.
        """
        # Common action keywords that might trigger specific checks
        check_keywords = {
            'strength': ['lift', 'push', 'pull', 'break', 'bend', 'climb', 'jump'],
            'dexterity': ['sneak', 'hide', 'balance', 'dodge', 'catch', 'pick'],
            'constitution': ['endure', 'resist', 'withstand', 'hold breath'],
            'intelligence': ['recall', 'investigate', 'analyze', 'research', 'study'],
            'wisdom': ['spot', 'notice', 'sense', 'perceive', 'track', 'survive'],
            'charisma': ['persuade', 'convince', 'deceive', 'intimidate', 'perform']
        }

        action = action.lower()
        
        # Don't check for simple actions
        simple_actions = ['walk', 'look', 'say', 'speak', 'sit', 'stand']
        if any(word in action for word in simple_actions):
            return None

        # Check each ability's keywords
        for ability, keywords in check_keywords.items():
            if any(keyword in action for keyword in keywords):
                return ability

        # Default to None if no check needed
        return None

    def _get_specific_skill_rules(self, skill_name: str, ability_score: str) -> dict:
        """Get rules specific to a skill and ability combination"""
        gameplay_rules = self.rules_manager.get_rules_section("Abilities")
        
        return {
            "skill": {
                "name": skill_name,
                "ability": ability_score,
                "description": f"A {skill_name} check measures ability to {skill_name.replace('_', ' ')}",
                "related_rules": gameplay_rules
            }
        }

