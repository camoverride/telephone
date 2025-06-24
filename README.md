# Telephone ☎️ 

Code and setup guide for an interactive rotary telephone.


## Materials & Assembly Guide

See [the wiki](https://github.com/camoverride/telephone/wiki)


## Setup

- `git clone git@github.com:camoverride/telephone.git`
- `cd telephone`
- `python3 -m venv .venv`
- `source .venv/bin/activate`
- `pip install -r requirements.txt`

Get vosk model:

- `wget https://alphacephei.com/vosk/models/vosk-model-small-en-us-0.15.zip`
- `unzip vosk-model-small-en-us-0.15.zip`
- `mv vosk-model-small-en-us-0.15 models/vosk-model-small-en-us-0.15`

Create markov models:

- `cd models/markov`
- `python _train_markov_model.py`


## Test

- `python local_bot.py`


## Run in Production

Start a service with *systemd*. This will start the program when the computer starts and revive it when it dies. It expects that the username is `pi`:

- `mkdir -p ~/.config/systemd/user`
- `cat display.service > ~/.config/systemd/user/display.service`

Start the service using the commands below:

- `systemctl --user daemon-reload`
- `systemctl --user enable display.service`
- `systemctl --user start display.service`

Start it on boot: `sudo loginctl enable-linger pi`

Get the logs: `journalctl --user -u display.service`


## Increase System Longevity

Follow these steps in order:

- Install tailscale for remote access and debugging.
- Configure backup wifi networks.
- Set up periodic reboots (cron job)


## Notes & Todo's

- ASR: Vosk seems adequte, as people are speaking very close to the mic.
- TTS: I like the google voice model.
- Response: tiny-llama should be OK!


Important:

- [ ] set up additional response models (conditioned markov, llama, tiny-llama [local])
- [ ] set up additional synthesis model (piper-tts)
- [ ] set up lever-press GPIO start (with exeternal pull up/down resistor?)
- [ ] research [this repo](https://github.com/heristop/gutenku) for haiku model

Less important:

- [ ] suppress annying vox logs
- [ ] remove ephemeral files to allow Read-Only FS
- [ ] vosk model seems to work fine, but potentially set up Whisper too.
- [ ] google works fine, but potentially set up additional TTS models
