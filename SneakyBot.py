from discord.ext import commands
import discord
import json
import os
import platform
import logging
   
# Class for Bot creation
class SneakyBot(commands.Bot):
    def __init__(self, config) -> None:
        '''
        Constructor
        '''
        self.root = os.path.dirname(os.path.abspath(__file__))
        self.config_path = os.path.join(self.root, "config.json")
        self.config = self._config_with_defaults(config)
        self._apply_startup_overrides()
        intents = discord.Intents.default()
        intents.voice_states = True
        super().__init__(
            command_prefix=self.config['prefix'],
            auto_sync_commands=True,
            debug_guilds=self.config['debug_guild_ids'] or None,
            intents=intents
        )
        self.logger = logging.getLogger(__name__)
        logging.basicConfig(level=logging.DEBUG)
        self.apply_runtime_config()

    def _config_with_defaults(self, config) -> dict:
        '''
        _config_with_defaults:
        Adds new optional config values when older config files are loaded.
        '''
        config.setdefault('prefix', 'Sneaky')
        config.setdefault('ignore_members', [])
        config.setdefault('model_size_or_path', 'large-v2')
        config.setdefault('device', 'cpu')
        config.setdefault('compute_type', 'float32')
        config.setdefault('download_root', 'models/')
        config.setdefault('local_files_only', False)
        config.setdefault('transcript_channel_id', None)
        config.setdefault('debug_guild_ids', [])

        return config

    def _apply_startup_overrides(self) -> None:
        '''
        _apply_startup_overrides:
        Lets homelab deployment settings choose startup defaults without
        preventing runtime slash commands from changing them later.
        '''
        startup_model = os.getenv("SNEAKY_WHISPER_MODEL")
        if startup_model:
            self.config['model_size_or_path'] = startup_model

        startup_channel = os.getenv("SNEAKY_TRANSCRIPT_CHANNEL_ID")
        if startup_channel:
            try:
                self.config['transcript_channel_id'] = int(startup_channel)
            except ValueError:
                pass

    def apply_runtime_config(self) -> None:
        '''
        apply_runtime_config:
        Keeps frequently-used settings available as bot attributes.
        '''
        self.prefix = self.config['prefix']
        self.ignore_members = self.config['ignore_members']
        self.model_size_or_path = self.config['model_size_or_path']
        self.device = self.config['device']
        self.compute_type = self.config['compute_type']
        self.download_root = self.config['download_root']
        self.local_files_only = self.config['local_files_only']
        self.transcript_channel_id = self.config['transcript_channel_id']
    
    def update_config(self, config) -> None:
        '''
        update_config:
        Persists config.json and refreshes runtime attributes.
        '''
        self.config = self._config_with_defaults(config)
        with open(self.config_path, 'w') as f:
            json.dump(self.config, f, indent=4)
        self.apply_runtime_config()

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
