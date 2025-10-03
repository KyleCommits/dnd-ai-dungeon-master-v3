# start_system.py
import logging
import sys
import asyncio
from src.bot import run_bot
from src.setup_indexes import main as setup_indexes
from src.llm_manager import llm_manager

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

async def main():
    """Main function to start the system."""
    try:
        # First, set up the indexes.
        logging.info("Setting up LlamaIndex indexes...")
        await setup_indexes()
        logging.info("Index setup complete.")

        # Load the local LLM model directly
        logging.info("Loading local LLM model...")
        llm_manager.load_model()
        logging.info("LLM model loaded.")

        # Now, start the bot.
        logging.info("Starting Discord bot...")
        await run_bot()

    except Exception as e:
        logging.error(f"An error occurred during system startup: {e}")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logging.info("System startup interrupted by user.")
