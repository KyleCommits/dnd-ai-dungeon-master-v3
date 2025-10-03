# src/bot.py
import discord
from discord.ext import commands
import logging
from .config import settings
from .llm_manager import llm_manager
from .database import get_db_session, get_all_campaign_structures
from .models import Campaign  # Character moved to character_models.py (legacy Discord bot deprecated)
from .rag_manager import rag_manager # Import the rag_manager
from .campaign_manager import create_and_index_campaign, delete_campaign
from .detailed_campaign_generator import DetailedCampaignGenerator
from .campaign_state_manager import campaign_state_manager
from .dynamic_dm import dynamic_dm
import asyncio
import random
import re
import json
import os
import time

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Define intents
intents = discord.Intents.default()
intents.messages = True
intents.message_content = True
intents.guilds = True

class DnDBot(commands.Bot):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.prompt_template = ""
        self.active_campaign = None # Will be set by load_campaign_dynamic

    async def on_ready(self):
        logging.info(f'Logged on as {self.user}!')
        self.load_prompt_template()
        logging.info("Prompt template loaded.")
        
        # Terminal startup message instead of Discord DM
        print("\n" + "="*60)
        print("D&D DISCORD BOT IS READY!")
        print("="*60)
        print(f"[OK] Bot logged in as: {self.user}")
        print(f"[OK] Connected to Discord")
        print(f"[OK] Local AI model loaded")
        print(f"[OK] RAG system initialized") 
        print(f"[OK] Campaign generation ready")
        # XAI integration disabled - focusing on local LLM only
        # if settings.XAI_API_KEY:
        #     print("[OK] XAI API available for detailed campaigns")
        print("="*60)
        print("Ready for epic D&D adventures!")
        print("Tip: Use !new_campaign_detailed for ultra-rich campaigns")
        print("="*60 + "\n")

    def load_prompt_template(self):
        self.prompt_template = """
        You are a master Dungeon Master for a Dungeons & Dragons 5e campaign.
        Your role is to create a rich, narrative-driven experience.
        You will guide the players through a story, describing the world, controlling NPCs, and adjudicating the rules.
        You will be given context from the campaign book and the official rules. Use this context to inform your response.
        Keep your responses concise and engaging.
        """

    async def on_message(self, message):
        # Ignore messages from the bot itself
        if message.author == self.user:
            return

        # Process commands first
        await self.process_commands(message)

        # If the message is not a command, and in the correct channel, treat it as a story message
        if not message.content.startswith(self.command_prefix) and message.channel.id == settings.BOT_CHANNEL_ID:
            if not message.content.strip():
                return
                
            logging.info(f'Message from {message.author} in {message.channel}: {message.content}')

            try:
                async with message.channel.typing():
                    # Check if dynamic campaign is loaded
                    if campaign_state_manager.current_state:
                        # Use dynamic DM system for intelligent responses
                        logging.info(f"Using dynamic DM system for: {message.content}")
                        response = await dynamic_dm.generate_response(message.content, message.author.name)
                        
                        # Create rich embed response
                        state = campaign_state_manager.current_state
                        embed = discord.Embed(
                            title=f"DM - {state.campaign_name}",
                            description=response,
                            color=discord.Color.purple()
                        )
                        embed.add_field(
                            name="Location", 
                            value=f"{state.location} (Act {state.current_act})",
                            inline=True
                        )
                        embed.set_footer(text=f"Session {state.session_count} | Dynamic AI DM")
                        await message.channel.send(embed=embed)
                        
                    else:
                        # Fall back to static RAG system if no dynamic campaign loaded
                        logging.info("No dynamic campaign loaded, using static RAG system...")
                        rules_context = await rag_manager.query_rules(message.content)
                        campaign_context = await rag_manager.query_campaign(self.active_campaign, message.content) if self.active_campaign else ""
                        
                        full_prompt = (
                            f"{self.prompt_template}\n\n"
                            f"--- Rules Context ---\n{rules_context}\n\n"
                            f"--- Campaign Context ---\n{campaign_context}\n\n"
                            f"Player: {message.content}\n\n"
                            f"DM:"
                        )
                        
                        response = await llm_manager.generate(full_prompt)
                        
                        if response:
                            await message.channel.send(response)
                        else:
                            logging.warning("LLM generated an empty response.")

            except Exception as e:
                logging.error(f"Error generating LLM response: {e}")
                await message.channel.send("Sorry, I encountered an error and couldn't process your request.")

