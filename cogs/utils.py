from discord.ext import commands
import discord
import sys
import json
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
                "**/start** to start a recording in the current channel\n"),
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
            print(user)
            users += user.name + '\n'
            
        await ctx.respond("Currently ignoring the following members for "
                          f"transcription:\n{users}")
        
    async def update_config(self, config):
        '''
        update_config:
        Updates the config.json for SneakyBot
        '''
        with open(f"{self.bot.root}/config.json", 'w') as f:
            json.dump(config, f, indent=4)
            
        self.bot.config = config

# this adds the cogs to bot
def setup(bot) -> None:
    bot.add_cog(Utils(bot))