import pyaudio
import wave
import subprocess
import platform


# if platform.system() == "Linux":
#     import RPi.GPIO as GPIO

#     # Choose the pin. GPIO 17, physical pin 11.
#     BUTTON_PIN = 17

#     # Set up GPIO.
#     GPIO.setmode(GPIO.BCM)
#     GPIO.setup(BUTTON_PIN, GPIO.IN)

#     def phone_picked_up() -> bool:
#         """
#         Check whether the phone is picked up.

#         Returns
#         -------
#         bool
#             Returns True if the button is pressed, otherwise False.
#         """
#         if GPIO.input(BUTTON_PIN) == GPIO.LOW:
#             return True

#         else:
#             return False

# # If testing on MacBook
# elif platform.system() == "Darwin":
#     def phone_picked_up():
#         return True



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
        subprocess.run(["aplay", filename])
    
    # The system is not recognized.
    else:
        raise RuntimeError("Unsupported OS for audio playback")