# --- Bot Commands ---
bot = DnDBot(command_prefix='!', intents=intents)

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.NotOwner):
        logging.warning(f"Non-owner user {ctx.author} (ID: {ctx.author.id}) tried to use the owner-only command '{ctx.command}'.")
        await ctx.send("Sorry, that command can only be used by the bot owner.")
    elif isinstance(error, commands.CommandNotFound):
        await ctx.send("Unknown command. Please check your spelling.")
    else:
        logging.error(f"An unexpected command error occurred: {error}", exc_info=True)
        await ctx.send("An error occurred while processing the command. Please check the logs.")

@bot.command(name='hello')
async def hello(ctx):
    """A simple test command to see if the bot is responding."""
    await ctx.send('Hello! I am the D&D bot. I am ready to play.')

@bot.command(name='create_character')
async def create_character(ctx):
    """Starts the interactive character creation process."""
    author = ctx.author
    await author.send("Hello! Let's create your D&D character. What is your character's name?")

    def check(m):
        return m.author == author and isinstance(m.channel, discord.DMChannel)

    try:
        name_message = await bot.wait_for('message', check=check, timeout=300.0)
        character_name = name_message.content

        await author.send(f"Great! Your character's name is {character_name}. Now, what is your character's race?")
        race_message = await bot.wait_for('message', check=check, timeout=300.0)
        character_race = race_message.content

        await author.send(f"A {character_race} named {character_name}. Excellent! Finally, what is your character's class?")
        class_message = await bot.wait_for('message', check=check, timeout=300.0)
        character_class = class_message.content

        # Save to database - DISABLED: Discord bot deprecated, use web interface
        # async for session in get_db_session():
        #     new_character = Character(
        #         player_id=author.id,
        #         name=character_name,
        #         race=character_race,
        #         class_=character_class,
        #     )
        #     session.add(new_character)
        #     await session.commit()

        await author.send(f"Your character, {character_name} the {character_race} {character_class}, has been created!")

    except asyncio.TimeoutError:
        await author.send("Character creation timed out. Please start over by using the `!create_character` command in the server.")

@bot.command(name='load_campaign')
@commands.is_owner()
async def load_campaign(ctx, *, campaign_name: str):
    """Loads a new campaign. (Owner only)"""
    normalized_name = campaign_name.lower().replace(" ", "_")
    index_name = f"campaign_{normalized_name}"
    
    logging.info(f"Attempting to load campaign: {campaign_name} (index: {index_name})")
    
    # Check if the query engine for this campaign can be initialized
    query_engine = await rag_manager.get_query_engine(index_name)
    
    if query_engine:
        bot.active_campaign = normalized_name
        await ctx.send(f"Campaign '{campaign_name}' loaded successfully!")
        logging.info(f"Active campaign changed to: {normalized_name}")
    else:
        await ctx.send(f"Could not find or initialize the campaign '{campaign_name}'. Please make sure the source file exists and the indexes have been generated.")
        logging.warning(f"Failed to load campaign: {normalized_name}")

@bot.command(name='my_sheet')
async def my_sheet(ctx):
    """Displays the character sheet of the user."""
    author = ctx.author
    async for session in get_db_session():
        character = await session.get(Character, author.id)
        if character:
            embed = discord.Embed(title=f"Character Sheet: {character.name}", color=discord.Color.blue())
            embed.add_field(name="Race", value=character.race, inline=True)
            embed.add_field(name="Class", value=character.class_, inline=True)
            # Add more fields as the model evolves
            await ctx.send(embed=embed)
        else:
            await ctx.send("You don't have a character yet! Use `!create_character` to make one.")

