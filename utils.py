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
                 speech_onset_timeout : int,
                 max_duration: int,
                 silence_timeout : int) -> str | None:
    """
    Records audio and saves it to a .wav file.

    Listening begins immediately, with voice activity detection (VAD)
    waiting up to `speech_onset_timeout` seconds to detect human speech.
    Speech is recorded from the beginning of speech onset for up to
    `max_duration` seconds or until the speaker is silent for
    `silence_timeout` seconds.

    The file is saved to `save_filepath`.

    NOTE: there is a buffer so that some audio from before VAD detects
    speech onset is also recorded, meaning that no speech is lost
    (VAD can lag slightly behind actual speech onset).

    NOTE: If no speech is recorded within the initial `speech_onset_timeout`
    window, the function returns None.

    Parameters
    ----------
    save_filepath : str
        Where the resulting .wav file will be saved.
    speech_onset_timeout : int
        This function listens for `speech_onset_timeout` from the beginning
        of this function call for human speech. NOTE: If no speech is detected
        within this window the function returns `None`
    max_duration : int
        Maximum duration of the speech recording, in seconds, starting
        from the beginning of speech onset.
    silence_timeout : int
        Ends recording if speech has been initiated but there is no
        additional speech for `silence_timeout` secs.

    Returns
    -------
    None
        if no speech is detected within the `speech_onset_timeout`
        window, or if VAD is triggered but there is some downstream
        error (for example: speech is incomprehensible).
    str 
        if there was audio, filepath of the saved audio.
    """
    # Voice activity detection
    # (mode 0=aggressive, 2=moderate aggressive, 3=very aggressive).
    # NOTE: possibly yank `mode`` to argument variable.
    vad = webrtcvad.Vad()
    vad.set_mode(2)
    P = pyaudio.PyAudio()

    rate = 16000
    frame_duration_ms = 30
    frame_size = int(rate * frame_duration_ms / 1000)
    frame_bytes = frame_size * 2 # 16-bit audio => 2 bytes per sample

    # Open audio stream, defined globally
    stream = P.open(format=pyaudio.paInt16,
                    channels=1,
                    rate=rate,
                    input=True,
                    frames_per_buffer=frame_size)

    # Recorded frames after speech onset.
    frames = []

    # Buffer of ~300ms before speech onset.
    pre_speech_buffer = collections.deque(maxlen=10)

    # Track silence after speech onset.
    ring_buffer = collections.deque(maxlen=int(silence_timeout * 1000 / frame_duration_ms))

    # Timers and flags
    function_start_time = time.time()
    speech_start_time = None # When speech was first detected
    last_speech_time = None # Last time speech was detected

    try:
        while True:
            time.sleep(0.01)
            now = time.time()

            # Read one frame of audio
            data = stream.read(frame_size, exception_on_overflow=False)

            # Check if frame contains speech
            is_speech = vad.is_speech(data, rate)

            if speech_start_time is None:
                # Waiting for speech onset

                pre_speech_buffer.append(data)

                if is_speech:
                    # Speech detected - mark speech start time and last speech time
                    speech_start_time = now
                    last_speech_time = now

                    # Add buffered pre-speech audio frames to recording frames
                    frames.extend(pre_speech_buffer)

                    print("Speech detected, starting recording...")

            # This check must be outside the inner `if` block
            if speech_start_time is None and now - function_start_time > speech_onset_timeout:
                print(f"No speech detected within {speech_onset_timeout} seconds, aborting.")
                return None

            else:
                # Speech has started - recording ongoing

                frames.append(data)
                ring_buffer.append(is_speech)

                if is_speech:
                    last_speech_time = now

                # Check if max_duration exceeded (count from speech start)
                if now - speech_start_time > max_duration:
                    print("Max duration reached, stopping recording.")
                    break

                # Check if silence timeout exceeded after last speech detected
                if now - last_speech_time > silence_timeout:
                    print("Silence timeout reached after speech, stopping recording.")
                    break

    finally:
        stream.stop_stream()
        stream.close()
        P.terminate()

    # If no frames recorded (shouldn't happen, but safeguard)
    if not frames:
        print("No audio recorded despite speech detection, returning None.")
        return None

    # Save recorded frames to WAV file
    with wave.open(save_filepath, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(P.get_sample_size(pyaudio.paInt16))
        wf.setframerate(rate)
        wf.writeframes(b''.join(frames))

    print(f"Audio saved to {save_filepath}")

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


def print_text(text : str,
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
    print(f"Printing this: {text}")
    data = {"text": text}

    response = requests.post(printer_api,
                             json=data,
                             timeout=(1.0, 10.0)) # (connect_timeout, read_timeout)

    print(response.json())


def start_audio_loop(looping_sound: str) -> subprocess.Popen:
    """
    Starts playing audio in a loop using ffplay (Linux) or
    afplay (macOS). Returns the subprocess so it can be terminated.

    NOTE: afplay does not loop on MACOS

    Parameters
    ----------
    looping_sound : str
        Path to an audio file that will loop following the initial message.
    
    Returns
    -------
    subprocess.Popen
        A subprocess that can be terminated.
    """
    # Play the sound ONE TIME.
    if platform.system() == "Darwin":
        process = subprocess.Popen(["afplay", looping_sound])

    # Play the looping sound.
    elif platform.system() == "Linux":
        process = subprocess.Popen(
            ["ffplay", "-nodisp", "-autoexit", "-loglevel",
             "quiet", "-loop", "0", looping_sound],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )

    else:
        raise RuntimeError("Unsupported OS for audio playback")

    return process


def stop_audio_loop(process: subprocess.Popen) -> None:
    """
    Stops the audio loop by terminating the process.

    Parameters
    ----------
    process : subprocess.Popen
        A process that can be terminated.
    
    Returns
    -------
    None
        A process is terminated.
    """
    if process and process.poll() is None:
        process.terminate()
