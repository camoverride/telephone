import base64
from flask import jsonify, Response
from flask_restful import Resource
import io
import logging
import numpy as np
import platform
import requests
import select
from sentence_transformers import SentenceTransformer
import subprocess
import sys
import threading
import time
from typing import Optional
import wave



# Set up logging configuration
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s')


# Read all the banned words into a list.
BANNED_WORDS: Optional[list[str]] = None
try:
    with open("banned_words.txt", "r") as f:
        BANNED_WORDS = [line.rstrip('\n') for line in f]
except FileNotFoundError:
    logging.warning("WARNING: no './banned_words.txt' file - please create one!")


# System-dependent import. Get The GPIO pins on Raspbian.
# Check for Raspbian specifically, and not just any Linux system.
if platform.system() == "Linux":
    try:
        with open("/etc/os-release") as f:
            os_info = f.read().lower()
            if "raspbian" in os_info:
                from gpiozero import Button  # type: ignore
                # GPIO 17 with 50ms debounce time.
                button = Button(17, bounce_time=0.05)
            else:
                logging.warning("Not running on Raspbian, skipping GPIO setup.")
    except FileNotFoundError:
        logging.warning("Could not read /etc/os-release to check \
                         for Raspbian. Skipping GPIO setup.")
    from gpiozero import Button # type: ignore


# Load the model once at module level for efficiency
_embedding_model = SentenceTransformer('all-MiniLM-L6-v2')


class PhonePutDownError(Exception):
    """
    Exception raised when the phone is put down.
    """
    def __init__(self, message="Phone put down"):
        super().__init__(message)


def phone_picked_up() -> bool:
    """
    Returns True if the phone is picked up, otherwise False.

    Imports `button` from RPi's gpiozero library.

    NOTE: when the phone is picked up, the circuit is completed.
    When the phone is placed down, the circuit disconnects.

    Returns
    -------
    bool
        True
            The phone is picked up.
            NOTE: also always True if testing on MacOS
        False
            The phone is placed down.
    """
    if platform.system() == "Darwin":
        # Wait max 0.1 seconds for input
        i, _, _ = select.select([sys.stdin], [], [], 0.1)

        if i:
            user_input = sys.stdin.readline().strip()
            if user_input.lower() == "q":

                # Should raise a custom error!
                # raise PhonePutDownError
                return False

        return True

    elif platform.system() == "Linux":
        if button.is_pressed:
            return True
        
        else:
            # raise PhonePutDownError
            return False

    # If it's some other system, return True.
    else:
        return True


def ignored_phrases(text : str) -> bool:
    """
    Returns True if the text should be ignored and bypassed.

    Parameters
    ----------
    text : str
        Some text that may contain stuff we don't want.

    Returns
    -------
    bool
        True if the input is a simple greeting, a filler word, or
        contains profanity. Otherwise False.
    """
    # If there are no banned words, just return False.
    if not BANNED_WORDS:
        return False

    # Check whether the entire input is bad, like a greeting.
    if text.lower() in ("huh", "hi", "hello", "sup",
                        "what's up", "greetings", "hi there",
                        "hello there"):
        return True

    # Check whether the input is a filler word.
    if (not text) or text.lower() in ("", " ", "huh", "what", "um"):
        return True

    # Check if there are banned words in the input.
    if BANNED_WORDS:
        if any(word in text.lower() for word in BANNED_WORDS):
            return True

    return False


def print_text(
    text : str,
    printer_api: str) -> None:
    """
    Sends some text to a thermal printer to be printed out.

    Parameters
    ----------
    text : str
        Some text to be printed
    printer_api : str
        The endpoint.

    Returns
    -------
    None
        Prints text.
    """
    logging.info(f"Printing this: {text}")
    data = {"text": text}

    response = requests.post(
        printer_api,
        json=data,
        timeout=(1.0, 10.0)) # (connect_timeout, read_timeout)

    logging.debug(response.json())


