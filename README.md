# sneaky-helper
Discord.py bot leveraging Whisper AI for transcription of voice chats

## To build sneaky-helper wheel

Create and activate a virtual environment.

```sh
$(realpath `which python3`) -m venv .venv
source .venv/bin/activate
```

Install dependencies and build the wheel.

```sh
pip install -e .[build,test]
python -m build
```

Install the wheel and run it.

```sh
# uncomment if reinstalling for testing
# pip install --force-reinstall dist/*.whl

pip install dist/*.whl
sneaky-helper
```