@bot.command(name='rule')
async def rule(ctx, *, query: str):
    """Asks a question about the D&D 5e rules."""
    logging.info(f"Received rule query: '{query}'")
    
    async with ctx.typing():
        response = await rag_manager.query_rules(query)
        
        summary_prompt = (
            f"You are a helpful D&D assistant. A player asked the following question: '{query}'\n\n"
            f"The official rules state:\n{response}\n\n"
            f"Please provide a clear and concise answer to the player's question based on these rules."
        )
        
        summarized_response = await llm_manager.generate(summary_prompt, 150)

    if summarized_response:
        await ctx.send(summarized_response)
    else:
        await ctx.send("Sorry, I couldn't find an answer to that question.")

@bot.command(name='roll')
async def roll(ctx, *, expression: str):

    """Rolls dice based on a given expression (e.g., '2d6+3', 'd20 adv')."""
    expression = expression.lower().strip()
    parts = expression.split()
    dice_expr = parts[0]
    
    advantage = 'adv' in parts or 'advantage' in parts
    disadvantage = 'dis' in parts or 'disadvantage' in parts

    if advantage and disadvantage:
        await ctx.send("You can't have both advantage and disadvantage on the same roll!")
        return

    match = re.match(r'(\d*)d(\d+)(?:([+-])(\d+))?', dice_expr)
    
    if not match:
        await ctx.send("Invalid dice expression! Please use a format like '2d6+3', 'd20', or '1d8-1'.")
        return

    num_dice = int(match.group(1)) if match.group(1) else 1
    num_sides = int(match.group(2))
    operator = match.group(3)
    modifier = int(match.group(4)) if match.group(4) else 0

    if num_dice > 100:
        await ctx.send("I can't roll more than 100 dice at a time!")
        return
    if num_sides > 1000:
        await ctx.send("I can't roll a die with more than 1000 sides!")
        return

    if (advantage or disadvantage) and (num_dice != 1 or num_sides != 20):
        await ctx.send("Advantage and disadvantage only apply to a single d20 roll.")
        return

    if advantage or disadvantage:
        roll1 = random.randint(1, 20)
        roll2 = random.randint(1, 20)
        rolls = [roll1, roll2]
        
        if advantage:
            result = max(roll1, roll2)
            title = f"Dice Roll: {expression} (Advantage)"
        else: # disadvantage
            result = min(roll1, roll2)
            title = f"Dice Roll: {expression} (Disadvantage)"
        
        total = result
    else:
        rolls = [random.randint(1, num_sides) for _ in range(num_dice)]
        total = sum(rolls)
        title = f"Dice Roll: {expression}"

    if operator == '+':
        total += modifier
    elif operator == '-':
        total -= modifier

    roll_str = ", ".join(str(r) for r in rolls)
    result_str = f"**Total:** {total}"
    
    embed = discord.Embed(title=title, color=discord.Color.green())
    embed.add_field(name="Rolls", value=f"[{roll_str}]", inline=False)
    embed.add_field(name="Result", value=result_str, inline=False)
    
    await ctx.send(embed=embed)

def remove_trailing_commas(json_string):
    """Removes trailing commas from a JSON string."""
    # This regex finds a comma followed by whitespace and then a closing brace or bracket
    # and removes the comma and whitespace.
    return re.sub(r',\s*([\}\]])', r'\1', json_string)

