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
    filepath: str,
    save_folder: str) -> None:
    """
    Reads an existing audio file (WAV) from `filepath`
    and saves a copy into `save_folder` with a timestamped filename.
    """
    os.makedirs(save_folder, exist_ok=True)

    # Generate new filename
    filename = os.path.join(
        save_folder, f"recording_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.wav"
    )

    # Read and write WAV data
    with wave.open(filepath, "rb") as source:
        params = source.getparams()
        audio_data = source.readframes(params.nframes)

    with wave.open(filename, "wb") as target:
        target.setparams(params)
        target.writeframes(audio_data)

    print(f"Saved audio copy to: {filename}")
