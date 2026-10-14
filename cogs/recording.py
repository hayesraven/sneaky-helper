from discord.ext import commands
import discord
import asyncio
import datetime
import inspect
import json
import os
import re
import wave


class SneakyWaveSink(discord.sinks.WaveSink):
    '''
    SneakyWaveSink:
    Compatibility shim for Pycord 2.8's DAVE receiver path.
    '''
    __sink_listeners__ = []

    def walk_children(self, *args, **kwargs):
        return []

    def write(self, data, user):
        pcm = getattr(data, "pcm", data)
        if pcm is None:
            return
        if not isinstance(pcm, (bytes, bytearray)):
            pcm = bytes(pcm)
        super().write(bytes(pcm), user)

    def format_audio(self, audio):
        if self.vc and self.vc.is_recording():
            raise discord.sinks.WaveSinkError(
                "Audio may only be formatted after recording is finished."
            )

        data = audio.file
        with wave.open(data, "wb") as f:
            f.setnchannels(discord.opus.Decoder.CHANNELS)
            f.setsampwidth(
                discord.opus.Decoder.SAMPLE_SIZE // discord.opus.Decoder.CHANNELS
            )
            f.setframerate(discord.opus.Decoder.SAMPLING_RATE)

        data.seek(0)
        audio.on_format(self.encoding)

