# src/campaign_generation/stage_managers.py
import logging
import json
import asyncio
from typing import Dict, Any, Optional, Callable
import openai
import google.generativeai as genai
from .campaign_context_loader import CampaignContextLoader
from ..llm_manager import llm_manager
from ..config import settings

class BaseStageManager:
    """Base class for campaign generation stages"""

    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.context_loader = CampaignContextLoader()

    async def execute(self, prompt: str, previous_results: Dict[str, Any],
                     progress_callback: Optional[Callable] = None) -> Dict[str, Any]:
        """Execute this stage of campaign generation"""
        raise NotImplementedError("Subclasses must implement execute method")

    def clean_json_response(self, response: str) -> str:
        """Clean JSON response from AI models"""
        clean_response = response.strip()
        clean_response = clean_response.replace('```json', '').replace('```', '').strip()

        # Find JSON boundaries
        json_start = clean_response.find('{')
        json_end = clean_response.rfind('}') + 1

        if json_start != -1 and json_end != -1 and json_start < json_end:
            clean_response = clean_response[json_start:json_end]

        # Additional cleaning for common JSON issues
        import re

        # Basic cleanup first
        clean_response = re.sub(r',(\s*[}\]])', r'\1', clean_response)  # Remove trailing commas
        clean_response = re.sub(r'(\s*[{,]\s*)([a-zA-Z_][a-zA-Z0-9_]*)(\s*:)', r'\1"\2"\3', clean_response)  # Quote unquoted keys

        # More aggressive JSON repair for XAI responses
        # Fix common XAI issues like missing commas between array elements
        clean_response = re.sub(r'"\s*\n\s*"', '",\n        "', clean_response)  # Add commas between quoted lines
        clean_response = re.sub(r'}\s*\n\s*{', '},\n    {', clean_response)  # Add commas between objects
        clean_response = re.sub(r']\s*\n\s*"', '],\n    "', clean_response)  # Add commas after arrays

        # Try to balance brackets/braces if truncated
        open_braces = clean_response.count('{')
        close_braces = clean_response.count('}')
        if open_braces > close_braces:
            clean_response += '}' * (open_braces - close_braces)

        open_brackets = clean_response.count('[')
        close_brackets = clean_response.count(']')
        if open_brackets > close_brackets:
            clean_response += ']' * (open_brackets - close_brackets)

        return clean_response


class XAIStageManager(BaseStageManager):
    """Manages XAI-powered generation stages (1-2)"""

    def __init__(self):
        super().__init__()
        self.xai_client = None

        if settings.XAI_API_KEY:
            try:
                clean_api_key = settings.XAI_API_KEY.strip().strip('"').strip("'")
                self.xai_client = openai.OpenAI(
                    api_key=clean_api_key,
                    base_url="https://api.x.ai/v1"
                )
                self.logger.info("XAI client initialized successfully")
            except Exception as e:
                self.logger.error(f"Failed to initialize XAI client: {e}")

    async def execute(self, prompt: str, previous_results: Dict[str, Any],
                     progress_callback: Optional[Callable] = None) -> Dict[str, Any]:
        """Execute XAI-powered stage with condensed context"""

        if not self.xai_client:
            raise RuntimeError("XAI client not available")

        if progress_callback:
            await progress_callback("Loading campaign examples...")

        # Get condensed examples that fit in XAI's 32k token limit
        condensed_context = self.context_loader.get_condensed_examples(5)

        return await self._generate_with_xai(prompt, condensed_context, previous_results, progress_callback)

    async def _generate_with_xai(self, prompt: str, context: str,
                                previous_results: Dict[str, Any],
                                progress_callback: Optional[Callable] = None) -> Dict[str, Any]:
        """Generate content using XAI"""
        raise NotImplementedError("Subclasses must implement XAI generation")


class GeminiStageManager(BaseStageManager):
    """Manages Gemini-powered generation stages (3-4) with massive context"""

    def __init__(self):
        super().__init__()
        self.gemini_client = None

        if settings.GEMINI_API_KEY:
            try:
                genai.configure(api_key=settings.GEMINI_API_KEY)
                self.gemini_client = genai.GenerativeModel('gemini-1.5-flash')
                self.logger.info("Gemini client initialized successfully")
            except Exception as e:
                self.logger.error(f"Failed to initialize Gemini client: {e}")

    async def execute(self, prompt: str, previous_results: Dict[str, Any],
                     progress_callback: Optional[Callable] = None) -> Dict[str, Any]:
        """Execute Gemini-powered stage with massive context"""

        if not self.gemini_client:
            raise RuntimeError("Gemini client not available")

        if progress_callback:
            await progress_callback("Loading full campaign examples (this may take a moment)...")

        # Create massive context with full 7k-line campaign examples
        stage_name = self.__class__.__name__.replace('Manager', '')
        massive_context = self.context_loader.create_massive_context(prompt, stage_name)

        return await self._generate_with_gemini(prompt, massive_context, previous_results, progress_callback)

    async def _generate_with_gemini(self, prompt: str, context: str,
                                  previous_results: Dict[str, Any],
                                  progress_callback: Optional[Callable] = None) -> Dict[str, Any]:
        """Generate content using Gemini with massive context"""
        raise NotImplementedError("Subclasses must implement Gemini generation")


