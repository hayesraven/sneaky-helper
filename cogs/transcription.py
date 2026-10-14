from discord.ext import commands
import discord
import faster_whisper
import logging
import os
import pydub
import re


class Transcription(commands.Cog, name="transcription"):
    def __init__(self, bot) -> None:
        '''
        Constructor
        '''
        self.bot = bot
        self.logger = logging.getLogger(__name__)
        logging.basicConfig(level=logging.DEBUG)

    async def process_session(self, session: dict):
        '''
        process_session:
        Transcribes, merges, and sends a single completed recording session.
        '''
        final_path = await self.bot.loop.run_in_executor(
            None, self.transcribe_session, session
        )
        await self.send_file(session, final_path)

    def _load_audio(self, filepath: str):
        '''
        _load_audio:
        Lets pydub infer the actual container written by the sink.
        '''
        return pydub.AudioSegment.from_file(filepath)

    def align_audio_tracks(self, session: dict) -> None:
        '''
        align_audio_tracks:
        Pads shorter synchronized tracks at the end so timestamps keep the same
        session zero point.
        '''
        speakers = session["manifest"]["speakers"]
        if len(speakers) < 2:
            return

        loaded_tracks = []
        max_duration = 0

        for speaker in speakers:
            filepath = os.path.join(session["raw_dir"], speaker["audio_file"])
            audio = self._load_audio(filepath)
            duration = len(audio)
            loaded_tracks.append((speaker, filepath, audio, duration))
            max_duration = max(max_duration, duration)

        for speaker, filepath, audio, duration in loaded_tracks:
            if duration >= max_duration:
                continue

            padding = pydub.AudioSegment.silent(duration=max_duration - duration)
            padded = audio + padding
            extension = os.path.splitext(speaker["audio_file"])[1].lstrip(".")
            padded.export(filepath, format=extension)

    def transcribe_session(self, session: dict) -> str:
        '''
        transcribe_session:
        Handles transcription and transcript merging for one session.
        '''
        self.logger.info("Now transcribing session %s", session["session_id"])
        os.makedirs(session["processed_dir"], exist_ok=True)
        self.align_audio_tracks(session)

        model = faster_whisper.WhisperModel(
            model_size_or_path=session["manifest"]["model_size_or_path"],
            device=self.bot.device,
            compute_type=self.bot.compute_type,
            download_root=self.bot.download_root,
            local_files_only=self.bot.local_files_only
        )

        for speaker in session["manifest"]["speakers"]:
            audio_path = os.path.join(session["raw_dir"], speaker["audio_file"])
            transcript_path = os.path.join(
                session["processed_dir"], speaker["transcript_file"]
            )
            segments, info = model.transcribe(
                audio_path,
                language="en",
                condition_on_previous_text=False,
                word_timestamps=True,
                vad_filter=True
            )
            self.logger.info(
                "Detected language '%s' with probability %s",
                info.language,
                info.language_probability
            )

            with open(transcript_path, 'w') as f:
                for segment in segments:
                    line = "[%.3fs] %s\n" % (segment.start, segment.text)
                    f.write(line)

        return self.merge_session(session)

    def merge_session(self, session: dict) -> str:
        '''
        merge_session:
        Merges per-speaker transcripts using manifest speaker metadata.
        '''
        lines = []
        reg_transcript = (
            r'^\[(?P<time_float>[0-9]+(?:\.[0-9]+)?)s\]\s+'
            r'(?P<string>.+)$'
        )

        for speaker in session["manifest"]["speakers"]:
            transcript_path = os.path.join(
                session["processed_dir"], speaker["transcript_file"]
            )
            if not os.path.exists(transcript_path):
                continue

            with open(transcript_path, 'rb') as f:
                data = f.read().decode(errors='ignore')

            for line in data.splitlines():
                match_script = re.match(reg_transcript, line)

                if match_script is not None:
                    timestamp = float(match_script.group('time_float'))
                    lines.append({
                        'time_float': timestamp,
                        'string':
                            "- [%.3fs] " % timestamp +
                            "**" + speaker["display_name"] + ':** ' +
                            match_script.group('string').strip() + "\n"
                    })

        final = sorted(lines, key=lambda d: d['time_float'])
        final_path = os.path.join(
            session["processed_dir"], f"{session['session_id']}_transcript.md"
        )
        os.makedirs(session["processed_dir"], exist_ok=True)

        with open(final_path, 'w') as f:
            f.write(f"# Sneaky Helper Transcript: {session['session_id']}\n\n")
            f.write(f"- Model: `{session['manifest']['model_size_or_path']}`\n")
            f.write(f"- Started: `{session['manifest']['started_at']}`\n")
            f.write(f"- Stopped: `{session['manifest']['stopped_at']}`\n\n")

            participants = session["manifest"].get("participants", [])
            if participants:
                f.write("## Voice Channel Participants\n\n")
                for participant in participants:
                    f.write(f"- {participant['display_name']}\n")
                f.write("\n")

            f.write("## Transcript\n\n")
            for line in final:
                f.write(line['string'])

        return final_path

    async def send_file(self, session: dict, final_path: str):
        '''
        send_file:
        Sends the final transcript for this session to the configured channel.
        '''
        channel_id = session["manifest"].get("transcript_channel_id")
        channel = self.bot.get_channel(channel_id) if channel_id else None

        if channel is None:
            self.logger.error("ERROR: transcript channel cannot be found!")
            return

        with open(final_path, 'rb') as f:
            file = discord.File(f, filename=os.path.basename(final_path))
            await channel.send(file=file)


# this adds the cogs to bot
def setup(bot) -> None:
    bot.add_cog(Transcription(bot))
