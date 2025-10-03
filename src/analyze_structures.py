# src/analyze_structures.py
import os
import sys
import asyncio
import json
import logging
import argparse
from PyPDF2 import PdfReader
from sqlalchemy import delete
from sqlalchemy.future import select

# Add project root to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.database import AsyncSessionLocal
from src.llm_manager import llm_manager
from src.models import CampaignStructure
from src.config import settings

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

CAMPAIGNS_DIR = settings.campaign_pdf_path

def get_campaign_files():
    """Lists all .md and .pdf files in the campaigns directory."""
    files = []
    if not os.path.isdir(CAMPAIGNS_DIR):
        logging.error(f"Campaigns directory not found at: {CAMPAIGNS_DIR}")
        return files
        
    for filename in os.listdir(CAMPAIGNS_DIR):
        if filename.endswith(('.md', '.pdf')):
            files.append(os.path.join(CAMPAIGNS_DIR, filename))
    logging.info(f"Found {len(files)} campaign files to analyze.")
    return files

def read_file_content(filepath: str) -> str:
    """Reads content from a file, supporting .md and .pdf."""
    logging.info(f"Reading file: {filepath}")
    content = ""
    try:
        if filepath.endswith('.md'):
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
        elif filepath.endswith('.pdf'):
            with open(filepath, 'rb') as f:
                reader = PdfReader(f)
                for page in reader.pages:
                    content += page.extract_text() or ""
    except Exception as e:
        logging.error(f"Error reading {filepath}: {e}")
    return content

async def analyze_campaign_structure(content: str) -> str:
    """
    Uses the LLM to analyze campaign content and extract narrative structures.
    Runs the synchronous LLM call in a separate thread to avoid blocking.
    """
    prompt = f"""
    Analyze the following D&D campaign content and extract its core narrative structure.
    Provide the output in a clean JSON format. Do not include any text before or after the JSON block.
    The JSON object should contain the following keys:
    - "narrative_structure": A brief description of the overall story arc (e.g., "Classic hero's journey," "Sandbox investigation").
    - "plot_hook_types": A list of the main methods used to draw players into the story (e.g., "Mysterious letter," "NPC in distress," "Ancient prophecy").
    - "npc_archetypes": A list of key non-player character roles (e.g., "Wise old mentor," "Scheming vizier," "Betrayed ally").
    - "villain_motivations": A brief description of the primary antagonist's goals (e.g., "Achieve godhood," "Revenge for a past wrong," "World domination").
    - "key_locations": A list of 3-5 critical locations in the campaign.
    - "major_plot_points": A list of 3-5 major events or turning points in the story.

    Campaign Content:
    ---
    {content[:8000]}
    ---
    """
    logging.info("Sending content to LLM for analysis...")
    loop = asyncio.get_running_loop()
    analysis_json_str = await loop.run_in_executor(
        None,
        lambda: asyncio.run(llm_manager.generate(prompt, max_new_tokens=1024))
    )
    return analysis_json_str

async def main(fresh_start: bool = False):
    """
    Main function to process campaign files, analyze them, and store the
    results in the database.
    """
    print("DEBUG: Inside main function.")
    logging.info("Starting campaign structure analysis...")
    
    async with AsyncSessionLocal() as session:
        if fresh_start:
            logging.info("Fresh start requested. Deleting existing campaign structure data...")
            await session.execute(delete(CampaignStructure))
            await session.commit()
            logging.info("Existing data deleted.")

        campaign_files = get_campaign_files()
        
        for filepath in campaign_files:
            campaign_name = os.path.basename(filepath)
            
            result = await session.execute(
                select(CampaignStructure).filter_by(campaign_name=campaign_name)
            )
            existing = result.scalars().first()
            
            if existing:
                logging.info(f"Skipping '{campaign_name}', analysis already exists.")
                continue

            content = read_file_content(filepath)
            if not content:
                continue

            if len(content) > 8192:
                logging.warning(f"Content for {campaign_name} is very long, truncating for analysis.")
                content = content[:8192]

            analysis_json_str = await analyze_campaign_structure(content)
            
            try:
                clean_json_str = analysis_json_str.strip().replace('```json', '').replace('```', '').strip()
                structure_data = json.loads(clean_json_str)
                
                new_structure = CampaignStructure(
                    campaign_name=campaign_name,
                    structure_data=structure_data
                )
                session.add(new_structure)
                await session.commit()
                logging.info(f"Successfully analyzed and stored structure for '{campaign_name}'.")
                
            except json.JSONDecodeError as e:
                logging.error(f"Failed to decode JSON for '{campaign_name}': {e}")
                logging.error(f"Received string: {analysis_json_str}")
            except Exception as e:
                logging.error(f"An error occurred while processing '{campaign_name}': {e}")
                await session.rollback()

    logging.info("Campaign structure analysis finished.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Analyze D&D campaign structures.")
    parser.add_argument(
        '--fresh',
        action='store_true',
        help='If set, the script will delete all existing analysis data before starting.'
    )
    args = parser.parse_args()

    llm_manager.load_model()
    print("DEBUG: Model loaded, about to run asyncio.run(main()).")
    asyncio.run(main(fresh_start=args.fresh))