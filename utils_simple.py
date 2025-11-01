import datetime
import os
import random
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
    audio_file,
    save_folder) -> None:

    os.makedirs(save_folder, exist_ok=True)
    filename = f"{save_folder}/recording_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.wav"
    
    with wave.open(filename, "wb") as f:
        f.setnchannels(1)
        f.setsampwidth(2)
        f.setframerate(16000)
        f.writeframes(audio_file)
