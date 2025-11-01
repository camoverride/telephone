import base64
import datetime
import os
import random
from typing import Union
import wave



def get_random_file(folder_path : str) -> str:
    """
    Returns a randomly selected file path from the given folder.

    Parameters
    ----------
    folder_path : str
        Path to the folder containing files.

    Returns
    -------
    str
        Full path to a randomly selected file.
    """
    files = [f for f in os.listdir(folder_path) if \
             os.path.isfile(os.path.join(folder_path, f))]

    return os.path.join(folder_path, random.choice(files))


def save_audio(
    audio_file: Union[str, bytes],  # Can be base64 string or raw bytes
    save_folder: str,
    channels: int = 1,
    sampwidth: int = 2,
    framerate: int = 16000
) -> str:
    """
    Save audio data to a WAV file.

    Parameters
    ----------
    audio_file : str | bytes
        Audio data to save. If a string, it should be base64-encoded WAV bytes.
    save_folder : str
        Folder path where the WAV file will be saved. Will be created if it doesn't exist.
    channels : int, optional
        Number of audio channels (default is 1, mono).
    sampwidth : int, optional
        Sample width in bytes (default is 2 bytes = 16-bit audio).
    framerate : int, optional
        Sampling rate in Hz (default is 16000).

    Returns
    -------
    str
        The full path to the saved WAV file.
    """
    # Ensure save folder exists
    os.makedirs(save_folder, exist_ok=True)

    # Build filename with timestamp
    filename = os.path.join(
        save_folder, f"recording_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.wav"
    )

    # If input is base64 string, decode it
    if isinstance(audio_file, str):
        audio_bytes = base64.b64decode(audio_file)
    else:
        audio_bytes = audio_file

    # Write WAV file
    with wave.open(filename, "wb") as wf:
        wf.setnchannels(channels)
        wf.setsampwidth(sampwidth)
        wf.setframerate(framerate)
        wf.writeframes(audio_bytes)

    return filename
