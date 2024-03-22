import discord
import os
import dotenv
import json
import sys
import ctypes.util
import SneakyBot
import logging

if __name__ == "__main__":
    # Check for config and grab it      
    try:
        with open(f"{os.path.realpath(os.path.dirname(__file__))}"
                "/config.json") as file:
            config = json.load(file)
    except:
        sys.exit("'config.json' not found! Please add it and try again.")
            
    # Set up opus and such to make sure you can handle audio filesfiles
    a = ctypes.util.find_library('opus')
    discord.opus.load_opus(a) # type: ignore
    if not discord.opus.is_loaded():
        sys.exit('Opus failed to load! Exiting...')
        
    # Set up logging
    logger = logging.getLogger(__name__)
    logging.basicConfig(level=logging.INFO)
        
    # Start Sneaky      
    dotenv.load_dotenv()          
    bot = SneakyBot.SneakyBot(config)
    bot.load_cogs()
    bot.run(os.getenv("TOKEN"))