class LocalLLMStageManager(BaseStageManager):
    """Manages local LLM-powered generation stages (5-6)"""

    async def execute(self, prompt: str, previous_results: Dict[str, Any],
                     progress_callback: Optional[Callable] = None) -> Dict[str, Any]:
        """Execute local LLM-powered stage"""

        if progress_callback:
            await progress_callback("Processing with local LLM...")

        return await self._generate_with_local_llm(prompt, previous_results, progress_callback)

    async def _generate_with_local_llm(self, prompt: str, previous_results: Dict[str, Any],
                                     progress_callback: Optional[Callable] = None) -> Dict[str, Any]:
        """Generate content using local LLM"""
        raise NotImplementedError("Subclasses must implement local LLM generation")


# Specific Stage Implementations

class CampaignOutlineStage(XAIStageManager):
    """Stage 1: Generate campaign outline using XAI"""

    async def _generate_with_xai(self, prompt: str, context: str,
                                previous_results: Dict[str, Any],
                                progress_callback: Optional[Callable] = None) -> Dict[str, Any]:

        if progress_callback:
            await progress_callback("Generating campaign outline with XAI...")

        system_prompt = """You are a master D&D campaign architect. Generate a comprehensive campaign outline in JSON format.
Study the provided examples and create something of similar scope and complexity."""

        full_prompt = f"""{context}

## USER REQUEST
{prompt}

Create a detailed JSON campaign outline with this structure:
{{
    "title": "Campaign Title",
    "core_concept": "2-3 sentence description",
    "themes": ["theme1", "theme2", "theme3"],
    "estimated_sessions": 30,
    "central_mystery": "Main driving force",
    "acts": {{
        "act_1": {{"title": "", "sessions": 8, "summary": ""}},
        "act_2": {{"title": "", "sessions": 12, "summary": ""}},
        "act_3": {{"title": "", "sessions": 10, "summary": ""}}
    }},
    "key_npcs": [
        {{"name": "", "role": "", "importance": ""}},
    ],
    "key_locations": [
        {{"name": "", "type": "", "importance": ""}},
    ]
}}

Respond ONLY with valid JSON."""

        try:
            response = self.xai_client.chat.completions.create(
                model="grok-3-mini",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": full_prompt}
                ],
                max_tokens=2048,
                temperature=0.8
            )

            json_content = self.clean_json_response(response.choices[0].message.content)

            try:
                outline = json.loads(json_content)
            except json.JSONDecodeError as e:
                print(f"ERROR: JSON parsing failed in outline stage: {e}")
                print(f"Raw response: {response.choices[0].message.content[:500]}...")
                print(f"Cleaned JSON: {json_content[:500]}...")

                # Fallback: create a basic outline structure
                outline = {
                    "title": "Generated Dark Fantasy Campaign",
                    "core_concept": "A dark fantasy campaign about political intrigue",
                    "themes": ["political intrigue", "ancient evil", "guild warfare"],
                    "estimated_sessions": 30,
                    "central_mystery": "An ancient evil awakens beneath the streets",
                    "acts": {
                        "act_1": {"title": "Rising Tensions", "sessions": 8, "summary": "Introduction to guild politics"},
                        "act_2": {"title": "Ancient Stirrings", "sessions": 12, "summary": "Discovery of underground threat"},
                        "act_3": {"title": "Final Confrontation", "sessions": 10, "summary": "Climactic battle"}
                    },
                    "key_npcs": [{"name": "Guild Leader", "role": "Antagonist", "importance": "High"}],
                    "key_locations": [{"name": "Guild District", "type": "City", "importance": "High"}]
                }
                print("Using fallback outline structure to continue generation")

            self.logger.info(f"Generated campaign outline: {outline.get('title', 'Unknown')}")
            return {"outline": outline, "stage": "outline_complete"}

        except Exception as e:
            self.logger.error(f"XAI outline generation failed: {e}")
            raise


