import collections
import os
import platform
import pyaudio
import random
import requests
import subprocess
import time
import wave
import webrtcvad



# System-dependent import.
if platform.system() == "Linux":
    from gpiozero import Button # type: ignore

    # GPIO 17 with 50ms debounce time.
    button = Button(17, bounce_time=0.05)


# Voice activity detection. 0=aggressive, 3=very aggressive.
vad = webrtcvad.Vad()
vad.set_mode(2)
P = pyaudio.PyAudio()



def phone_picked_up() -> None:
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


def play_audio_interruptible(filepath : str) -> None:
    """
    Plays an audio file asynchronously using subprocess.Popen.
    Waits for the file to complete playing before moving on.
    If the phone is put down, the audio is killed and this
    function completed.
    """
    # Use afplay for MacOS.
    if platform.system() == "Darwin":
        process = subprocess.Popen(["afplay", filepath])

    # Use aplay for Raspberry Pi audio playback (Linux)
    elif platform.system() == "Linux":
        process = subprocess.Popen(
            ["ffplay", "-nodisp", "-autoexit", "-loglevel", "quiet", filepath],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )

    else:
        raise RuntimeError("Unsupported OS for audio playback")

    # If the phone is picked up, kill the process playing audio.
    try:
        while process.poll() is None:
            if not phone_picked_up():
                process.terminate()
                break
            time.sleep(0.1)

    except Exception:
        process.terminate()
        raise


def play_prompt(prompt_start_delay : int,
                starting_audio_prompt_dir : str,
                prompt_closing_sound : str) -> None:
    """
    Plays a prompt at the beginning of the conversation following a delay.

    Parameters
    ----------
    prompt_start_delay : int
        How long after the reciever is picked up should the propt play.
    starting_audio_prompt_dir : str
        The location of the dir containing prompt files (wav)
    prompt_closing_sound : str or None
        The sound that gets played after a prompt.
    
    Returns
    -------
    None
        Plays an audio file.
    """
    # Delay before prompt
    time.sleep(prompt_start_delay)

    # Randomly select a prompt from the dir
    prompt_files = [f for f in os.listdir(starting_audio_prompt_dir) \
                    if f.lower().endswith(".wav")]
    prompt_path = os.path.join(starting_audio_prompt_dir, 
                               random.choice(prompt_files))

    # Play prompt.
    play_audio_interruptible(prompt_path)

    # Play closing sound, only if phone is still up.
    if prompt_closing_sound and phone_picked_up():
        play_audio_interruptible(prompt_closing_sound)


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

    # Duration of a single frame in milliseconds
    frame_duration_ms = 30

    # Number of samples per frame
    frame_size = int(rate * frame_duration_ms / 1000)

    # 2 bytes per sample (16-bit audio)
    frame_bytes = frame_size * 2

    # Stop if silence for 1 second
    silence_timeout = 1

    # Open audio stream, defined globally
    stream = P.open(format=pyaudio.paInt16,
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
        P.terminate()

    with wave.open(save_filepath, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(P.get_sample_size(pyaudio.paInt16))
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
    bool or str
        False if bad text, otherwise a str
        - "hello" - the person just said "hi"
        - "nothing" - the person didn't say anything
        - "profanity" - the person used profanity.
    """
    # Check whether the entire input is bad.
    if text.lower() in ("huh", "hi", "hello", "sup",
                        "what's up", "greetings", "hi there",
                        "hello there"):
        return "hello"
    
    if not text or text.lower() in ("", " ", "huh", "what", "um"):
        return "nothing"

    # Check if there are banned words.
    if any(word in text.lower() for word in BANNED_WORDS):
        return "profanity"
    
    return False


def print_text(text : str, printer_api: str) -> None:
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

    response = requests.post(printer_api, json=data)

    print(response.json())
