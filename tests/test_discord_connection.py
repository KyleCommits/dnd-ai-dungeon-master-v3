# tests/test_discord_connection.py
import discord
import asyncio
import logging
import sys
import os

# Add src to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.config import settings

# --- Configuration ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
)

# --- Test Logic ---

class TestBot(discord.Client):
    async def on_ready(self):
        logging.info(f'Successfully logged in as {self.user}.')
        logging.info('Discord token is valid.')
        logging.info('Closing connection in 3 seconds...')
        await asyncio.sleep(3)
        await self.close_bot()

    async def close_bot(self):
        await self.http.close()
        await self.close()

    async def on_error(self, event, *args, **kwargs):
        logging.error(f"An error occurred in event: {event}")
        await self.close_bot()

async def main():
    if not settings.DISCORD_TOKEN:
        logging.error("DISCORD_TOKEN not found in .env file.")
        return

    logging.info("Attempting to connect to Discord...")
    
    intents = discord.Intents.default()
    client = TestBot(intents=intents)
    
    try:
        await client.start(settings.DISCORD_TOKEN)
    except discord.errors.LoginFailure:
        logging.error("Discord login failed. Please check if your DISCORD_TOKEN is correct.")
    except Exception as e:
        if client.is_closed():
            logging.info("Client is already closed.")
        else:
            logging.error(f"An unexpected error occurred: {e}")

if __name__ == "__main__":
    asyncio.run(main())
