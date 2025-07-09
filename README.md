# Telephone ☎️ 

Code and setup guide for an interactive rotary telephone.


## Materials & Assembly Guide

See [the wiki](https://github.com/camoverride/telephone/wiki)


## Setup

- `git clone git@github.com:camoverride/telephone.git`
- `cd telephone`

If MacOS:

- `pip install -r requirements_macos.txt`
- `python3 -m venv .venv`
- `source .venv/bin/activate`

If Raspberry Pi:

- `python3 -m venv .venv --system-site-packages`
- `source .venv/bin/activate`
- `sudo apt-get update`
- `sudo apt-get install -y portaudio19-dev`
- `pip install -r requirements_pi.txt`


Get vosk model:

- `wget https://alphacephei.com/vosk/models/vosk-model-small-en-us-0.15.zip`
- `unzip vosk-model-small-en-us-0.15.zip`
- `mv vosk-model-small-en-us-0.15 models/vosk-model-small-en-us-0.15`

Create markov models:

- `cd models/markov`
- `python _train_markov_model.py`
- `cd ../..`

If using the deepseek model, you must have your API key inside a single-line file named `deepseek_api_key.txt`

If using the vector_quotes model, first download the quotes spreadsheet as an Excel file names `quotes.xlsx` - it should have two columns: `author` and `quote`. Then run `create_embeddings_db.py` to generate `quote_embeddings.db`.


## Test

- `python run_chatbot.py 2>/dev/null`


## Run in Production

Start a service with *systemd*. This will start the program when the computer starts and revive it when it dies. It expects that the username is `pi`:

- `mkdir -p ~/.config/systemd/user`
- `cat telephone.service > ~/.config/systemd/user/telephone.service`

Start the service using the commands below:

- `systemctl --user daemon-reload`
- `systemctl --user enable telephone.service`
- `systemctl --user start telephone.service`

Start it on boot:

- `sudo loginctl enable-linger pi`

Get the status:

- `systemctl --user status telephone.service`


Get the logs:

- `journalctl --user -u telephone.service`


## Increase System Longevity

Follow these steps in order:

- Install tailscale for remote access and debugging.
- Configure backup wifi networks.
- Set up periodic reboots (cron job)


## Notes & Todo's

- ASR: Vosk seems adequte, as people are speaking very close to the mic.
- Response: `vector_quotes` and `deepseek` work well.
- TTS: I like the google voice model.


Important:

- [X] set up additional response models (conditioned markov, llama, tiny-llama [local])
- [ ] add better instructions
- [ ] make haiku continue printing even if hung up
- [ ] add gong sound while waiting
- [ ] set up additional synthesis model (piper-tts)
- [ ] stop speech synthesis if phone is hung up (see `utils.py: play_audio_interruptible`)
- [ ] more elegant beginning prompt
- [ ] deepseek chat mode (with memory)

Less important:

- [ ] reject ASR if it doesn't meet a confidence level.
- [ ] convert `print` to `logging`
- [ ] suppress annying vox logs (only relevant for local testing, these are not logged)
- [ ] remove ephemeral files to allow Read-Only FS
- [ ] vosk model seems to work fine, but potentially set up Whisper too.
- [ ] generic longevity tips
- [ ] double check requirements
