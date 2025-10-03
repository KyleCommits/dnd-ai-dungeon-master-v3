# tests/test_send_message.py
import asyncio
import discord
import os
import sys
import logging
import datetime

# Add project root to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.config import settings

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Define intents
intents = discord.Intents.default()
intents.messages = True
intents.message_content = True

client = discord.Client(intents=intents)

@client.event
async def on_ready():
    """
    This event is triggered once the bot is connected and ready.
    """
    logging.info(f'Logged in as {client.user}')
    
    try:
        channel_id = settings.BOT_CHANNEL_ID
        if not channel_id:
            logging.error("BOT_CHANNEL_ID is not set in the .env file.")
            await client.close()
            return
            
        channel = client.get_channel(channel_id)
        
        if channel:
            logging.info(f"Found channel: '{channel.name}' ({channel.id})")
            
            # Construct the test command
            timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
            test_prompt = f"A test campaign generated at {timestamp} about a lost artifact in a forgotten jungle temple."
            command = f"!new_campaign {test_prompt}"
            
            await channel.send(command)
            logging.info(f"Sent test command to the bot: '{command}'")
        else:
            logging.error(f"Could not find the channel with ID: {channel_id}. Please check the BOT_CHANNEL_ID in your .env file.")
            
    except Exception as e:
        logging.error(f"An error occurred: {e}")
    finally:
        # Disconnect the bot after sending the message
        logging.info("Closing the connection.")
        await client.close()

async def main():
    """
    Main function to run the bot.
    """
    token = settings.DISCORD_TOKEN
    if not token:
        logging.error("DISCORD_TOKEN is not set in the .env file.")
        return
        
    try:
        logging.info("Attempting to connect to Discord...")
        await client.start(token)
    except discord.errors.LoginFailure:
        logging.error("Failed to log in. Please ensure your DISCORD_TOKEN is correct.")
    except Exception as e:
        logging.error(f"An unexpected error occurred: {e}")

if __name__ == "__main__":
    # This allows the script to be run directly.
    # It will connect, send one message, and then disconnect.
    asyncio.run(main())
