# src/sync_campaigns.py
import os
import re
import asyncio
import asyncpg
import sys

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.config import settings

CAMPAIGNS_DIR = "dnd_src_material/custom_campaigns"

def generate_display_name(filename: str) -> str:
    """Generates a human-readable name from a filename."""
    # Remove .md extension
    name = filename.replace(".md", "")
    # Remove common prefixes
    name = re.sub(r'^(campaign_title_|campaign_)', '', name)
    # Replace underscores with spaces and capitalize
    name = name.replace("_", " ").title()
    return name

async def main():
    """
    Scans the campaign directory and ensures each .md file has a corresponding
    entry in the 'campaigns' database table.
    """
    print("--- Starting Campaign Sync Script ---")
    
    conn = None
    try:
        db_url = settings.DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://")
        conn = await asyncpg.connect(db_url)
        print("✅ Database connection successful.")

        # 1. Get existing campaigns from the database
        existing_records = await conn.fetch("SELECT name FROM campaigns")
        existing_campaign_names = {record['name'] for record in existing_records}
        print(f"Found {len(existing_campaign_names)} existing campaigns in the database.")

        # 2. Get campaign files from the directory
        if not os.path.isdir(CAMPAIGNS_DIR):
            print(f"❌ ERROR: Campaign directory not found at '{CAMPAIGNS_DIR}'. Aborting.")
            return

        campaign_files = [f for f in os.listdir(CAMPAIGNS_DIR) if f.endswith('.md')]
        print(f"Found {len(campaign_files)} .md files in '{CAMPAIGNS_DIR}'.")

        # 3. Compare and insert missing campaigns
        added_count = 0
        for filename in campaign_files:
            if filename not in existing_campaign_names:
                display_name = generate_display_name(filename)
                file_path = os.path.join(CAMPAIGNS_DIR, filename).replace("\", "/")
                description = f"A campaign titled '{display_name}'."

                print(f"  -> Adding new campaign: '{filename}' as '{display_name}'")
                await conn.execute(
                    """
                    INSERT INTO campaigns (name, display_name, description, file_path)
                    VALUES ($1, $2, $3, $4)
                    ON CONFLICT (name) DO NOTHING;
                    """,
                    filename, display_name, description, file_path
                )
                added_count += 1
        
        if added_count > 0:
            print(f"✅ Successfully added {added_count} new campaigns to the database.")
        else:
            print("✅ Database is already up-to-date. No new campaigns were added.")

    except Exception as e:
        print(f"❌ An error occurred: {e}")
    finally:
        if conn:
            await conn.close()
            print("Database connection closed.")

if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())
