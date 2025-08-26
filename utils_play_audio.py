import platform
import subprocess
import threading
import time
from typing import Optional
from utils_gpio import phone_picked_up, PhonePutDownError



class play_audio:
    """
    A cross-platform audio playback class with support for delayed
    start, looping, blocking or non-blocking playback, and conditional
    termination based on an external condition (e.g. phone being put down).

    Supports:
    - macOS (via `afplay`)
    - Linux (Ubuntu, Raspbian) via `ffplay`

    Example usage (non-blocking looped audio with kill-switch):

        audio = play_audio("sound.wav",
                           looping=True,
                           blocking=False,
                           killable=True)
        audio.start()
        ...
        audio.stop()  # To stop playback manually

    Parameters
    ----------
    filepath : str
        Path to the audio file (.wav, .mp3, etc.)
    start_delay : int, optional
        Delay (in seconds) before audio playback starts. Default is 0.
    looping : bool, optional
        If True, the audio file will loop indefinitely. Default is False.
    blocking : bool, optional
        If True, the call to `.start()` will block until playback finishes. 
        If False, playback runs in a background thread. Default is True.
    killable : bool, optional
        If True, playback will stop automatically 
        if `phone_picked_up()` returns False. 
        Default is False.
    """
    def __init__(
        self,
        filepath : str,
        start_delay : int,
        looping : bool,
        blocking : bool,
        killable : bool):

        self.filepath = filepath
        self.start_delay = start_delay
        self.looping = looping
        self.blocking = blocking
        self.killable = killable

        # Active audio subprocess.
        self.process: Optional[subprocess.Popen] = None
        # (Unused currently).
        self._kill_thread: Optional[threading.Thread] = None
        # Used to manually break out of afplay loops (macOS).
        self._looping = True

    def _build_command(self) -> list[str]:
        """
        Constructs the appropriate playback command depending
        on the platform.

        Returns
        -------
        list[str]
            Command list to be passed to subprocess.
        """
        if platform.system() == "Darwin":
            # No native loop--handled in Python.
            return ["afplay", self.filepath]

        elif platform.system() == "Linux":
            base_cmd = ["ffplay", "-nodisp", "-loglevel", "quiet"]
            if self.looping:
                base_cmd += ["-loop", "0"] # Infinite loop.
            else:
                base_cmd += ["-autoexit"] # Exit after playing once.
            return base_cmd + [self.filepath]

        else:
            raise RuntimeError("Unsupported OS for audio playback")

    def _monitor_kill_switch(self):
        """
        Thread that monitors phone state and stops playback
        if `phone_picked_up()` returns False.

        (Used only in non-blocking Linux mode.)
        """
        while self.process and self.process.poll() is None:
            if not phone_picked_up():
                raise PhonePutDownError
                logging.info("Phone put down — terminating audio.")
                self.stop()
                break
            time.sleep(0.1)

    def start(self) -> None:
        if self.start_delay > 0:
            time.sleep(self.start_delay)

        self._looping = True

        def play_loop():
            while self._looping:
                if self.killable and not phone_picked_up():
                    raise PhonePutDownError
                    logging.info("Phone put down — terminating audio.")
                    self.stop()
                    break

                command = self._build_command()
                self.process = subprocess.Popen(
                    command,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )

                if self.blocking:
                    # Poll subprocess and phone state in a tight loop for killability
                    while True:
                        if self.process.poll() is not None:
                            # Playback finished naturally
                            break
                        if self.killable and not phone_picked_up():
                            raise PhonePutDownError
                            logging.info("Phone put down — terminating audio during playback.")
                            self.stop()
                            break
                        time.sleep(0.1)

                    if not self.looping or not self._looping:
                        break

                else:
                    # Non-blocking, just start process and return (kill monitor elsewhere)
                    self.process.wait()
                    if not self.looping or not self._looping:
                        break

        if self.blocking:
            play_loop()
        else:
            thread = threading.Thread(target=play_loop, daemon=True)
            thread.start()


    def stop(self) -> None:
        """
        Terminates any active playback process and exits the loop.
        Safe to call even if no playback is active.
        """
        # Stops loop even on macOS.
        self._looping = False

        if self.process and self.process.poll() is None:
            self.process.terminate()
            self.process.wait()
        self.process = None

    def is_playing(self) -> bool:
        """
        Returns whether audio is currently playing.

        Returns
        -------
        bool
            True if an audio process is running, False otherwise.
        """
        return (self.process is not None) and (self.process.poll() is None)