def validate_campaign_data(campaign_data):
    """Validates that campaign data has all required fields with sufficient detail."""
    required_fields = ['title', 'description', 'plot', 'key_npcs', 'key_locations']
    missing_fields = []
    
    # Check required top-level fields
    for field in required_fields:
        if field not in campaign_data or not campaign_data[field]:
            missing_fields.append(field)
    
    if missing_fields:
        return False, f"Missing required fields: {', '.join(missing_fields)}"
    
    # Validate plot structure
    plot = campaign_data.get('plot', {})
    required_plot_keys = ['act_1_hook', 'act_2_rising_action', 'act_3_climax']
    for plot_key in required_plot_keys:
        if plot_key not in plot or not plot[plot_key] or len(plot[plot_key].strip()) < 50:
            return False, f"Plot section '{plot_key}' is missing or too short (less than 50 characters)"
    
    # Validate NPCs
    npcs = campaign_data.get('key_npcs', [])
    if len(npcs) < 3:
        return False, f"Need at least 3 key NPCs, found {len(npcs)}"
    
    for i, npc in enumerate(npcs):
        if not npc.get('name') or not npc.get('description'):
            return False, f"NPC {i+1} is missing name or description"
        if len(npc.get('description', '').strip()) < 100:
            return False, f"NPC '{npc.get('name', 'unnamed')}' description is too short (less than 100 characters)"
    
    # Validate locations
    locations = campaign_data.get('key_locations', [])
    if len(locations) < 3:
        return False, f"Need at least 3 key locations, found {len(locations)}"
    
    for i, location in enumerate(locations):
        if not location.get('name') or not location.get('description'):
            return False, f"Location {i+1} is missing name or description"
        if len(location.get('description', '').strip()) < 100:
            return False, f"Location '{location.get('name', 'unnamed')}' description is too short (less than 100 characters)"
    
    # Check overall content quality
    description_length = len(campaign_data.get('description', '').strip())
    if description_length < 200:
        return False, f"Campaign description is too short ({description_length} characters, need at least 200)"
    
    return True, "Campaign data validation passed"

