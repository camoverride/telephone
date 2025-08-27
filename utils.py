import base64
from flask import jsonify, Response
from flask_restful import Resource
import io
import logging
import numpy as np
import requests
from sentence_transformers import SentenceTransformer
import subprocess
from typing import Optional
import wave



# Set up logging configuration.
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


# Load the model once at module level for efficiency
_embedding_model = SentenceTransformer('all-MiniLM-L6-v2')


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
    data = {"text": text}

    response = requests.post(
        printer_api,
        json=data,
        timeout=(1.0, 10.0)) # (connect_timeout, read_timeout)


def create_embedding(text : str) -> np.ndarray:
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

    return embedding  # type: ignore


def encode_audio_to_base64(
    audio : np.ndarray,
    sample_rate : int = 16000) -> str:
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


def decode_base64_wav_to_np(audio_b64 : str) -> np.ndarray:
    """
    
    """
    audio_bytes = base64.b64decode(audio_b64)
    with wave.open(io.BytesIO(audio_bytes), 'rb') as wav_file:
        n_channels = wav_file.getnchannels()
        sample_width = wav_file.getsampwidth()
        n_frames = wav_file.getnframes()
        raw_data = wav_file.readframes(n_frames)
        # Assuming 16-bit PCM
        audio_np = np.frombuffer(raw_data, dtype=np.int16)
        if n_channels > 1:
            # Convert to mono by averaging channels
            audio_np = audio_np.reshape(-1, n_channels).mean(axis=1).astype(np.int16)
    return audio_np
