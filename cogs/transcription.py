from discord.ext import commands
from discord.utils import get
import pydub
import os
import faster_whisper
import logging
import re
import discord

"""
These are the arguments the whisper model takes in:
Option: default

model_size_or_path: 
Size of the model to use (tiny, tiny.en, base, base.en,
small, small.en, medium, medium.en, large-v1, large-v2, large-v3, or large), 
a path to a converted model directory, or a CTranslate2-converted Whisper 
model ID from the HF Hub. When a size or a model ID is configured, the 
converted model is downloaded from the Hugging Face Hub.

device: auto
Device to use for computation ("cpu", "cuda", "auto"). 

device_index: 0
Device ID to use. The model can also be loaded on multiple GPUs by passing a
ist of IDs (e.g. [0, 1, 2, 3]). In that case, multiple transcriptions can run
in parallel when transcribe() is called from multiple Python threads (see also
num_workers).

compute_type: default
Type to use for computation. See https://opennmt.net/CTranslate2/quantization.html.

cpu_threads: 4
Number of threads to use when running on CPU. A non zero value overrides the 
OMP_NUM_THREADS environment variable. 

num_workers: 1
When transcribe() is called from multiple Python threads, having multiple
workers enables true parallelism when running the model (concurrent calls
to self.model.generate() will run in parallel). This can improve the global
throughput at the cost of increased memory usage.

download_root: 
Directory where the models should be saved. If not set, the models are saved in
the standard Hugging Face cache directory. 

local_files_only: False
If True, avoid downloading the file and return the path to the local cached
file if it exists.
"""

class Transcription(commands.Cog, name="transcription"):
    def __init__(self, bot) -> None:
        '''
        Constructor
        '''
        self.bot = bot
        self.logger = logging.getLogger(__name__)
        logging.basicConfig(level=logging.DEBUG)
        
    async def preprocess_init(self, test: bool):
        '''
        preprocess_init:
        Allows transcribe to be ran in separate thread
        '''
        await self.bot.loop.run_in_executor(None, self.preprocess, test)
    
    async def transcribe_init(self, unfilepath, test: bool):
        '''
        transcribe_init:
        Allows transcribe to be ran in separate thread
        '''
        await self.bot.loop.run_in_executor(None, self.transcribe, unfilepath, test)
    
    async def merge_init(self, pfilepath):
        '''
        merge_init:
        Allows merge to be ran in separate thread
        '''
        await self.bot.loop.run_in_executor(None, self.merge, pfilepath)
    
    async def send_file(self, ctx, pfilepath):
        '''
        send_file:
        Finds the newest final transcript and sends it to the channel
        '''
        channel_name = 'transcripts'
        channel = get(ctx.guild.channels, name=channel_name)
        
        if channel:
            channel_id = channel.id
            
            for file in [f for f in os.listdir(pfilepath) 
                    if os.path.isfile(os.path.join(pfilepath, f))]: 
                match = re.search(r"_final\.txt", file)
                if match:
                    filename = pfilepath + file
                    
                    with open(filename, 'rb') as f:
                        file = discord.File(f)
                        await channel.send(file=file)
        else:
            ctx.respond(f"ERROR: {channel_name} cannot be found!")
        
    def preprocess(self, test: bool):
        '''
        preprocess:
        take in files, process them, and prep them for transcription
        and diarization
        '''
        segments = []
        longest = ['',0,pydub.AudioSegment.empty()]
        filepath = f"{self.bot.root}/unprocessed/"

        for file in [f for f in os.listdir(filepath) 
                    if os.path.isfile(os.path.join(filepath, f))]:
            curr = []
            curr.append(filepath + file)
            seg = pydub.AudioSegment.from_file(curr[0], format="mp3")
            seg_len = len(seg)
            curr.append(seg_len)
            curr.append(seg)
                
            # Determine the longest audio segment
            if curr[1] > longest[1]:
                segments.append(longest)
                longest[0] = curr[0]
                longest[1] = curr[1]
                longest[2] = curr[2]
            else:
                segments.append(curr)

        # Using the length of the longest file, we prepend silence to 
        # each other file to make them the same length. This will allow
        # us to sync the timestamps in the transcriptions and create one
        # final script of the entire audio session
        for file in segments:
            curr_len = longest[1] - file[1]
            silence = pydub.AudioSegment.silent(duration=curr_len)
            final = silence + file[2]
            final.export(file[0], format="mp3")

        final = longest[2]
        final.export(longest[0], format="mp3") 
        
        if not test:
            self.transcribe(filepath, test=False)
        
    def transcribe(self, unfilepath, test: bool):
        '''
        transcribe:
        Handles WhisperX transcription of the files
        '''
        model = faster_whisper.WhisperModel(
            model_size_or_path=self.bot.model_size_or_path,
            device=self.bot.device,
            compute_type=self.bot.compute_type,
            download_root=self.bot.download_root,
            local_files_only=self.bot.local_files_only       
        )
        pfilepath = f"{self.bot.root}/processed/"
        
        for file in [f for f in os.listdir(unfilepath) 
                     if os.path.isfile(os.path.join(unfilepath, f))]:
            segments, info = model.transcribe(
                unfilepath + file,
                language="en",
                condition_on_previous_text=False,
                vad_filter=True
                )
            self.logger.info(f"Detected language '{info.language}'"
                             f" with probability {info.language_probability}")
            
            filename = pfilepath + file.replace('.mp3', '.txt')
            with open(filename, 'w') as f:
                for segment in segments:
                    line = "[%.3fs] %s\n" % (segment.start, segment.text)
                    f.write(line)        
        
        if not test:
            self.merge(pfilepath)        
        
    def merge(self, pfilepath):
        '''
        merge:
        Handles transcription merging and formatting
        '''
        lines = []
        reg_transcript = r'(?P<timestamp>\[(?P<time_float>[0-9]+.[0-9]+)s\])\s\s(?P<string>.+)$'
        reg_username = r'^.+/(?P<date>[0-9a-zA-Z]+)_(?P<username>.+)#'
        date = ""
        
        for file in [f for f in os.listdir(pfilepath) 
                    if os.path.isfile(os.path.join(pfilepath, f))]: 
            
            filename = pfilepath + file
            match_user = re.match(reg_username, filename)

            if date == "" and match_user is not None:
                date = match_user.group('date')
                
            with open(filename, 'r') as f:
                data = f.read()
            
            for line in data.splitlines():
                match_script = re.match(reg_transcript, line)

                if match_script is not None and match_user is not None:
                    curr = {
                        'time_float': float(match_script.group('time_float')),
                        'string': 
                            match_script.group('timestamp') + " " +
                            match_user.group('username') + ': "' +
                            match_script.group('string') + '"' + "\n"
                    }
                    lines.append(curr)
        
        final = sorted(lines, key=lambda d: d['time_float'])
        
        with open(f"{pfilepath}{date}_final.txt", 'w') as f:
            for line in final:
                f.write(line['string'])
    
# this adds the cogs to bot
def setup(bot) -> None:
    bot.add_cog(Transcription(bot))