@bot.command(name='new_campaign')
@commands.is_owner()
async def new_campaign(ctx, *, prompt: str):
    """Generates, saves, and indexes a new campaign from a prompt. (Owner only)"""
    # Input validation
    if not prompt or len(prompt.strip()) < 10:
        await ctx.send("ERROR: Campaign prompt is too short. Please provide at least 10 characters describing your desired campaign.")
        return
    
    if len(prompt) > 500:
        await ctx.send("ERROR: Campaign prompt is too long (max 500 characters). Please shorten your description.")
        return
    
    logging.info(f"Received new campaign prompt: '{prompt}'")
    await ctx.send(f"Received prompt! Starting to generate a new campaign based on: '{prompt}'\n\nThis is a multi-step process and might take 2-3 minutes...")

    async def generate_campaign_thread():
        try:
            # 1. Get campaign structures from the database
            await ctx.send("Step 1/4: Loading campaign inspiration from database...")
            structures = await get_all_campaign_structures()
            if not structures:
                await ctx.send("ERROR: No campaign structures found in the database.\n\nFIX: Run `!analyze_structures` first to populate the database with campaign patterns.")
                return

            if len(structures) < 3:
                await ctx.send(f"WARNING: Only {len(structures)} campaign structures found. This may result in less detailed campaigns.\n\nTIP: Add more campaign files to `dnd_src_material/campaigns/` and run `!analyze_structures`.")

            structures_text = "\n\n".join([f"Campaign: {s.campaign_name}\n{json.dumps(s.structure_data, indent=2)}" for s in structures])

            # 2. Load the prompt template
            await ctx.send("Step 2/4: Loading campaign generation template...")
            template_path = "prompts/campaign_generation_prompt.txt"
            if not os.path.exists(template_path):
                await ctx.send(f"ERROR: Campaign generation template not found at '{template_path}'")
                return
            
            try:
                with open(template_path, "r", encoding="utf-8") as f:
                    template = f.read()
                if not template.strip():
                    await ctx.send("ERROR: Campaign generation template is empty")
                    return
            except Exception as e:
                await ctx.send(f"ERROR: Failed to read campaign template: {e}")
                return

            # 3. Construct the full prompt
            full_prompt = template.format(user_prompt=prompt, campaign_structures=structures_text)
            
            # Check prompt size
            if len(full_prompt) > 15000:
                await ctx.send("WARNING: Generated prompt is very large. This may impact AI performance.")

            # 4. Generate the campaign from the LLM
            await ctx.send("Step 3/4: Generating detailed campaign narrative from AI...")
            logging.info("Generating new campaign content from LLM...")
            
            generated_campaign_str = await llm_manager.generate(full_prompt, 4096)
            
            # Validate LLM response
            if not generated_campaign_str or len(generated_campaign_str.strip()) < 100:
                await ctx.send("ERROR: AI generated insufficient content. This may be due to:\n• Local model issues\n• Insufficient GPU memory\n• Prompt too complex\n\nTIP: Try with a shorter, simpler prompt.")
                return

            # 5. Parse and validate the JSON output
            await ctx.send("Step 4/4: Parsing and validating campaign data...")
            try:
                clean_json_str = generated_campaign_str.strip()
                
                # Remove markdown code blocks
                clean_json_str = clean_json_str.replace('```json', '').replace('```', '').strip()
                
                # Remove trailing commas
                clean_json_str = remove_trailing_commas(clean_json_str)
                
                # Try to find JSON if wrapped in other text
                json_start = clean_json_str.find('{')
                json_end = clean_json_str.rfind('}') + 1
                if json_start != -1 and json_end != -1 and json_start < json_end:
                    clean_json_str = clean_json_str[json_start:json_end]
                
                campaign_data = json.loads(clean_json_str)
                
            except json.JSONDecodeError as e:
                logging.error(f"Failed to decode JSON for new campaign: {e}")
                logging.error(f"Received string: {generated_campaign_str[:1000]}...")
                await ctx.send("ERROR: AI response was not in valid JSON format.\n\nDEBUG INFO:\n• This usually means the local AI model needs more resources\n• Try restarting the bot or using a simpler prompt\n\nCheck logs for detailed error information.")
                return

            # 6. Validate campaign content quality
            is_valid, validation_message = validate_campaign_data(campaign_data)
            if not is_valid:
                logging.error(f"Campaign validation failed: {validation_message}")
                await ctx.send(f"ERROR: Generated campaign lacks sufficient detail.\n\n**Issue:** {validation_message}\n\nSOLUTIONS:\n• Try a more specific prompt\n• Ensure your local AI model has enough resources\n• Run `!analyze_structures` to improve inspiration data")
                return

            title = campaign_data.get('title', 'Untitled Campaign')

            # 7. Save and index the campaign
            await ctx.send(f"Saving '{title}' and creating knowledge index...")
            try:
                sanitized_title = await create_and_index_campaign(campaign_data)
                logging.info(f"Successfully created and indexed new campaign '{sanitized_title}'.")
            except Exception as e:
                logging.error(f"Failed to save/index campaign: {e}")
                await ctx.send(f"ERROR: Failed to save campaign '{title}'.\n\n**Error:** {str(e)}\n\nCheck file permissions and disk space.")
                return

            # 8. Create detailed success summary
            embed = discord.Embed(
                title=f"Campaign Created: {title}",
                description=campaign_data.get('description', 'No description provided.'),
                color=discord.Color.green()
            )
            
            # Add campaign stats
            plot_sections = len([k for k in campaign_data.get('plot', {}) if campaign_data['plot'][k]])
            npc_count = len(campaign_data.get('key_npcs', []))
            location_count = len(campaign_data.get('key_locations', []))
            
            embed.add_field(name="Campaign Stats", 
                          value=f"• **Plot Acts:** {plot_sections}\n• **Key NPCs:** {npc_count}\n• **Locations:** {location_count}", 
                          inline=True)
            
            embed.add_field(name="Ready to Play", 
                          value=f"Use: `!load_campaign {sanitized_title}`", 
                          inline=True)
            
            embed.set_footer(text=f"Campaign saved as: {sanitized_title}.md | Vector index created")
            
            await ctx.send(embed=embed)
            await ctx.send(f"SUCCESS! Your campaign '{title}' is ready!\n\n**Next steps:**\n1. Load the campaign: `!load_campaign {sanitized_title}`\n2. Create characters: `!create_character`\n3. Begin your adventure!")

        except Exception as e:
            logging.error(f"An error occurred during the new campaign generation task: {e}", exc_info=True)
            await ctx.send(f"CRITICAL ERROR: Campaign generation failed.\n\n**Error:** {str(e)}\n\nTROUBLESHOOTING:\n• Check logs for detailed error info\n• Ensure local AI model is running\n• Try restarting the bot\n• Use a simpler campaign prompt")

    # Create the background task to run the generation logic.
    asyncio.create_task(generate_campaign_thread())

