# src/detailed_campaign_generator.py
import logging
import asyncio
import json
import time
from typing import Dict, List, Any, Tuple
from .llm_manager import llm_manager
from .config import settings
import openai

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class DetailedCampaignGenerator:
    def __init__(self):
        # XAI integration disabled - focusing on local LLM only
        # self.xai_client = None
        # if settings.XAI_API_KEY:
        #     self.xai_client = openai.OpenAI(
        #         api_key=settings.XAI_API_KEY,
        #         base_url="https://api.x.ai/v1"
        #     )
    
    async def generate_campaign_outline(self, user_prompt: str, campaign_structures: str, ctx=None) -> Dict[str, Any]:
        """Stage 1: Generate detailed campaign outline and section prompts"""
        
        outline_prompt = f"""You are a master campaign architect for D&D 5e. Your job is to create a comprehensive outline for an epic campaign.

USER REQUEST: {user_prompt}

CAMPAIGN INSPIRATION:
{campaign_structures[:3000]}

Create a detailed campaign outline that includes:
1. Core campaign concept and themes
2. Detailed plot structure (3 acts with specific scenes)
3. List of 5-7 key NPCs with their roles
4. List of 5-7 key locations
5. Central mystery/threat
6. Estimated session count (aim for 25-35 sessions)

Respond with JSON containing:
{{
  "title": "Campaign title",
  "core_concept": "2-3 sentence concept",
  "themes": ["theme1", "theme2", "theme3"],
  "estimated_sessions": 30,
  "act_1": {{
    "title": "Act 1 title",
    "sessions": 8,
    "key_scenes": ["scene1", "scene2", "scene3"]
  }},
  "act_2": {{
    "title": "Act 2 title", 
    "sessions": 12,
    "key_scenes": ["scene1", "scene2", "scene3", "scene4"]
  }},
  "act_3": {{
    "title": "Act 3 title",
    "sessions": 10,
    "key_scenes": ["scene1", "scene2", "scene3"]
  }},
  "npcs": [
    {{"name": "NPC Name", "role": "brief role description"}},
  ],
  "locations": [
    {{"name": "Location Name", "importance": "brief importance"}},
  ],
  "central_mystery": "What drives the entire campaign"
}}"""

        if ctx:
            await ctx.send("**[TARGET] Stage 1/5:** Generating campaign outline and structure...")
        
        try:
            # XAI integration disabled - using local LLM only
            # if self.xai_client:
            #     logging.info("Using XAI for campaign outline generation")
            #     response = self.xai_client.chat.completions.create(
            #         model="grok-beta",
            #         messages=[
            #             {"role": "system", "content": "You are a master D&D campaign designer. Respond only with valid JSON."},
            #             {"role": "user", "content": outline_prompt}
            #         ],
            #         max_tokens=2048,
            #         temperature=0.8
            #     )
            #     outline_response = response.choices[0].message.content
            # else:
            logging.info("Using local AI for campaign outline generation")
            outline_response = await llm_manager.generate( outline_prompt, 2048)
            
            # Clean and parse JSON
            clean_json = self._clean_json_response(outline_response)
            outline_data = json.loads(clean_json)
            
            logging.info(f"Generated outline for campaign: {outline_data.get('title', 'Untitled')}")
            return outline_data
            
        except Exception as e:
            logging.error(f"Failed to generate campaign outline: {e}")
            raise

    async def generate_plot_act(self, outline: Dict[str, Any], act_number: int, ctx=None) -> str:
        """Stage 2a: Generate detailed plot act"""
        
        act_key = f"act_{act_number}"
        act_info = outline.get(act_key, {})
        
        plot_prompt = f"""You are crafting Act {act_number} of the D&D campaign "{outline.get('title', 'Unknown Campaign')}".

CAMPAIGN CONCEPT: {outline.get('core_concept', 'Unknown')}
CENTRAL MYSTERY: {outline.get('central_mystery', 'Unknown')}
THEMES: {', '.join(outline.get('themes', []))}

ACT {act_number} OVERVIEW:
- Title: {act_info.get('title', f'Act {act_number}')}
- Estimated Sessions: {act_info.get('sessions', 8)}
- Key Scenes: {', '.join(act_info.get('key_scenes', []))}

Write a detailed 5-6 paragraph description of Act {act_number}. Include:
- Specific opening scenes and how players get involved
- Major challenges and obstacles players will face  
- Key NPCs they'll interact with and their motivations
- Important locations they'll visit
- Plot revelations and turning points
- How this act connects to the overall campaign arc
- Specific encounters, investigations, or diplomatic scenarios
- Moral dilemmas and character development opportunities

Make this feel like a complete act of an epic story with rich detail."""

        if ctx:
            await ctx.send(f"**[BOOK] Stage 2{chr(ord('a') + act_number - 1)}/5:** Generating detailed Act {act_number} narrative...")
        
        try:
            # XAI integration disabled - using local LLM only
            # if self.xai_client:
            #     response = self.xai_client.chat.completions.create(
            #         model="grok-beta",
            #         messages=[
            #             {"role": "system", "content": "You are a master storyteller crafting detailed D&D campaign acts."},
            #             {"role": "user", "content": plot_prompt}
            #         ],
            #         max_tokens=1500,
            #         temperature=0.8
            #     )
            #     return response.choices[0].message.content.strip()
            # else:
            return await llm_manager.generate( plot_prompt, 1500)
                
        except Exception as e:
            logging.error(f"Failed to generate Act {act_number}: {e}")
            return f"Error generating Act {act_number}. Using fallback content."

    async def generate_npc_details(self, outline: Dict[str, Any], npc_info: Dict[str, str], ctx=None) -> Dict[str, str]:
        """Stage 3: Generate detailed NPC information"""
        
        npc_prompt = f"""You are creating a detailed NPC for the D&D campaign "{outline.get('title', 'Unknown Campaign')}".

CAMPAIGN CONTEXT:
- Concept: {outline.get('core_concept', 'Unknown')}
- Central Mystery: {outline.get('central_mystery', 'Unknown')}
- Themes: {', '.join(outline.get('themes', []))}

NPC BASIC INFO:
- Name: {npc_info.get('name', 'Unknown')}
- Role: {npc_info.get('role', 'Unknown')}

Create a rich, detailed NPC with 4-5 paragraphs covering:
1. Physical appearance and distinctive features
2. Personality, mannerisms, and speaking style  
3. Background, history, and personal motivations
4. Secrets, hidden agendas, and internal conflicts
5. Relationships with other NPCs and role in the campaign
6. How they interact with players and potential character arcs
7. Specific plot hooks and adventure opportunities they provide

Make this NPC feel like a real person with depth, flaws, and compelling story potential."""

        if ctx and ctx.channel:
            await ctx.send(f"**[NPC] Crafting detailed NPC: **{npc_info.get('name', 'Unknown')}**")
        
        try:
            # XAI integration disabled - using local LLM only
            # if self.xai_client:
            #     response = self.xai_client.chat.completions.create(
            #         model="grok-beta",
            #         messages=[
            #             {"role": "system", "content": "You are creating detailed, memorable NPCs for D&D campaigns."},
            #             {"role": "user", "content": npc_prompt}
            #         ],
            #         max_tokens=1200,
            #         temperature=0.8
            #     )
            #     description = response.choices[0].message.content.strip()
            # else:
            description = await llm_manager.generate( npc_prompt, 1200)
            
            return {
                "name": npc_info.get('name', 'Unknown'),
                "description": description
            }
            
        except Exception as e:
            logging.error(f"Failed to generate NPC {npc_info.get('name', 'Unknown')}: {e}")
            return {
                "name": npc_info.get('name', 'Unknown'),
                "description": f"Error generating details for {npc_info.get('name', 'Unknown')}. Using fallback content."
            }

    async def generate_location_details(self, outline: Dict[str, Any], location_info: Dict[str, str], ctx=None) -> Dict[str, str]:
        """Stage 4: Generate detailed location information"""
        
        location_prompt = f"""You are creating a detailed location for the D&D campaign "{outline.get('title', 'Unknown Campaign')}".

CAMPAIGN CONTEXT:
- Concept: {outline.get('core_concept', 'Unknown')}
- Central Mystery: {outline.get('central_mystery', 'Unknown')}
- Themes: {', '.join(outline.get('themes', []))}

LOCATION BASIC INFO:
- Name: {location_info.get('name', 'Unknown')}
- Importance: {location_info.get('importance', 'Unknown')}

Create a vivid, detailed location with 4-5 paragraphs covering:
1. Physical appearance, architecture, and distinctive features
2. Atmosphere, sounds, smells, and overall mood
3. Key inhabitants, their culture, and daily life
4. Political situation, leadership, and social dynamics
5. Economic basis, defenses, and strategic importance
6. Secrets, hidden areas, and mysterious elements
7. Plot relevance and potential adventures within this location
8. How it changes or evolves throughout the campaign

Make this location feel alive and integral to the campaign story."""

        if ctx and ctx.channel:
            await ctx.send(f"**[LOCATION] Designing detailed location: **{location_info.get('name', 'Unknown')}**")
        
        try:
            # XAI integration disabled - using local LLM only
            # if self.xai_client:
            #     response = self.xai_client.chat.completions.create(
            #         model="grok-beta",
            #         messages=[
            #             {"role": "system", "content": "You are creating vivid, immersive locations for D&D campaigns."},
            #             {"role": "user", "content": location_prompt}
            #         ],
            #         max_tokens=1200,
            #         temperature=0.8
            #     )
            #     description = response.choices[0].message.content.strip()
            # else:
            description = await llm_manager.generate( location_prompt, 1200)
            
            return {
                "name": location_info.get('name', 'Unknown'),
                "description": description
            }
            
        except Exception as e:
            logging.error(f"Failed to generate location {location_info.get('name', 'Unknown')}: {e}")
            return {
                "name": location_info.get('name', 'Unknown'),
                "description": f"Error generating details for {location_info.get('name', 'Unknown')}. Using fallback content."
            }

    async def generate_additional_elements(self, outline: Dict[str, Any], ctx=None) -> Dict[str, Any]:
        """Stage 5: Generate additional campaign elements"""
        
        elements_prompt = f"""You are adding final touches to the D&D campaign "{outline.get('title', 'Unknown Campaign')}".

CAMPAIGN OVERVIEW:
- Title: {outline.get('title', 'Unknown Campaign')}
- Concept: {outline.get('core_concept', 'Unknown')}
- Central Mystery: {outline.get('central_mystery', 'Unknown')}
- Themes: {', '.join(outline.get('themes', []))}
- Estimated Sessions: {outline.get('estimated_sessions', 30)}

Create additional campaign elements as JSON:

{{
  "recurring_themes": ["List 4-5 major themes explored throughout"],
  "player_agency_moments": [
    "Specific decision point 1 that significantly impacts story",
    "Specific decision point 2 that changes campaign direction", 
    "Specific decision point 3 with moral implications",
    "Specific decision point 4 affecting NPC relationships",
    "Specific decision point 5 determining campaign ending"
  ],
  "potential_betrayals": [
    "Specific betrayal scenario 1 with trusted ally",
    "Specific betrayal scenario 2 involving politics",
    "Specific betrayal scenario 3 with personal stakes"
  ],
  "campaign_tone": "2-3 sentences describing overall mood and atmosphere",
  "side_quests": [
    "Side quest 1: brief description",
    "Side quest 2: brief description", 
    "Side quest 3: brief description"
  ],
  "recurring_villains": [
    "Secondary antagonist 1 and their role",
    "Secondary antagonist 2 and their motivation"
  ]
}}"""

        if ctx:
            await ctx.send("**[THEATER] Stage 5/5:** Adding campaign themes, betrayals, and side quests...")
        
        try:
            # XAI integration disabled - using local LLM only
            # if self.xai_client:
            #     response = self.xai_client.chat.completions.create(
            #         model="grok-beta",
            #         messages=[
            #             {"role": "system", "content": "You are finalizing a D&D campaign with additional story elements. Respond only with valid JSON."},
            #             {"role": "user", "content": elements_prompt}
            #         ],
            #         max_tokens=1000,
            #         temperature=0.7
            #     )
            #     elements_response = response.choices[0].message.content
            # else:
            elements_response = await llm_manager.generate( elements_prompt, 1000)
            
            # Clean and parse JSON
            clean_json = self._clean_json_response(elements_response)
            return json.loads(clean_json)
            
        except Exception as e:
            logging.error(f"Failed to generate additional elements: {e}")
            return {
                "recurring_themes": ["Power and corruption", "Loyalty vs. ambition", "Cost of heroism"],
                "player_agency_moments": ["Choose faction alliance", "Decide villain's fate", "Shape kingdom's future"],
                "potential_betrayals": ["Trusted advisor reveals true agenda", "Allied kingdom switches sides"],
                "campaign_tone": "Epic fantasy with political intrigue and personal drama",
                "side_quests": ["Local noble needs help", "Ancient ruins discovered", "Merchant caravan protection"],
                "recurring_villains": ["Ambitious general", "Corrupt merchant lord"]
            }

    def _clean_json_response(self, response: str) -> str:
        """Clean JSON response from AI models"""
        clean_response = response.strip()
        
        # Remove markdown code blocks
        clean_response = clean_response.replace('```json', '').replace('```', '').strip()
        
        # Find JSON boundaries
        json_start = clean_response.find('{')
        json_end = clean_response.rfind('}') + 1
        
        if json_start != -1 and json_end != -1 and json_start < json_end:
            clean_response = clean_response[json_start:json_end]
        
        return clean_response

    async def generate_complete_campaign(self, user_prompt: str, campaign_structures: str, ctx=None) -> Dict[str, Any]:
        """Main method: Generate complete detailed campaign using multi-stage approach"""
        
        start_time = time.time()
        logging.info(f"Starting detailed campaign generation for prompt: {user_prompt}")
        
        try:
            # Stage 1: Generate outline
            outline = await self.generate_campaign_outline(user_prompt, campaign_structures, ctx)
            
            if ctx:
                estimated_time = len(outline.get('npcs', [])) * 2 + len(outline.get('locations', [])) * 2 + 10
                await ctx.send(f"**[CHART] Campaign Outline Complete!**\n"
                              f"• **Title:** {outline.get('title', 'Unknown')}\n"
                              f"• **NPCs to detail:** {len(outline.get('npcs', []))}\n"
                              f"• **Locations to detail:** {len(outline.get('locations', []))}\n"
                              f"• **Estimated time:** {estimated_time} minutes\n\n"
                              f"**[HOURGLASS] This will be worth the wait for an epic campaign!**")
            
            # Stage 2: Generate detailed plot acts
            act_1_details = await self.generate_plot_act(outline, 1, ctx)
            await asyncio.sleep(1)  # Rate limiting
            act_2_details = await self.generate_plot_act(outline, 2, ctx)  
            await asyncio.sleep(1)
            act_3_details = await self.generate_plot_act(outline, 3, ctx)
            await asyncio.sleep(1)
            
            # Stage 3: Generate detailed NPCs
            detailed_npcs = []
            npc_list = outline.get('npcs', [])
            for i, npc_info in enumerate(npc_list[:6]):  # Limit to 6 NPCs for reasonable time
                npc_details = await self.generate_npc_details(outline, npc_info, ctx)
                detailed_npcs.append(npc_details)
                await asyncio.sleep(1)  # Rate limiting
                
                if ctx and i % 2 == 1:  # Progress update every 2 NPCs
                    await ctx.send(f"**[CHECKMARK] Created {i+1}/{len(npc_list[:6])} detailed NPCs...**")
            
            # Stage 4: Generate detailed locations
            detailed_locations = []
            location_list = outline.get('locations', [])
            for i, location_info in enumerate(location_list[:6]):  # Limit to 6 locations
                location_details = await self.generate_location_details(outline, location_info, ctx)
                detailed_locations.append(location_details)
                await asyncio.sleep(1)  # Rate limiting
                
                if ctx and i % 2 == 1:  # Progress update every 2 locations
                    await ctx.send(f"**[CHECKMARK] Designed {i+1}/{len(location_list[:6])} detailed locations...**")
            
            # Stage 5: Generate additional elements
            additional_elements = await self.generate_additional_elements(outline, ctx)
            
            # Compile final campaign
            final_campaign = {
                "title": outline.get('title', 'Untitled Campaign'),
                "description": f"{outline.get('core_concept', 'An epic D&D campaign.')} "
                             f"This {outline.get('estimated_sessions', 30)}-session campaign explores "
                             f"themes of {', '.join(outline.get('themes', ['adventure', 'heroism']))}. "
                             f"The central mystery revolves around {outline.get('central_mystery', 'ancient secrets')}. "
                             f"Players will face moral dilemmas, political intrigue, and epic confrontations "
                             f"as they shape the fate of the world through their choices.",
                "plot": {
                    "act_1_hook": act_1_details,
                    "act_2_rising_action": act_2_details,
                    "act_3_climax": act_3_details
                },
                "key_npcs": detailed_npcs,
                "key_locations": detailed_locations,
                "additional_elements": additional_elements,
                "campaign_metadata": {
                    "estimated_sessions": outline.get('estimated_sessions', 30),
                    "generation_method": "multi_stage_detailed",
                    "generation_time_minutes": round((time.time() - start_time) / 60, 1),
                    "api_used": "local"
                }
            }
            
            total_time = round((time.time() - start_time) / 60, 1)
            logging.info(f"Completed detailed campaign generation in {total_time} minutes")
            
            return final_campaign
            
        except Exception as e:
            logging.error(f"Failed to generate detailed campaign: {e}")
            raise