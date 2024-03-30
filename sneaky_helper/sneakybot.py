from discord.ext import commands
import discord
import os
import platform
import logging
   
# Class for Bot creation
class SneakyBot(commands.Bot):
    def __init__(self, config) -> None:
        '''
        Constructor
        '''
        super().__init__(
            auto_sync_commands=True
        )
        self.config = config
        self.logger = logging.getLogger(__name__)
        logging.basicConfig(level=logging.DEBUG)
        self.prefix = self.config['prefix']
        self.ignore_members = self.config['ignore_members']
        self.model_size_or_path = self.config['model_size_or_path']
        self.device = self.config['device']
        self.compute_type = self.config['compute_type']
        self.download_root = self.config['download_root']
        self.local_files_only = self.config['local_files_only']
        self.root = os.path.dirname(os.path.abspath(__file__))
    
    async def on_ready(self):
        print(f"{self.user} is ready!")
                
    def load_cogs(self) -> None:
        '''
        load_cogs:
        '''
        self.logger.info(f"Logged in as {self.user}")
        self.logger.info(f"discord.py API version: {discord.__version__}")
        self.logger.info(f"Python version: {platform.python_version()}")
        self.logger.info(
            f"Running on: {platform.system()} {platform.release()} ({os.name})"
        )
        self.logger.info("-------------------")
        
        for file in os.listdir(
            f"{os.path.realpath(os.path.dirname(__file__))}/cogs"
            ):
            if file.endswith(".py"):
                extension = file[:-3]
                try:
                    self.load_extension(f"cogs.{extension}")
                    self.logger.info(f"Loaded extension '{extension}'")
                except Exception as e:
                    exception = f"{type(e).__name__}: {e}"
                    self.logger.error(
                        f"Failed to load extension {extension}\n{exception}"
                    )