class PlotStructureStage(XAIStageManager):
    """Stage 2: Generate detailed plot structure using XAI"""

    async def _generate_with_xai(self, prompt: str, context: str,
                                previous_results: Dict[str, Any],
                                progress_callback: Optional[Callable] = None) -> Dict[str, Any]:

        if progress_callback:
            await progress_callback("Generating detailed plot structure with XAI...")

        outline = previous_results.get("outline", {})

        system_prompt = """You are expanding a campaign outline into detailed plot structure.
Create rich, detailed plot progression that matches professional campaign quality."""

        full_prompt = f"""{context}

## CAMPAIGN OUTLINE
{json.dumps(outline, indent=2)}

Create detailed plot structure with:
1. Detailed act summaries (2-3 paragraphs each)
2. Key scenes and turning points
3. NPC motivations and arcs
4. Player agency moments
5. Cliffhangers and plot hooks

Respond in JSON format with detailed "plot_structure" object."""

        try:
            response = self.xai_client.chat.completions.create(
                model="grok-3-mini",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": full_prompt}
                ],
                max_tokens=3000,
                temperature=0.8
            )

            json_content = self.clean_json_response(response.choices[0].message.content)

            try:
                plot_data = json.loads(json_content)
            except json.JSONDecodeError as e:
                print(f"ERROR: JSON parsing failed: {e}")
                print(f"Raw response: {response.choices[0].message.content[:500]}...")
                print(f"Cleaned JSON: {json_content[:500]}...")

                # Fallback: create a basic structure
                plot_data = {
                    "plot_structure": {
                        "act_summaries": "Plot structure generation failed due to JSON parsing error",
                        "key_scenes": [],
                        "npc_motivations": [],
                        "player_agency": [],
                        "cliffhangers": []
                    }
                }
                print("Using fallback plot structure to continue generation")

            self.logger.info("Generated detailed plot structure")
            return {"plot_structure": plot_data, "stage": "plot_complete"}

        except Exception as e:
            self.logger.error(f"XAI plot structure generation failed: {e}")
            raise


class DetailedContentStage(GeminiStageManager):
    """Stage 3: Generate detailed campaign content using Gemini massive context"""

    async def _generate_with_gemini(self, prompt: str, context: str,
                                  previous_results: Dict[str, Any],
                                  progress_callback: Optional[Callable] = None) -> Dict[str, Any]:

        if progress_callback:
            await progress_callback("Generating detailed content with Gemini (full campaign examples)...")

        outline = previous_results.get("outline", {})
        plot_structure = previous_results.get("plot_structure", {})

        generation_prompt = f"""
{context}

## CAMPAIGN TO EXPAND
Title: {outline.get('title', 'Unknown Campaign')}
Concept: {outline.get('core_concept', '')}

Plot Structure: {json.dumps(plot_structure, indent=2)}

## YOUR TASK
Generate a complete, detailed campaign document with MINIMUM 500 lines for AI DM reference.

REQUIRED SECTIONS (aim for 500+ total lines):
1. Campaign Overview (50+ lines)
2. Detailed NPC Roster (150+ lines) - 20+ NPCs with motivations, secrets, relationships
3. Location Gazetteer (150+ lines) - 10+ locations with atmosphere, NPCs, encounters
4. Session-by-Session Outline (100+ lines) - detailed progression framework
5. Political/Faction Dynamics (50+ lines) - who wants what, conflicts, alliances

CONTENT REQUIREMENTS:
- Rich, atmospheric descriptions for immersion
- Detailed NPC personalities with specific motivations and secrets
- Complex location descriptions with hidden elements
- Intricate plot details and subplots for long-term consistency
- Player agency moments and branching paths
- Professional D&D writing style

Generate comprehensive campaign content that gives an AI DM enough reference material to maintain narrative consistency across 30+ sessions.
"""

        try:
            response = self.gemini_client.generate_content(generation_prompt)
            detailed_content = response.text

            self.logger.info(f"Generated detailed content: {len(detailed_content)} characters")
            return {"detailed_content": detailed_content, "stage": "content_complete"}

        except Exception as e:
            self.logger.error(f"Gemini content generation failed: {e}")
            raise


class NPCLocationStage(LocalLLMStageManager):
    """Stage 4: Polish and enhance NPCs/locations using local LLM"""

    async def _generate_with_local_llm(self, prompt: str, previous_results: Dict[str, Any],
                                     progress_callback: Optional[Callable] = None) -> Dict[str, Any]:

        if progress_callback:
            await progress_callback("Polishing NPCs and locations with local LLM...")

        detailed_content = previous_results.get("detailed_content", "")

        polish_prompt = f"""Polish and enhance this campaign content:

{detailed_content[:50000]}  # Increased limit for local LLM

Focus on:
1. Grammar and consistency
2. Enhanced NPC personality details
3. Richer location descriptions
4. Improved formatting
5. Professional presentation

Return the polished content."""

        try:
            polished_content = await llm_manager.generate(polish_prompt, 5000)

            self.logger.info("Polished content with local LLM")
            return {"polished_content": polished_content, "stage": "polish_complete"}

        except Exception as e:
            self.logger.error(f"Local LLM polishing failed: {e}")
            raise


