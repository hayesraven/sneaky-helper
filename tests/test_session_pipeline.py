import os
import sys
import tempfile
import types
import unittest
from io import BytesIO
from unittest import mock


def install_dependency_stubs():
    discord = types.ModuleType("discord")

    class File:
        def __init__(self, fp, filename=None):
            self.fp = fp
            self.filename = filename

    class Intents:
        @classmethod
        def default(cls):
            return cls()

    discord.File = File
    discord.Intents = Intents
    discord.TextChannel = object
    discord.User = object
    discord.__version__ = "test"
    discord.opus = types.SimpleNamespace(
        Decoder=types.SimpleNamespace(
            CHANNELS=2,
            SAMPLE_SIZE=4,
            SAMPLING_RATE=48000,
        )
    )

    class AudioData:
        def __init__(self):
            self.file = BytesIO()
            self.finished = False

        def write(self, data):
            self.file.write(data)

        def cleanup(self):
            self.file.seek(0)
            self.finished = True

        def on_format(self, encoding):
            if not self.finished:
                raise RuntimeError("AudioData is still writing")

    class WaveSinkError(Exception):
        pass

    class WaveSink:
        def __init__(self):
            self.encoding = "wav"
            self.vc = None
            self.audio_data = {}

        def init(self, vc):
            self.vc = vc

        def write(self, data, user):
            self.audio_data.setdefault(user, AudioData()).write(data)

        def cleanup(self):
            for audio in self.audio_data.values():
                audio.cleanup()
                self.format_audio(audio)

    discord.sinks = types.SimpleNamespace(
        WaveSink=WaveSink,
        WaveSinkError=WaveSinkError,
    )

    ext = types.ModuleType("discord.ext")
    commands = types.ModuleType("discord.ext.commands")

    class Bot:
        def __init__(self, *args, **kwargs):
            self.args = args
            self.kwargs = kwargs

    class Cog:
        def __init_subclass__(cls, **kwargs):
            super().__init_subclass__()

    def slash_command(*args, **kwargs):
        def decorator(func):
            return func
        return decorator

    commands.Bot = Bot
    commands.Cog = Cog
    commands.slash_command = slash_command
    ext.commands = commands
    discord.ext = ext

    faster_whisper = types.ModuleType("faster_whisper")

    class WhisperModel:
        pass

    faster_whisper.WhisperModel = WhisperModel

    pydub = types.ModuleType("pydub")
    pydub.AudioSegment = types.SimpleNamespace()

    sys.modules.setdefault("discord", discord)
    sys.modules.setdefault("discord.ext", ext)
    sys.modules.setdefault("discord.ext.commands", commands)
    sys.modules.setdefault("faster_whisper", faster_whisper)
    sys.modules.setdefault("pydub", pydub)


install_dependency_stubs()

import SneakyBot
from cogs.recording import SneakyWaveSink
from cogs.transcription import Transcription


class SneakyBotConfigTests(unittest.TestCase):
    def test_config_defaults_and_startup_model_override(self):
        config = {
            "prefix": "Sneaky",
            "ignore_members": [],
        }

        with mock.patch.dict(os.environ, {"SNEAKY_WHISPER_MODEL": "base"}):
            bot = SneakyBot.SneakyBot(config)

        self.assertEqual(bot.model_size_or_path, "base")
        self.assertIsNone(bot.transcript_channel_id)
        self.assertEqual(bot.config["debug_guild_ids"], [])
        self.assertEqual(bot.kwargs["command_prefix"], "Sneaky")


class TranscriptMergeTests(unittest.TestCase):
    def test_merge_session_uses_manifest_speakers_and_sorts_by_timestamp(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            processed_dir = os.path.join(tmpdir, "processed")
            os.makedirs(processed_dir)

            with open(os.path.join(processed_dir, "111.txt"), "w") as f:
                f.write("[2.000s] Later line\n")

            with open(os.path.join(processed_dir, "222.txt"), "w") as f:
                f.write("[0.500s] Earlier line\n")

            session = {
                "session_id": "session-1",
                "processed_dir": processed_dir,
                "manifest": {
                    "model_size_or_path": "base",
                    "started_at": "2026-09-18T00:00:00Z",
                    "stopped_at": "2026-09-18T01:00:00Z",
                    "participants": [
                        {"user_id": 111, "display_name": "Raven"},
                        {"user_id": 222, "display_name": "Hayes"},
                    ],
                    "speakers": [
                        {
                            "user_id": 111,
                            "display_name": "Raven",
                            "transcript_file": "111.txt",
                        },
                        {
                            "user_id": 222,
                            "display_name": "Hayes",
                            "transcript_file": "222.txt",
                        },
                    ]
                },
            }

            final_path = Transcription(bot=types.SimpleNamespace()).merge_session(
                session
            )

            with open(final_path) as f:
                final = f.read()

        self.assertEqual(
            final,
            "# Sneaky Helper Transcript: session-1\n\n"
            "- Model: `base`\n"
            "- Started: `2026-09-18T00:00:00Z`\n"
            "- Stopped: `2026-09-18T01:00:00Z`\n\n"
            "## Voice Channel Participants\n\n"
            "- Raven\n"
            "- Hayes\n\n"
            "## Transcript\n\n"
            "- [0.500s] **Hayes:** Earlier line\n"
            "- [2.000s] **Raven:** Later line\n"
        )


class RecordingSinkTests(unittest.TestCase):
    def test_sneaky_wave_sink_accepts_voice_data_and_formats_wav(self):
        sink = SneakyWaveSink()
        sink.init(types.SimpleNamespace(is_recording=lambda: False))

        sink.write(types.SimpleNamespace(pcm=b"\x00\x00" * 960), 123)
        sink.cleanup()

        self.assertTrue(hasattr(sink, "__sink_listeners__"))
        self.assertEqual(list(sink.walk_children()), [])
        self.assertEqual(sink.encoding, "wav")
        self.assertIn(123, sink.audio_data)
        self.assertGreater(len(sink.audio_data[123].file.getvalue()), 44)


if __name__ == "__main__":
    unittest.main()