class Recording(commands.Cog, name="recording"):
    def __init__(self, bot) -> None:
        '''
        Constructor
        '''
        self.bot = bot
        self.sessions = {}

    def _safe_name(self, value: str) -> str:
        '''
        _safe_name:
        Keeps Discord display names usable in local filenames.
        '''
        safe = re.sub(r"[^a-zA-Z0-9_.-]+", "_", value).strip("._")
        return safe or "speaker"

    def _session_paths(self, guild_id: int, session_id: str) -> dict:
        '''
        _session_paths:
        Builds the folder layout for one recording session.
        '''
        session_root = os.path.join(
            self.bot.root, "sessions", str(guild_id), session_id
        )
        return {
            "session_root": session_root,
            "raw_dir": os.path.join(session_root, "raw"),
            "processed_dir": os.path.join(session_root, "processed"),
            "manifest_path": os.path.join(session_root, "manifest.json"),
        }

    def _write_manifest(self, session: dict) -> None:
        '''
        _write_manifest:
        Persists the session metadata used for speaker attribution.
        '''
        with open(session["manifest_path"], 'w') as f:
            json.dump(session["manifest"], f, indent=4)

    def _sink_for_session(self, guild_id: int, session_id: str):
        '''
        _sink_for_session:
        Stores session identifiers on the sink so newer Pycord callbacks do not
        depend on deprecated custom callback args.
        '''
        sink = SneakyWaveSink()
        sink.sneaky_guild_id = guild_id
        sink.sneaky_session_id = session_id
        return sink

    async def _speaker_label(self, guild_id: int, user_id: int) -> str:
        '''
        _speaker_label:
        Prefer the server display name, but keep the Discord handle visible.
        '''
        guild = self.bot.get_guild(guild_id)
        member = guild.get_member(user_id) if guild else None
        if member:
            handle = str(member)
            if member.display_name and member.display_name != member.name:
                return f"{member.display_name} ({handle})"
            return handle

        user = await self.bot.fetch_user(user_id)
        return str(user)

    def _voice_participants(self, voice_channel) -> list:
        '''
        _voice_participants:
        Captures who was present when recording started, even if they never talk.
        '''
        participants = []
        for member in voice_channel.members:
            if member.bot:
                continue
            handle = str(member)
            display_name = handle
            if member.display_name and member.display_name != member.name:
                display_name = f"{member.display_name} ({handle})"
            participants.append({
                "user_id": member.id,
                "display_name": display_name,
            })
        return participants

    def _start_synced_recording(self, vc, sink, channel):
        '''
        _start_synced_recording:
        Enables Pycord's shared recording zero point when the installed
        version exposes that option.
        '''
        kwargs = {}
        params = inspect.signature(vc.start_recording).parameters
        if "sync_start" not in params and "start_sync" not in params:
            self.bot.logger.warning(
                "start_recording has no sync_start/start_sync parameter; "
                "audio alignment will depend on the sink implementation."
            )

        sink.init(vc)
        callback = self._recording_finished_callback(sink, channel)
        vc.start_recording(
            sink,
            callback,
            **kwargs
        )

    def _recording_finished_callback(self, sink, channel):
        '''
        _recording_finished_callback:
        Bridges Pycord's receiver-thread callback back to the bot event loop.
        '''
        def callback(error):
            asyncio.run_coroutine_threadsafe(
                self.once_done(sink, channel, error),
                self.bot.loop
            )

        return callback
    
    @commands.slash_command(
        name="start", 
        description="Record in my current channel!"
        )
    async def start_recording(self, ctx):
        '''
        start_recording:
        Action to gather connections in cache and begin recording
        '''
        await ctx.defer()

        if ctx.guild is None:
            await ctx.respond("Recordings can only be started inside a server.")
            return

        voice = ctx.author.voice
        
        if not voice:
            await ctx.respond("You must be in a voice channel to start recording!")
            return

        if ctx.guild.id in self.sessions:
            await ctx.respond("I am already recording in this server.")
            return

        transcript_channel_id = self.bot.transcript_channel_id
        transcript_channel = (
            self.bot.get_channel(transcript_channel_id)
            if transcript_channel_id else None
        )

        if transcript_channel is None:
            await ctx.respond(
                "Please choose a transcript channel first with "
                "`/set_transcript_channel`."
            )
            return

        session_id = datetime.datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
        paths = self._session_paths(ctx.guild.id, session_id)
        os.makedirs(paths["raw_dir"], exist_ok=True)
        os.makedirs(paths["processed_dir"], exist_ok=True)
        started_at = datetime.datetime.utcnow().isoformat() + "Z"

        vc = None
        try:
            vc = await voice.channel.connect()
            session = {
                "vc": vc,
                "session_id": session_id,
                "session_root": paths["session_root"],
                "raw_dir": paths["raw_dir"],
                "processed_dir": paths["processed_dir"],
                "manifest_path": paths["manifest_path"],
                "manifest": {
                    "session_id": session_id,
                    "guild_id": ctx.guild.id,
                    "voice_channel_id": voice.channel.id,
                    "transcript_channel_id": transcript_channel.id,
                    "model_size_or_path": self.bot.model_size_or_path,
                    "started_at": started_at,
                    "stopped_at": None,
                    "participants": self._voice_participants(voice.channel),
                    "speakers": [],
                },
            }
            self.sessions[ctx.guild.id] = session
            self._write_manifest(session)

            self._start_synced_recording(
                vc,
                self._sink_for_session(ctx.guild.id, session_id),
                ctx.channel
            )
        except Exception as exc:
            self.sessions.pop(ctx.guild.id, None)
            if vc and vc.is_connected():
                await vc.disconnect()
            self.bot.logger.exception("Failed to start recording")
            await ctx.respond(f"Could not start recording: {exc}")
            return

        await ctx.respond(
            "Started recording with "
            f"`{self.bot.model_size_or_path}`. Transcript will be sent to "
            f"{transcript_channel.mention}."
        )
        
    @commands.slash_command(
        name="stop", 
        description="Stop the recording and leave!"
        )
    async def stop_recording(self, ctx):
        '''
        stop_recording:
        Action to stop recording in channel and begin callback
        '''
        await ctx.defer()

        if ctx.guild is None:
            await ctx.respond("Recordings can only be stopped inside a server.")
            return

        if ctx.guild.id in self.sessions:  # Check if the guild is in the cache
            vc = self.sessions[ctx.guild.id]["vc"]
            try:
                vc.stop_recording()  # Stop recording, and call once_done (callback)
            except Exception as exc:
                self.bot.logger.exception("Failed to stop recording")
                await ctx.respond(f"Could not stop recording: {exc}")
                return
            await ctx.respond("Stopped recording. I am processing the session now.")
        else:
            await ctx.respond("I am currently not recording here.")
    
    async def once_done(
            self, sink, channel: discord.TextChannel, error=None):
        '''
        once_done:
        Coroutine that runs when recording is stopped
        '''
        guild_id = getattr(sink, "sneaky_guild_id", None)
        session_id = getattr(sink, "sneaky_session_id", None)
        if guild_id is None or session_id is None:
            await channel.send("Recording finished, but the sink lost session metadata.")
            return

        session = self.sessions.pop(guild_id, None)
        if session is None or session["session_id"] != session_id:
            await channel.send("Recording finished, but I could not find session metadata.")
            return

        if error:
            self.bot.logger.error("Recording stopped with an error: %s", error)

        try:
            sink.cleanup()
        except Exception as exc:
            self.bot.logger.exception("Failed to finalize recorded audio")
            await channel.send(f"Recording stopped, but audio finalization failed: {exc}")
            return

        recorded_users = []
        ignored = {int(user_id) for user_id in self.bot.config['ignore_members']}
        session["manifest"]["stopped_at"] = (
            datetime.datetime.utcnow().isoformat() + "Z"
        )

        for user_id, audio, in sink.audio_data.items():
            user_id = int(user_id)
            if user_id not in ignored:
                display_name = await self._speaker_label(guild_id, user_id)
                recorded_users.append(display_name)
                safe_name = self._safe_name(display_name)
                extension = getattr(sink, "encoding", "wav")
                filename = f"{user_id}_{safe_name}.{extension}"
                filepath = os.path.join(session["raw_dir"], filename)

                with open(filepath, 'wb') as f:
                    f.write(audio.file.getbuffer())

                session["manifest"]["speakers"].append({
                    "user_id": user_id,
                    "display_name": display_name,
                    "audio_file": filename,
                    "transcript_file": f"{user_id}.txt",
                })

        self._write_manifest(session)

        vc = session["vc"]
        if vc.is_connected():
            await vc.disconnect()

        if recorded_users:
            await channel.send(("Finished! Recorded audio for "
                                f"{', '.join(recorded_users)}."))
        else:
            await channel.send("Finished, but no non-ignored speakers were recorded.")
            return

        # Call the transcription cog when the files are written.
        transcription = self.bot.get_cog('transcription')
        if transcription is None:
            await channel.send("Recording saved, but the transcription cog is not loaded.")
            return

        try:
            await transcription.process_session(session)
        except Exception as exc:
            self.bot.logger.exception("Failed to process recording session")
            await channel.send(f"Recording saved, but transcription failed: {exc}")

# this adds the cogs to bot
def setup(bot) -> None:
    bot.add_cog(Recording(bot))
