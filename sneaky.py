import os, discord
from dotenv import load_dotenv
import ctypes
import ctypes.util

'''
Initial set up
'''
load_dotenv()
bot = discord.Bot(auto_sync_commands=True)
token = str(os.getenv("TOKEN"))
connections = {}
dont_listen = [
    #1139938844834271242 # KenkuBot
    ]

a = ctypes.util.find_library('opus')
discord.opus.load_opus(a)
if not discord.opus.is_loaded():
    raise RuntimeError('Opus failed to load')

@bot.event
async def on_ready():
    print(f"{bot.user} is ready!")
    
@bot.slash_command(name="hello", description="Say hello to the bot!")
async def hello(ctx):
    await ctx.respond("Hey!")

@bot.slash_command(name="help", description="Ask for help from me!")
async def help(ctx):
    embed_var = discord.Embed(title="Commands you can use!", 
                              description=("**/hello** to say hi!\n",
                                            "**/help** to see this message",
                                            "**/start** to start a recording in the current channel"), color=0x546e7a)
    await ctx.send(embed=embed_var)
    
async def once_done(sink: discord.sinks, channel: discord.TextChannel, *args):
    '''
    once_done:
    Coroutine that runs when recording is stopped
    '''
    await sink.vc.disconnect()  # Disconnect from voice channel
        
    files = []
    for user_id, audio, in sink.audio_data.items():
        if user_id not in dont_listen:
            username = await bot.fetch_user(user_id)
            with open(f"{username}.{sink.encoding}", 'wb') as f:
                f.write(audio.file.getbuffer())
                    
    '''
    TODO:
        - Check file size for hour long sessions
        - pass to faster
    '''
    
@bot.slash_command(name="start", description="Record in my current channel!")
async def start_recording(ctx):
    '''
    start_recording:
    Action to gather connections in cache and begin recording
    '''
    voice = ctx.author.voice
    
    if not voice:
        await ctx.respond("You must be in a voice channel to start recording!")
        
    vc = await voice.channel.connect()      # Connect to current voice channel
    connections.update({ctx.guild.id: vc})  # Update cache with guild and channel
    
    vc.start_recording(
        discord.sinks.WaveSink(),            # Sink to use 
        once_done,                          # Coroutine when done recording
        ctx.channel                         # Channel to disconnect from
    )
    
    await ctx.respond("Started recording!")
    
@bot.slash_command(name="stop", description="Stop the recording and leave!")
async def stop_recording(ctx):
    if ctx.guild.id in connections:  # Check if the guild is in the cache.
        vc = connections[ctx.guild.id]
        vc.stop_recording()  # Stop recording, and call the callback (once_done).
        del connections[ctx.guild.id]  # Remove the guild from the cache.
        await ctx.delete()  # And delete.
    else:
        await ctx.respond("I am currently not recording here.")  # Respond with this if we aren't recording.
    
bot.run(token)

'''
    What does SneakyBot need to do?
    1. Join channel on slash command.
    2. Stop recording and leave channel on slash command
    3. Gather all users, compare them to static 'no-record' list, and list out who will be recorded
    4. Begin recording.
    5. Save to copies to location and then transfer to whishper
'''


# help links
# this should help with merging and overlaying length of a file
# https://github.com/Pycord-Development/pycord/blob/master/examples/audio_recording_merged.py

# speaker diarization, might need it
# https://github.com/MahmoudAshraf97/whisper-diarization

# Explanation of using whisper
# https://wandb.ai/wandb_fc/gentle-intros/reports/OpenAI-Whisper-How-to-Transcribe-Your-Audio-to-Text-for-Free-with-SRTs-VTTs---VmlldzozNDczNTI0

# Another transcriber?
# https://github.com/RyanCheddar/discord-voice-message-transcriber/blob/main/main.py

# faster whisper
# https://github.com/SYSTRAN/faster-whisper

# whishper
# https://github.com/pluja/whishper