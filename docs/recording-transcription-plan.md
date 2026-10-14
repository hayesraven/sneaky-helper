# Recording and Transcription Plan

## Goals

- Start recording when `/start` is called from a Discord voice channel.
- Stop recording when `/stop` is called and send the transcript to the configured text channel.
- Keep each recorded audio track associated with the Discord speaker that produced it.
- Keep per-speaker tracks aligned to a shared session zero.
- Allow the Whisper model to be selected at startup and changed at runtime.

## Recording Session

Each recording creates a session id based on UTC time. Raw audio, transcript
files, and metadata are stored under that session. This prevents old recordings
from being retranscribed or merged into the next session.

The session manifest stores:

- guild id
- voice channel id
- text channel id for transcript delivery
- selected Whisper model
- UTC start/stop timestamps
- one entry per speaker with Discord user id, display label, and audio file

## Audio Alignment

Pycord's synchronized recording mode is the alignment source. When that mode is
enabled, each user track should share the same zero point, including silence
before a speaker first talks. After export, shorter tracks can be padded at the
end so all files share the same duration without moving speech later.

The previous approach prepended silence to shorter files. That made the shortest
or least-active speakers appear to speak later than they did, which explains the
manual Audyssey alignment work.

## Speaker Attribution

Speaker attribution should come from Discord metadata captured at recording time,
not from filenames. Filenames may contain sanitized labels for convenience, but
transcript merging should read the manifest and use stable Discord user ids.

## Commands

- `/start`: join the caller's current voice channel and start one recording
  session for the guild.
- `/stop`: stop the active session, disconnect, transcribe, merge to Markdown,
  and send.
- `/set_transcript_channel`: persist the channel where final transcripts are
  posted.
- `/show_transcript_channel`: display the configured transcript channel.
- `/set_whisper_model`: persist and activate the Whisper model.
- `/show_whisper_model`: display the active Whisper model and runtime settings.
- Existing ignore/listen/list commands continue to control which users are
  excluded from recording/transcription.

## Verification

Local tests should cover pure logic where possible: config updates, manifest
speaker lookup, transcript merge ordering, and audio alignment direction. Live
Discord testing is still needed for Pycord voice receive behavior and callback
signatures.
