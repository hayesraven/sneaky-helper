from discord.ext import commands
import discord
import datetime

class Recording(commands.Cog, name="recording"):
    def __init__(self, bot) -> None:
        '''
        Constructor
        '''
        self.bot = bot
        self.connections = {}
    
    @commands.slash_command(
        name="start", 
        description="Record in my current channel!"
        )
    async def start_recording(self, ctx):
        '''
        start_recording:
        Action to gather connections in cache and begin recording
        '''
        voice = ctx.author.voice
        
        if not voice:
            await ctx.respond("You must be in a voice channel to start recording!")
            
        vc = await voice.channel.connect()      # Connect to current voice channel
        self.connections.update({ctx.guild.id: vc})  # Update cache with guild/channel
        
        vc.start_recording(
            discord.sinks.WaveSink(),            # Sink to use 
            self.once_done,                          # Coroutine when done recording
            ctx.channel,                         # Channel to disconnect from
            start_sync=True
        )
        
        recording = True
        await ctx.respond("Started recording!")    
        
    @commands.slash_command(
        name="stop", 
        description="Stop the recording and leave!"
        )
    async def stop_recording(self, ctx):
        '''
        stop_recording:
        Action to stop recording in channel and begin callback
        '''
        if ctx.guild.id in self.connections:  # Check if the guild is in the cache
            vc = self.connections[ctx.guild.id]
            vc.stop_recording()  # Stop recording, and call once_done (callback)
            del self.connections[ctx.guild.id]  # Remove the guild from the cache
            await ctx.delete()  # And delete
        else:
            await ctx.respond("I am currently not recording here.")
    
    async def once_done(self, sink, channel: discord.TextChannel, *args):
        '''
        once_done:
        Coroutine that runs when recording is stopped
        '''    
        recorded_users = []
        today = datetime.date.today().strftime("%d%b%Y")

        for user_id, audio, in sink.audio_data.items():
            if user_id not in self.bot.config['ignore_members']:
                username = await self.bot.fetch_user(user_id)
                recorded_users.append(str(username))
                filename = f"unprocessed/{today}_{username}.{sink.encoding}"
                with open(filename, 'wb') as f:
                    f.write(audio.file.getbuffer())
        
        await channel.send(("Finished! Recorded audio for "
                            f"{', '.join(recorded_users)}."))    
        
        # Call the transcription cog when the files are written and start
        transcription = self.bot.get_cog('transcription')
        await transcription.preprocess(test=False)
        await transcription.send_file(f"{self.bot.root}/processed/")

# this adds the cogs to bot
def setup(bot) -> None:
    bot.add_cog(Recording(bot))