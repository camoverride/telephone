import os
import random
import requests



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