@bot.command(name='new_campaign_detailed')
@commands.is_owner()
async def new_campaign_detailed(ctx, *, prompt: str):
    """Generates an ultra-detailed campaign using multi-stage AI generation. (Owner only)"""
    # Input validation
    if not prompt or len(prompt.strip()) < 10:
        await ctx.send("ERROR: Campaign prompt is too short. Please provide at least 10 characters describing your desired campaign.")
        return
    
    if len(prompt) > 500:
        await ctx.send("ERROR: Campaign prompt is too long (max 500 characters). Please shorten your description.")
        return
    
    logging.info(f"Starting detailed campaign generation for prompt: '{prompt}'")
    
    # XAI integration disabled - using local LLM only
    generator = DetailedCampaignGenerator()
    api_info = "Local AI"
    
    await ctx.send(f"ULTRA-DETAILED CAMPAIGN GENERATION STARTED\n\n"
                  f"**Request:** {prompt}\n"
                  f"**AI Model:** {api_info}\n"
                  f"**Estimated Time:** 20-45 minutes\n"
                  f"**Expected Output:** 5,000+ words of detailed campaign content\n\n"
                  f"**This will create an incredibly detailed campaign suitable for 25-35 game sessions!**\n"
                  f"Progress updates will be posted here regularly...")

    async def detailed_generation_thread():
        try:
            # Get campaign structures
            structures = await get_all_campaign_structures()
            if not structures:
                await ctx.send("ERROR: No campaign structures found in database. Run `!analyze_structures` first.")
                return

            if len(structures) < 3:
                await ctx.send(f"WARNING: Only {len(structures)} campaign structures available. Consider running `!analyze_structures` for better results.")

            structures_text = "\n\n".join([f"Campaign: {s.campaign_name}\n{json.dumps(s.structure_data, indent=2)}" for s in structures])

            # Generate detailed campaign
            start_time = time.time()
            campaign_data = await generator.generate_complete_campaign(prompt, structures_text, ctx)
            generation_time = round((time.time() - start_time) / 60, 1)

            # Validate the generated campaign
            is_valid, validation_message = validate_campaign_data(campaign_data)
            if not is_valid:
                await ctx.send(f"QUALITY CHECK WARNING: {validation_message}\n\nProceeding with campaign save anyway...")

            title = campaign_data.get('title', 'Untitled Detailed Campaign')

            # Save and index the campaign
            await ctx.send(f"Final Stage: Saving '{title}' and creating knowledge indexes...")
            
            try:
                sanitized_title = await create_and_index_campaign(campaign_data)
                logging.info(f"Successfully created detailed campaign: {sanitized_title}")
            except Exception as e:
                await ctx.send(f"SAVE ERROR: Failed to save campaign: {str(e)}")
                return

            # Create comprehensive success report
            metadata = campaign_data.get('campaign_metadata', {})
            plot_word_count = sum(len(act.split()) for act in campaign_data.get('plot', {}).values())
            npc_count = len(campaign_data.get('key_npcs', []))
            location_count = len(campaign_data.get('key_locations', []))
            
            embed = discord.Embed(
                title=f"EPIC CAMPAIGN CREATED: {title}",
                description=f"**Ultra-detailed campaign ready for epic adventures!**\n\n{campaign_data.get('description', 'No description.')[:500]}...",
                color=discord.Color.gold()
            )
            
            embed.add_field(
                name="Campaign Statistics", 
                value=f"• **Plot Words:** ~{plot_word_count:,}\n"
                      f"• **Detailed NPCs:** {npc_count}\n"  
                      f"• **Rich Locations:** {location_count}\n"
                      f"• **Est. Sessions:** {metadata.get('estimated_sessions', '25-35')}\n"
                      f"• **Generation Time:** {generation_time} min",
                inline=True
            )
            
            embed.add_field(
                name="Ready to Play",
                value=f"**Load Command:**\n`!load_campaign {sanitized_title}`\n\n"
                      f"**AI Model Used:**\n{metadata.get('api_used', 'local').upper()}",
                inline=True
            )

            additional_elements = campaign_data.get('additional_elements', {})
            if additional_elements:
                themes = additional_elements.get('recurring_themes', [])
                if themes:
                    embed.add_field(
                        name="Campaign Themes",
                        value="\n".join([f"• {theme}" for theme in themes[:4]]),
                        inline=False
                    )

            embed.set_footer(text=f"File: {sanitized_title}.md | Method: Multi-stage AI generation | Vector indexes created")
            
            await ctx.send(embed=embed)
            
            # Additional success message with next steps
            await ctx.send(f"CAMPAIGN GENERATION COMPLETE!\n\n"
                          f"**What you got:**\n"
                          f"• Detailed 3-act plot structure with specific scenes\n"
                          f"• Rich NPCs with backstories, motivations, and secrets\n"
                          f"• Vivid locations with culture, politics, and mysteries\n"
                          f"• Side quests, betrayals, and moral dilemmas built-in\n"
                          f"• AI knowledge base ready for dynamic gameplay\n\n"
                          f"**Next Steps:**\n"
                          f"1. `!load_campaign {sanitized_title}` - Load the campaign\n"
                          f"2. `!create_character` - Create your characters\n"
                          f"3. Start your epic {metadata.get('estimated_sessions', 30)}-session adventure!\n\n"
                          f"**Pro Tip:** Your local AI DM now has detailed knowledge of this campaign for rich, consistent storytelling!")

        except Exception as e:
            logging.error(f"Detailed campaign generation failed: {e}", exc_info=True)
            await ctx.send(f"CRITICAL ERROR: Detailed campaign generation failed.\n\n"
                          f"**Error:** {str(e)}\n\n"
                          f"TROUBLESHOOTING:\n"
                          f"• Check your XAI API key in .env file\n"
                          f"• Ensure local AI model is running\n"
                          f"• Try `!new_campaign` for basic generation\n"
                          f"• Check logs for detailed error info")

    # Start the detailed generation process
    asyncio.create_task(detailed_generation_thread())

