# sneaky-helper

Pycord bot for recording Discord voice channels and transcribing DnD sessions
with Faster Whisper.

## What it does

- Starts recording with `/start` from your current voice channel.
- Stops recording with `/stop`.
- Saves each recording session under `sessions/<guild id>/<session id>/`.
- Writes a `manifest.json` that maps each audio track to a Discord user id and
  display label.
- Keeps Pycord synchronized tracks aligned to the same session zero point.
- Sends the merged Markdown transcript to a configured Discord text channel.
- Lets you select the Whisper model from `config.json`, environment variables,
  or `/set_whisper_model`.

## Setup

Install system audio tools first. On macOS:

```sh
brew install ffmpeg opus
```

Create a virtual environment and install Python dependencies:

```sh
/opt/homebrew/bin/python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Create your local environment file:

```sh
cp .env.example .env
```

Set `TOKEN` in `.env` to your Discord bot token. For first tests, use a small
model such as `base` or `small` before moving back to `large-v2`.

## Config

`config.json` contains startup defaults:

- `model_size_or_path`: Faster Whisper model name or local model path. The
  default is `base` so first-run tests are quick on a 16 GB MacBook Pro.
- `device`: `cpu`, `cuda`, or `auto`.
- `compute_type`: Faster Whisper compute type. The default is `int8` for local
  CPU testing on macOS.
- `download_root`: local model cache directory.
- `local_files_only`: use only already-downloaded model files.
- `transcript_channel_id`: default transcript destination.
- `debug_guild_ids`: optional guild ids for faster slash-command registration
  while testing.

Environment overrides:

- `SNEAKY_WHISPER_MODEL`
- `SNEAKY_TRANSCRIPT_CHANNEL_ID`

## Run

```sh
source .venv/bin/activate
python main.py
```

## First Test

In Discord:

1. Run `/set_transcript_channel` and choose the transcript text channel.
2. Run `/set_whisper_model base`.
3. Join a voice channel with at least one other account.
4. Run `/start`.
5. Speak with intentional pauses and overlap.
6. Run `/stop`.
7. Check the transcript channel and the matching `sessions/` folder.

## Notes

This project intentionally pins Pycord 2.4.1 for the initial voice-recording
test path. Newer Pycord docs warn that voice receive behavior is affected by
Discord's DAVE voice encryption changes, so test this path before investing in
more transcription polish.
