import os
import random



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
