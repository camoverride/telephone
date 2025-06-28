import pyaudio
import wave
import subprocess
import platform

# System-dependent import.
if platform.system() == "Linux":
    from gpiozero import Button



def phone_picked_up():
    """
    Returns True if the phone is picked up, otherwise False.

    NOTE: when the phone is picked up, the circuit is completed.
    When the phone is placed down, the circuit disconnects.

    NOTE: on MacOS, always returns True.
    """
    if platform.system() == "Darwin":
        return True
    
    elif platform.system() == "Linux":
        # Use GPIO17 with 50ms debounce
        button = Button(17, bounce_time=0.05)

        return button.is_pressed


def record_audio(save_filepath : str,
                 duration : int) -> str:
    """
    Records audio and saves it to a .wav file.

    Parameters
    ----------
    save_filepath : str
        Where the resulting .wav file will be saved.
    duration : int
        The duration of the recording, in seconds.

    Returns
    -------
    str
        A copy of `save_filepath`
    """
    # NOTE: `rate` should always be 16000
    rate = 16000

    # Record audio.
    p = pyaudio.PyAudio()

    stream = p.open(format=pyaudio.paInt16,
                    channels=1,
                    rate=rate,
                    input=True,
                    frames_per_buffer=1024)

    frames = []

    for _ in range(0, int(rate / 1024 * duration)):
        data = stream.read(1024, exception_on_overflow=False)
        frames.append(data)

    stream.stop_stream()
    stream.close()
    p.terminate()

    # Write to file.
    with wave.open(save_filepath, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(p.get_sample_size(pyaudio.paInt16))
        wf.setframerate(rate)
        wf.writeframes(b''.join(frames))

    # Return is not strictly necessary, because it copies one of the args.
    return save_filepath


def play_audio(filename : str) -> None:
    """
    Plays an audio file.

    Parameters
    ----------
    filename : str
        The file to be played.
    
    Returns
    -------
    None
        Plays an audio file.
    """
    # Use afplay for MacOS.
    if platform.system() == "Darwin":
        subprocess.run(["afplay", filename])
    
    # Use aplay for Raspberry Pi audio playback (Linux)
    elif platform.system() == "Linux":
        subprocess.run(["ffplay", "-autoexit", filename])
    
    # The system is not recognized.
    else:
        raise RuntimeError("Unsupported OS for audio playback")


# Read all the banned words into a list.
with open("banned_words.txt", "r") as f:
    BANNED_WORDS = [line.rstrip('\n') for line in f]

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
        False if bad text, otherwise True
    """
    # Check whether the entire input is bad.
    if not text or text.lower() in ("", " ", "huh", "hi"):
        return True

    # Check if there are banned words.
    if any(word in text.lower() for word in BANNED_WORDS):
        return True
    
    return False
