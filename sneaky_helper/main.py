import discord
import os
import dotenv
import json
import sys
import ctypes.util
import logging
import argparse

import sneaky_helper.sneakybot as sneakybot

def gen_args():
    parser = argparse.ArgumentParser()
    
    parser.add_argument('-c', '--config', help="Configuration file.", required=True)
    
    return parser.parse_args()

def main():
    # parse the argument for the config file
    args = gen_args()
    
    # Check for config and grab it      
    # try:
    #     with open(f"{os.path.realpath(os.path.dirname(__file__))}"
    #             "/config.json") as file:
    #         config = json.load(file)
    # except:
    #     sys.exit("'config.json' not found! Please add it and try again.")
    with open(args.config) as conf_file:
        config = json.load(conf_file)
            
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
    bot = sneakybot.SneakyBot(config)
    bot.load_cogs()
    bot.run(os.getenv("TOKEN"))

if __name__ == "__main__":
    main()