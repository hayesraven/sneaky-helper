from discord.ext import commands
import discord
import logging

class Utils(commands.Cog, name="utils"):
    def __init__(self, bot) -> None:
        '''
        Constructor
        '''
        self.bot = bot
        self.logger = logging.getLogger(__name__)
        logging.basicConfig(level=logging.DEBUG)
        
    @commands.slash_command(
        name="hello", description="Say hello to the bot!"
        )
    async def hello(self, ctx):
        await ctx.respond("Hey!")
        
    @commands.slash_command(
        name="help", 
        description="Ask for help from me!"
        )
    async def help(self, ctx):
        '''
        help:
        Shows a list of available commands
        '''
        embed_var = discord.Embed(
            title="Commands you can use!", 
            description=(
                "**/hello** to say hi!\n"
                "**/help** to see this message\n"
                "**/ignore @<username>** to add a user to the Do Not Listen "
                "To list\n"
                "**/listen @<username>** to remove a user from the Do Not "
                "To Listen list\n"
                "**/stop** to stop a recording and save the data\n"
                "**/start** to start a recording in the current channel\n"
                "**/set_transcript_channel #channel** to choose where "
                "transcripts are sent\n"
                "**/show_transcript_channel** to show the current transcript "
                "channel\n"
                "**/set_whisper_model <model>** to choose the Whisper model\n"
                "**/show_whisper_model** to show the active Whisper model\n"),
            color=0x546e7a)
                                                
        await ctx.respond(embed=embed_var)
        
    @commands.slash_command(
        name="ignore", 
        description=("Add a user to the 'don't listen to' list")
        )
    async def ignore(self, ctx, user: discord.User):
        '''
        ignore:
        Action to add a user ID to the ignore list for recording
        '''
        config = self.bot.config
        if user.id not in config["ignore_members"]:
            config["ignore_members"].append(user.id)

        await self.update_config(config)        
        await ctx.respond(f"Added {user.name} to the ignore list!")
        
    @commands.slash_command(
        name="listen", 
        description=("Remove a user from the 'don't listen to' list")
        )
    async def listen(self, ctx, user: discord.User):
        '''
        listen:
        Action to remove a user ID from the ignore list for recording
        '''
        config = self.bot.config

        if user.id in config["ignore_members"]:
            config["ignore_members"].remove(user.id)
        
        await self.update_config(config)        
        await ctx.respond(f"I will now eavesdrop on {user.name}!")
        
    @commands.slash_command(
        name="list_ignore", 
        description=("List the members on the 'don't listen to' list ")
        )
    async def list_ignore(self, ctx):
        '''
        list_ignore:
        Action to list a users currently on the ignore list for recording
        '''
        config = self.bot.config
        users = ""
        
        for user_id in config["ignore_members"]:
            user = await self.bot.fetch_user(user_id)
            users += user.name + '\n'
            
        await ctx.respond("Currently ignoring the following members for "
                          f"transcription:\n{users}")

    @commands.slash_command(
        name="set_transcript_channel",
        description="Choose the channel where transcripts are posted"
        )
    async def set_transcript_channel(
            self, ctx, channel: discord.TextChannel):
        '''
        set_transcript_channel:
        Stores the transcript delivery channel.
        '''
        config = self.bot.config
        config["transcript_channel_id"] = channel.id

        await self.update_config(config)
        await ctx.respond(f"Transcripts will be sent to {channel.mention}.")

    @commands.slash_command(
        name="show_transcript_channel",
        description="Show the configured transcript channel"
        )
    async def show_transcript_channel(self, ctx):
        '''
        show_transcript_channel:
        Displays the current transcript delivery channel.
        '''
        channel_id = self.bot.transcript_channel_id
        channel = self.bot.get_channel(channel_id) if channel_id else None

        if channel:
            await ctx.respond(f"Transcripts are sent to {channel.mention}.")
        else:
            await ctx.respond("No transcript channel is configured yet.")

    @commands.slash_command(
        name="set_whisper_model",
        description="Choose the Whisper model for future transcriptions"
        )
    async def set_whisper_model(self, ctx, model: str):
        '''
        set_whisper_model:
        Stores the model used when new recording sessions are transcribed.
        '''
        config = self.bot.config
        config["model_size_or_path"] = model

        await self.update_config(config)
        await ctx.respond(f"Whisper model set to `{model}`.")

    @commands.slash_command(
        name="show_whisper_model",
        description="Show the active Whisper model and runtime settings"
        )
    async def show_whisper_model(self, ctx):
        '''
        show_whisper_model:
        Displays the active transcription runtime settings.
        '''
        await ctx.respond(
            "Whisper settings:\n"
            f"Model: `{self.bot.model_size_or_path}`\n"
            f"Device: `{self.bot.device}`\n"
            f"Compute type: `{self.bot.compute_type}`"
        )
        
    async def update_config(self, config):
        '''
        update_config:
        Updates the config.json for SneakyBot
        '''
        self.bot.update_config(config)

# this adds the cogs to bot
def setup(bot) -> None:
    bot.add_cog(Utils(bot))
