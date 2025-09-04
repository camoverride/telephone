# Telephone ☎️ 

The code for an interactive rotary telephone chatbot by [Cam Smith](https://smith.cam/telephone.html).


## Overview

This project allows configuration of several different parts of the chatbot pipeline.
You can see more in `config.yaml`:

- *Recording parameters* change how audio is picked up and recorded.
- *ASR parameters* change how audio is converted into input text.
- *Response parameters* change how a reply is made in response to the input text.
- *TTS parameters* change how the reply is spoken.

See [the wiki](https://github.com/camoverride/telephone/wiki/Settings) for more info.


## Materials & Assembly Guide

See [the wiki](https://github.com/camoverride/telephone/wiki).


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

First run all the servers in different processed (command line interfaces):

- `python _silero_vad.py`
- `python _speech_to_text.py`
- `python _response.py`
- `python _text_to_speech.py`

Then run the chatbot:

- `python run_chatbot.py`

To simulate the phone being put down, press **'q'** + **ENTER**.


## Run in Production

Start a service with *systemd*. This will start the program when the computer starts and revive it when it dies. It expects that the username is `pi`:

- `mkdir -p ~/.config/systemd/user`
- `cat services/telephone.service > ~/.config/systemd/user/telephone.service`

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

This depends on 4 servers: `vad`, `asr`, `response`, and `tts`.

- `cat services/<server>.service > ~/.config/systemd/user/<server>.service`
- `systemctl --user daemon-reload`
- `systemctl --user enable <server>.service`
- `systemctl --user start <server>.service`


## Licence

License: Non-Commercial MIT-style license. See `LICENSE` for details.
