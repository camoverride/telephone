# Telephone ☎️ 

The code for an interactive rotary telephone chatbot by [Cam Smith](https://smith.cam/).


## Overview

This project allows configuration of several different parts


### Configuration

Which hardware this is configured on:

- *phone*: A custom rotary telephone described in the wiki that detects phone pick-up and put-down.
- *standard*: A computer with a mic and speaker attached.


### Chat Mode

The overall conversation mode:

- *echo*: repeats back whataver is heard.
- *translate*: translates whatever is heard into a specified. language.
- *chat*: returns a reply based on previous replies, chat format.


### Voice

Which text-to-speech (TTS) voice model should be used:

- *google-tts*: google's TTS model, (requires an internet connection).
- *terminal*: uses whichever local TTS software is on your machine (e.g. `say` on MacOS).
- *jeff*: custom voice model based off Jeff Bezos.
- *cam*: custom voice model based off the artist, Cam Smith.


### Personality

When using the *chat* mode, which personality will the agent have:

- *deepseek-memoryless*: A one-off reply from the deepseek API, with no memory of previous chats.
- *deepseek-remember*: A reply from the deepseek API, with a memory of previous chats.
- *tinyllama-memoryless*: A reply from a locally configured tiny-llama API endpoint.
- *markov*: A word-salad reply from a random markov model conditioned on Wikipedia text.


### Sounds

The sounds that are played at different points during the user interaction, saved in `prompts`:

- *start-prompt*: the audio played at the beginning of an interaction (`prompts/1_start_prompt`).
- *start-reply*: the audio played to indicate the end of *start-prompt* and beginning of *waiting-for-user-input* (`prompts/2_start_reply`).
- *waiting-for-user-input*: the audio played while waiting for user input (`prompts/3_waiting_for_user_input`).
- *thinking* : the audio played while waiting to generate a reply (`prompts/4_thinking`).
- *end-prompt*: the audio played at the end of an interaction (`prompts/5_end_prompt`).


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
- Set up periodic reboots (cron job).


## Licence

License: Non-Commercial MIT-style license. See `LICENSE` for details.