@bot.command(name='load_campaign_dynamic')
@commands.is_owner()
async def load_campaign_dynamic(ctx, *, campaign_name: str):
    """Load a campaign with dynamic state tracking for intelligent DM responses. (Owner only)"""
    logging.info(f"Loading campaign with dynamic state: '{campaign_name}'")
    
    async with ctx.typing():
        success = await campaign_state_manager.load_campaign(campaign_name)
    
    if success:
        state = campaign_state_manager.current_state
        embed = discord.Embed(
            title=f"Dynamic Campaign Loaded: {state.campaign_name}",
            description="Campaign loaded with intelligent state tracking and dynamic DM capabilities.",
            color=discord.Color.blue()
        )
        
        embed.add_field(
            name="Campaign Status",
            value=f"**Act:** {state.current_act}\n**Location:** {state.location}\n**Session:** {state.session_count}",
            inline=True
        )
        
        embed.add_field(
            name="Active NPCs",
            value=f"Tracking {len(state.npc_relationships)} key characters",
            inline=True
        )
        
        embed.add_field(
            name="Plot Threads",
            value=f"{len([t for t in state.active_plot_threads if t.status == 'active'])} active storylines",
            inline=True
        )
        
        embed.set_footer(text="The AI DM now has complete campaign knowledge and will dynamically respond to all player actions.")
        
        await ctx.send(embed=embed)
        await ctx.send("DYNAMIC CAMPAIGN ACTIVE! The AI DM will now:\n"
                      "• Track your actions and relationship changes\n"
                      "• Weave side activities into the main story\n"
                      "• Use NPCs to organically guide the narrative\n"
                      "• Adapt plot threads based on your choices\n\n"
                      "Simply type your actions and the AI will respond dynamically!")
        
    else:
        await ctx.send(f"ERROR: Could not load campaign '{campaign_name}'. Check that the campaign file exists in custom_campaigns/")

