import base64
import datetime
import os
import random
from typing import Union, List
import wave



def get_audio_file_paths_open_call(base_dir : str) -> List[str]:
    """
    Randomly selects a sub-folder from `base_dir` and returns the
    full paths to the "intro file" and "music file" from this
    directory. The "intro file" starts with "intro" and the music
    file is the other file. Folders should contain only these two
    files, both wavs. If these files don't exist or there are
    additional files, this function throws an error.

    Example:
        For a directory like this:

        base_dir
            Bailey_Audio
                intro.wav
                my_music_file.wav
            Samantha_Stuff
                intro_file.wav
                Song_About_Birds.wav
        
        One of the following two would be returned:
            ["base_dir/Bailey_Audio/intro.wav", "base_dir/Bailey_Audio/intro.wav"]
            ["base_dir/Samantha_Stuff/intro_file.wav", "base_dir/Samantha_Stuff/Song_About_Birds.wav"]
    
    Parameters
    ----------
    base_dir
        A directory containing one or more sub-folders, each of
        which contains an intro file and an audio file.

    Returns
    -------
    List[str]
        A list of length two, containing full paths from the base_dir
        to the two audio files, with the intro file first:
            ["base_dir/Bailey_Audio/intro.wav", "base_dir/Bailey_Audio/intro.wav"]
    """
    # Get all subdirectories.
    subdirs = [d for d in os.listdir(base_dir)
               if os.path.isdir(os.path.join(base_dir, d))]
    if not subdirs:
        raise ValueError(f"No subdirectories found in {base_dir}")

    # Pick one at random.
    chosen_dir = os.path.join(base_dir, random.choice(subdirs))

    # List files in the chosen directory.
    files = os.listdir(chosen_dir)
    wav_files = [f for f in files if f.lower().endswith(".wav")]

    # Check if there are exactly 2 files.
    if len(wav_files) != 2:
        raise ValueError \
            (f"Expected exactly 2 WAV files in {chosen_dir}, found {len(wav_files)}.")

    # Identify intro file.
    intro_candidates = [f for f in wav_files if f.lower().startswith("intro")]
    if len(intro_candidates) != 1:
        raise ValueError \
            (f"Expected exactly one intro file (starting with 'intro') in {chosen_dir}.")

    intro_file = intro_candidates[0]
    music_file = [f for f in wav_files if f != intro_file][0]

    return [
        os.path.join(chosen_dir, intro_file),
        os.path.join(chosen_dir, music_file)
        ]


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