class play_audio:
    """
    A cross-platform audio playback class with support for delayed
    start, looping, blocking or non-blocking playback, and conditional
    termination based on an external condition (e.g. phone being put down).

    Supports:
    - macOS (via `afplay`)
    - Linux (Ubuntu, Raspbian) via `ffplay`

    Example usage (non-blocking looped audio with kill-switch):

        audio = play_audio("sound.wav",
                           looping=True,
                           blocking=False,
                           killable=True)
        audio.start()
        ...
        audio.stop()  # To stop playback manually

    Parameters
    ----------
    filepath : str
        Path to the audio file (.wav, .mp3, etc.)
    start_delay : int, optional
        Delay (in seconds) before audio playback starts. Default is 0.
    looping : bool, optional
        If True, the audio file will loop indefinitely. Default is False.
    blocking : bool, optional
        If True, the call to `.start()` will block until playback finishes. 
        If False, playback runs in a background thread. Default is True.
    killable : bool, optional
        If True, playback will stop automatically 
        if `phone_picked_up()` returns False. 
        Default is False.
    """
    def __init__(
        self,
        filepath: str,
        start_delay: int,
        looping: bool,
        blocking: bool,
        killable: bool):

        self.filepath = filepath
        self.start_delay = start_delay
        self.looping = looping
        self.blocking = blocking
        self.killable = killable

        # Active audio subprocess.
        self.process: Optional[subprocess.Popen] = None
        # (Unused currently).
        self._kill_thread: Optional[threading.Thread] = None
        # Used to manually break out of afplay loops (macOS).
        self._looping = True

    def _build_command(self) -> list[str]:
        """
        Constructs the appropriate playback command depending
        on the platform.

        Returns
        -------
        list[str]
            Command list to be passed to subprocess.
        """
        if platform.system() == "Darwin":
            # No native loop--handled in Python.
            return ["afplay", self.filepath]

        elif platform.system() == "Linux":
            base_cmd = ["ffplay", "-nodisp", "-loglevel", "quiet"]
            if self.looping:
                base_cmd += ["-loop", "0"] # Infinite loop.
            else:
                base_cmd += ["-autoexit"] # Exit after playing once.
            return base_cmd + [self.filepath]

        else:
            raise RuntimeError("Unsupported OS for audio playback")

    def _monitor_kill_switch(self):
        """
        Thread that monitors phone state and stops playback
        if `phone_picked_up()` returns False.

        (Used only in non-blocking Linux mode.)
        """
        while self.process and self.process.poll() is None:
            if not phone_picked_up():
                raise PhonePutDownError
                logging.info("Phone put down — terminating audio.")
                self.stop()
                break
            time.sleep(0.1)

    def start(self) -> None:
        if self.start_delay > 0:
            time.sleep(self.start_delay)

        self._looping = True

        def play_loop():
            while self._looping:
                if self.killable and not phone_picked_up():
                    raise PhonePutDownError
                    logging.info("Phone put down — terminating audio.")
                    self.stop()
                    break

                command = self._build_command()
                self.process = subprocess.Popen(
                    command,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )

                if self.blocking:
                    # Poll subprocess and phone state in a tight loop for killability
                    while True:
                        if self.process.poll() is not None:
                            # Playback finished naturally
                            break
                        if self.killable and not phone_picked_up():
                            raise PhonePutDownError
                            logging.info("Phone put down — terminating audio during playback.")
                            self.stop()
                            break
                        time.sleep(0.1)

                    if not self.looping or not self._looping:
                        break

                else:
                    # Non-blocking, just start process and return (kill monitor elsewhere)
                    self.process.wait()
                    if not self.looping or not self._looping:
                        break

        if self.blocking:
            play_loop()
        else:
            thread = threading.Thread(target=play_loop, daemon=True)
            thread.start()



    def stop(self) -> None:
        """
        Terminates any active playback process and exits the loop.
        Safe to call even if no playback is active.
        """
        # Stops loop even on macOS.
        self._looping = False

        if self.process and self.process.poll() is None:
            self.process.terminate()
            self.process.wait()
        self.process = None

    def is_playing(self) -> bool:
        """
        Returns whether audio is currently playing.

        Returns
        -------
        bool
            True if an audio process is running, False otherwise.
        """
        return (self.process is not None) and (self.process.poll() is None)


def create_embedding(text: str) -> np.ndarray:
    """
    Create a sentence embedding from text using SentenceTransformer.

    Parameters
    ----------
    text : str
        Input text to embed.

    Returns
    -------
    np.ndarray
        Vector embedding of the input text.
    """
    embedding = _embedding_model.encode(text)

    return np.ndarray(embedding)  # type: ignore


def encode_audio_to_base64(audio: np.ndarray, sample_rate: int = 16000) -> str:
    """
    Encodes the recorded audio as WAV file and converts it to base64 string.

    Parameters:
    ----------
    audio : np.ndarray
        The recorded audio data (int16).
    sample_rate : int
        The sampling rate (default 16000 Hz).

    Returns:
    -------
    str
        Base64-encoded audio string.
    """
    # Convert numpy array to WAV format.
    with io.BytesIO() as audio_io:
        with wave.open(audio_io, 'wb') as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)  # 16-bit PCM
            wav_file.setframerate(sample_rate)
            wav_file.writeframes(audio.tobytes())

        audio_b64 = base64.b64encode(audio_io.getvalue()).decode('utf-8')

        return audio_b64


class HealthCheckAPI(Resource):
    """
    Simple health check API to monitor the server status.
    """

    def get(self) -> Response:
        # For example, we can return the system uptime and status.
        uptime = subprocess.check_output(["uptime", "-p"]).decode('utf-8')
        return jsonify({"status": "ok", "uptime": uptime.strip()})