@bot.command(name='dm_response')
async def dm_response(ctx, *, player_action: str):
    """Get a dynamic DM response to player action. Available to all players."""
    if not campaign_state_manager.current_state:
        await ctx.send("ERROR: No campaign loaded. Use `!load_campaign_dynamic <name>` first.")
        return
    
    logging.info(f"Generating dynamic DM response for: {ctx.author.name} - {player_action}")
    
    async with ctx.typing():
        response = await dynamic_dm.generate_response(player_action, ctx.author.name)
    
    # Create rich response embed
    state = campaign_state_manager.current_state
    embed = discord.Embed(
        title=f"DM Response - {state.campaign_name}",
        description=response,
        color=discord.Color.purple()
    )
    
    embed.add_field(
        name="Current Status",
        value=f"**Act:** {state.current_act} | **Location:** {state.location}",
        inline=False
    )
    
    embed.set_footer(text=f"Session {state.session_count} | Dynamic AI DM")
    
    await ctx.send(embed=embed)

@bot.command(name='campaign_status')
async def campaign_status(ctx):
    """Show current campaign state and relationship status. Available to all players."""
    if not campaign_state_manager.current_state:
        await ctx.send("ERROR: No campaign loaded.")
        return
    
    state = campaign_state_manager.current_state
    
    embed = discord.Embed(
        title=f"Campaign Status: {state.campaign_name}",
        color=discord.Color.green()
    )
    
    embed.add_field(
        name="Progress",
        value=f"**Act:** {state.current_act}\n**Scene:** {state.current_scene}\n**Location:** {state.location}\n**Session:** {state.session_count}",
        inline=True
    )
    
    # Show NPC relationships
    relationship_text = ""
    for npc_name, npc in list(state.npc_relationships.items())[:5]:
        trust_indicator = ""
        if npc.trust_level > 50:
            trust_indicator = "TRUSTED"
        elif npc.trust_level > 0:
            trust_indicator = "FRIENDLY"
        elif npc.trust_level > -50:
            trust_indicator = "NEUTRAL"
        else:
            trust_indicator = "HOSTILE"
        
        relationship_text += f"**{npc.name}:** {trust_indicator} ({npc.trust_level})\n"
    
    if relationship_text:
        embed.add_field(
            name="NPC Relationships",
            value=relationship_text,
            inline=True
        )
    
    # Show active plot threads
    plot_text = ""
    active_plots = [t for t in state.active_plot_threads if t.status == "active"]
    for plot in active_plots[:3]:
        plot_text += f"• {plot.name}\n"
    
    if plot_text:
        embed.add_field(
            name="Active Storylines",
            value=plot_text,
            inline=False
        )
    
    embed.set_footer(text="The AI DM is tracking your progress and will adapt the story accordingly.")
    
    await ctx.send(embed=embed)

@bot.command(name='story_guidance')
@commands.is_owner()
async def story_guidance(ctx):
    """Get AI guidance on current story state and opportunities. (Owner only)"""
    if not campaign_state_manager.current_state:
        await ctx.send("ERROR: No campaign loaded.")
        return
    
    async with ctx.typing():
        guidance = await dynamic_dm.get_story_guidance()
    
    embed = discord.Embed(
        title="Story Guidance",
        description=guidance,
        color=discord.Color.gold()
    )
    
    embed.set_footer(text="AI analysis of current campaign state and opportunities")
    
    await ctx.send(embed=embed)

@bot.command(name='delete_campaign')
@commands.is_owner()
async def delete_campaign_command(ctx, *, campaign_name: str):
    """Deletes a campaign file and its database index. (Owner only)"""
    logging.info(f"Received request to delete campaign: '{campaign_name}'")
    
    async with ctx.typing():
        success, message = await delete_campaign(campaign_name)
        
    if success:
        await ctx.send(f"SUCCESS: {message}")
    else:
        await ctx.send(f"ERROR: {message}")


async def run_bot():
    if settings.DISCORD_TOKEN:
        try:
            await bot.start(settings.DISCORD_TOKEN)
        except discord.errors.LoginFailure:
            logging.error("Failed to log in. Please check your DISCORD_TOKEN.")
        except Exception as e:
            logging.error(f"An unexpected error occurred while running the bot: {e}")
            await bot.close()
    else:
        logging.error("DISCORD_TOKEN not found in environment variables.")

if __name__ == '__main__':
    # For direct execution, we need to run the async function
    try:
        asyncio.run(run_bot())
    except KeyboardInterrupt:
        print("Bot shutdown by user.")


