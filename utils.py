import logging
import multiprocessing
import platform
import requests
import subprocess
import threading
import time



# Set up logging configuration
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s')


# Read all the banned words into a list.
with open("banned_words.txt", "r") as f:
    BANNED_WORDS = [line.rstrip('\n') for line in f]


# System-dependent import. Get The GPIO pins on Raspbian.
# TODO: must specifically recognize Raspbian (debian)
# TODO: not all Pi's will be using the button
if platform.system() == "Linux":
    from gpiozero import Button # type: ignore

    # GPIO 17 with 50ms debounce time.
    button = Button(17, bounce_time=0.05)


def phone_picked_up() -> bool: # type:ignore  Type not recognized.
    """
    Returns True if the phone is picked up, otherwise False.

    Imports `button` from RPi's gpiozero library.

    NOTE: when the phone is picked up, the circuit is completed.
    When the phone is placed down, the circuit disconnects.

    Returns
    -------
    bool
        True
            The phone is picked up.
            NOTE: also always True if testing on MacOS
        False
            The phone is placed down.
    """
    if platform.system() == "Darwin":
        return True

    elif platform.system() == "Linux":
        return button.is_pressed


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
        True if the input is a simple greeting, a filler word, or
        contains profanity. Otherwise False.
    """
    # Check whether the entire input is bad, like a greeting.
    if text.lower() in ("huh", "hi", "hello", "sup",
                        "what's up", "greetings", "hi there",
                        "hello there"):
        return True

    # Check whether the input is a filler word.
    if (not text) or text.lower() in ("", " ", "huh", "what", "um"):
        return True

    # Check if there are banned words in the input.
    if any(word in text.lower() for word in BANNED_WORDS):
        return True

    return False


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
    logging.info(f"Printing this: {text}")
    data = {"text": text}

    response = requests.post(
        printer_api,
        json=data,
        timeout=(1.0, 10.0)) # (connect_timeout, read_timeout)

    logging.debug(response.json())


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
        filepath: str,
        start_delay: int,
        looping: bool,
        blocking: bool,
        killable: bool):

        self.filepath = filepath
        self.start_delay = start_delay
        self.looping = looping
        self.blocking = blocking
        self.killable = killable

        # Active audio subprocess.
        self.process: subprocess.Popen | None = None
        # (Unused currently).
        self._kill_thread: threading.Thread | None = None
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
                logging.info("Phone put down — terminating audio.")
                self.stop()
                break
            time.sleep(0.1)

    def start(self) -> None:
        """
        Begins playback of the audio file. Respects the options specified at init:
            - Applies a start delay.
            - Repeats playback if `looping=True`.
            - Blocks the caller if `blocking=True`, otherwise runs in a background thread.
            - Terminates early if `killable=True` and `phone_picked_up()` returns False.
        """
        if self.start_delay > 0:
            time.sleep(self.start_delay)

        # Reset internal flag (useful if reusing the object).
        self._looping = True

        def play_loop():
            while self._looping:
                if self.killable and not phone_picked_up():
                    logging.info("Phone put down — terminating audio.")
                    self.stop()
                    break

                # Start playback.
                command = self._build_command()
                self.process = subprocess.Popen(
                    command,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL)

                # Wait for process to complete (or be killed).
                self.process.wait()

                # Stop loop after one play if not looping.
                if not self.looping:
                    break

        # Play as a blocking function.
        if self.blocking:
            play_loop()

        # Run the loop in a background thread.
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


class KillableFunction:
    def __init__(
        self,
        func,
        *,
        args=(),
        kwargs=None,
        kill_check=lambda: False,
        check_interval=0.1,
        use_thread=False):

        self.func = func
        self.args = args
        self.kwargs = kwargs if kwargs is not None else {}
        self.kill_check = kill_check
        self.check_interval = check_interval
        self.use_thread = use_thread
        self._result = None
        self._exception = None

        if not self.use_thread:
            self._result_queue = multiprocessing.Queue()

    def _target_process(self, result_queue):
        try:
            result = self.func(*self.args, **self.kwargs)
            result_queue.put(('result', result))
        except Exception as e:
            result_queue.put(('error', e))

    def _target_thread(self):
        try:
            self._result = self.func(*self.args, **self.kwargs)
        except Exception as e:
            self._exception = e

    def run(self):
        if self.use_thread:
            thread = threading.Thread(target=self._target_thread)
            thread.start()

            while thread.is_alive():
                if self.kill_check():
                    logging.warning("Kill condition triggered. Cannot forcibly kill threads cleanly.")
                    # Threads cannot be forcefully killed in Python, so just return None
                    return None
                time.sleep(self.check_interval)

            thread.join()
            if self._exception:
                raise self._exception
            return self._result
        else:
            process = multiprocessing.Process(target=self._target_process, args=(self._result_queue,))
            process.start()

            try:
                while process.is_alive():
                    if self.kill_check():
                        logging.warning("Kill condition triggered. Terminating process.")
                        process.terminate()
                        process.join()
                        return None
                    time.sleep(self.check_interval)

                process.join()
                if not self._result_queue.empty():
                    status, value = self._result_queue.get()
                    if status == 'result':
                        return value
                    elif status == 'error':
                        raise value
                else:
                    return None

            except KeyboardInterrupt:
                logging.warning("KeyboardInterrupt — terminating process.")
                process.terminate()
                process.join()
                return None
