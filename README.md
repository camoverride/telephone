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


## TODO's

- [ ] set up additional ASR models (whisper)
- [ ] set up additional response models (Markov)
- [ ] set up additional TTS models (???)
- [ ] set up level-press GPIO start (with exeternal pull up/down resistor?)
- [ ] suppress annying vox logs
- [ ] remove ephemeral files to allow Read-Only FS
