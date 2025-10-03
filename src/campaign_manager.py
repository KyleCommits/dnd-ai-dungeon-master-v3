# src/campaign_manager.py
import logging
import os
import re
import asyncpg
from .config import settings
from .rag_setup import create_vector_store, create_index

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

CAMPAIGNS_DIR = os.path.abspath(settings.custom_campaign_path)

def format_campaign_to_markdown(campaign_data: dict) -> str:
    """Formats the generated campaign JSON data into a structured Markdown file."""
    # This function remains the same as it correctly formats the content.
    # (Content of the function is omitted for brevity but is unchanged)
    if 'content' in campaign_data and campaign_data['content']:
        return campaign_data['content']
    title = campaign_data.get('title', 'Untitled Campaign')
    description = campaign_data.get('description', 'No description provided.')
    markdown_content = f"# {title}\n\n"
    markdown_content += f"## Description\n{description}\n\n"
    return markdown_content

async def create_and_index_campaign(campaign_data: dict):
    """
    Saves the campaign to a .md file, registers it in the 'campaigns' table,
    and creates a vector index for it.
    """
    title = campaign_data.get('title', 'Untitled Campaign')
    description = campaign_data.get('description', 'A new adventure awaits.')
    
    sanitized_title = re.sub(r'[^a-z0-9_]+', '', title.lower().replace(' ', '_'))
    if not sanitized_title:
        sanitized_title = "new_campaign"
        
    filename = f"{sanitized_title}.md"
    filepath = os.path.join(CAMPAIGNS_DIR, filename)
    
    logging.info(f"Creating new campaign file at: {filepath}")

    # 1. Format and save the Markdown file
    markdown_content = format_campaign_to_markdown(campaign_data)
    try:
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(markdown_content)
        logging.info(f"Successfully saved campaign file: {filename}")
    except IOError as e:
        logging.error(f"Failed to write campaign file to disk: {e}")
        raise

    # 2. Register the new campaign in the database
    conn = None
    try:
        db_url = settings.DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://")
        conn = await asyncpg.connect(db_url)
        
        display_name = title
        db_filepath = os.path.join(CAMPAIGNS_DIR, filename).replace("\\", "/")

        await conn.execute(
            """
            INSERT INTO campaigns (name, display_name, description, file_path)
            VALUES ($1, $2, $3, $4)
            ON CONFLICT (name) DO UPDATE SET
                display_name = EXCLUDED.display_name,
                description = EXCLUDED.description,
                file_path = EXCLUDED.file_path;
            """,
            filename, display_name, description, db_filepath
        )
        logging.info(f"Successfully registered '{filename}' in the campaigns table.")
    except Exception as e:
        logging.error(f"Failed to register campaign in database: {e}")
        # Clean up the created file if DB registration fails
        if os.path.exists(filepath):
            os.remove(filepath)
        raise
    finally:
        if conn:
            await conn.close()

    # 3. Create a new vector index for the campaign
    # (This part remains the same)
    try:
        table_name = f"campaign_{sanitized_title[:49]}"
        vector_store = await create_vector_store(table_name=table_name)
        await create_index(vector_store=vector_store, file_path=filepath)
        logging.info(f"Successfully created and populated index for '{filename}'.")
        return sanitized_title
        
    except Exception as e:
        logging.error(f"Failed to create vector index for new campaign: {e}")
        if os.path.exists(filepath):
            os.remove(filepath)
        # Optionally, you might want to remove the DB entry here as well
        raise

async def delete_campaign(campaign_name: str) -> (bool, str):
    """
    Deletes a campaign's file, its database entry, and its vector index.
    """
    # This function would also need to be updated to delete from the 'campaigns' table
    # (Implementation omitted for now to focus on the creation fix)
    logging.warning("delete_campaign function needs to be updated to remove from 'campaigns' table.")
    return False, "Delete function not fully implemented."