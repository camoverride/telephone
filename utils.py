import collections
import pyaudio
import wave
import subprocess
import platform
import webrtcvad
import time

# System-dependent import.
if platform.system() == "Linux":
    from gpiozero import Button

    # GPIO 17 with 50ms debounce time.
    button = Button(17, bounce_time=0.05)


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
        return button.is_pressed


def record_audio(save_filepath: str,
                 max_duration: int) -> str:
    """
    Records audio and saves it to a .wav file, stopping when
    speech ends or max_duration is reached.

    Parameters
    ----------
    save_filepath : str
        Where the resulting .wav file will be saved.
    max_duration : int
        Maximum duration of the recording, in seconds.

    Returns
    -------
    str
        The filepath of the saved audio.
    """
    rate = 16000
    frame_duration_ms = 30  # Duration of a single frame in milliseconds
    frame_size = int(rate * frame_duration_ms / 1000)  # Number of samples per frame
    frame_bytes = frame_size * 2  # 2 bytes per sample (16-bit audio)
    silence_timeout = 1  # Stop if silence for 1 second

    vad = webrtcvad.Vad()
    vad.set_mode(2)  # 0=aggressive, 3=very aggressive

    p = pyaudio.PyAudio()

    stream = p.open(format=pyaudio.paInt16,
                    channels=1,
                    rate=rate,
                    input=True,
                    frames_per_buffer=frame_size)

    frames = []
    ring_buffer = collections.deque(maxlen=int(silence_timeout * 1000 / frame_duration_ms))

    start_time = time.time()
    speech_detected = False

    try:
        while True:
            now = time.time()
            if now - start_time > max_duration:
                break

            data = stream.read(frame_size, exception_on_overflow=False)
            is_speech = vad.is_speech(data, rate)

            frames.append(data)
            ring_buffer.append(is_speech)

            if is_speech:
                speech_detected = True

            if speech_detected and not any(ring_buffer):
                # We heard speech earlier, but now it's been silent for a while
                break
    finally:
        stream.stop_stream()
        stream.close()
        p.terminate()

    with wave.open(save_filepath, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(p.get_sample_size(pyaudio.paInt16))
        wf.setframerate(rate)
        wf.writeframes(b''.join(frames))

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