class LocalCampaignOutlineStage(LocalLLMStageManager):
    """Stage 1: Generate campaign outline using Local LLM"""

    async def _generate_with_local_llm(self, prompt: str, previous_results: Dict[str, Any],
                                     progress_callback: Optional[Callable] = None) -> Dict[str, Any]:

        if progress_callback:
            await progress_callback("Generating campaign outline with Local LLM...")

        # Get some context examples for reference
        context_loader = CampaignContextLoader()
        condensed_context = context_loader.get_condensed_examples(2)

        outline_prompt = f"""Create a D&D campaign outline based on this request: {prompt}

{condensed_context}

Generate a detailed campaign outline with these elements:

TITLE: A compelling campaign name
CORE CONCEPT: 2-3 sentence description
THEMES: 3-4 main themes (e.g., political intrigue, ancient evil, etc.)
ESTIMATED SESSIONS: 20-35 sessions
CENTRAL MYSTERY: Main driving plot force
ACTS: 3 acts with titles, session counts, and summaries
KEY NPCS: 4-6 important characters with names, roles, and importance
KEY LOCATIONS: 4-6 significant places with names, types, and importance

Write this as a detailed outline, not JSON. Use clear headings and descriptions."""

        try:
            outline_content = await llm_manager.generate(outline_prompt, 2500)

            # Parse the outline content to extract actual campaign details
            import re

            # Extract title from generated content
            title_match = re.search(r'(?:TITLE|Title|#.*?)[:]*\s*(.+)', outline_content, re.IGNORECASE)
            campaign_title = title_match.group(1).strip() if title_match else "Generated Campaign"

            # Clean title for filename use
            campaign_title = campaign_title.strip('*#: ')

            # Extract concept
            concept_match = re.search(r'(?:CONCEPT|CORE CONCEPT|Concept)[:]*\s*(.+?)(?:\n|THEMES|$)', outline_content, re.IGNORECASE | re.DOTALL)
            campaign_concept = concept_match.group(1).strip() if concept_match else "A D&D campaign based on the user's request"

            # Parse the outline content into a structured format
            outline = {
                "title": campaign_title,
                "core_concept": campaign_concept,
                "themes": ["adventure", "mystery", "conflict"],
                "estimated_sessions": 30,
                "central_mystery": "A mystery to be uncovered",
                "acts": {
                    "act_1": {"title": "Beginning", "sessions": 8, "summary": "Introduction"},
                    "act_2": {"title": "Development", "sessions": 12, "summary": "Rising action"},
                    "act_3": {"title": "Climax", "sessions": 10, "summary": "Resolution"}
                },
                "key_npcs": [
                    {"name": "Campaign NPC", "role": "Important Character", "importance": "High"}
                ],
                "key_locations": [
                    {"name": "Campaign Location", "type": "Important Place", "importance": "High"}
                ],
                "raw_outline": outline_content
            }

            print(f"Generated campaign outline with Local LLM")
            return {"outline": outline, "stage": "outline_complete"}

        except Exception as e:
            print(f"ERROR: Local LLM outline generation failed: {e}")
            raise


class LocalPlotStructureStage(LocalLLMStageManager):
    """Stage 2: Generate detailed plot structure using Local LLM"""

    async def _generate_with_local_llm(self, prompt: str, previous_results: Dict[str, Any],
                                     progress_callback: Optional[Callable] = None) -> Dict[str, Any]:

        if progress_callback:
            await progress_callback("Generating detailed plot structure with Local LLM...")

        outline = previous_results.get("outline", {})

        plot_prompt = f"""Expand this campaign outline into a detailed plot structure:

CAMPAIGN: {outline.get('title', 'Campaign')}
CONCEPT: {outline.get('core_concept', '')}
THEMES: {', '.join(outline.get('themes', []))}

Create detailed plot progression with:
1. Detailed act summaries (2-3 paragraphs each)
2. Key scenes and turning points for each act
3. NPC motivations and character arcs
4. Player agency moments and decision points
5. Cliffhangers and plot hooks between acts
6. How the central mystery unfolds

Write this as detailed narrative descriptions, focusing on story flow and player engagement."""

        try:
            plot_content = await llm_manager.generate(plot_prompt, 3000)

            plot_structure = {
                "act_summaries": plot_content,
                "key_scenes": [],
                "npc_motivations": [],
                "player_agency": [],
                "cliffhangers": []
            }

            print("Generated detailed plot structure with Local LLM")
            return {"plot_structure": plot_structure, "stage": "plot_complete"}

        except Exception as e:
            print(f"ERROR: Local LLM plot structure generation failed: {e}")
            raise