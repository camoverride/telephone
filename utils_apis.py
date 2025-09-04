import logging
import multiprocessing
import requests
import time
from typing import Any, Callable, Optional
import yaml
from utils_gpio import phone_picked_up



# Set up logging configuration.
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        # Print logs to the console.
        logging.StreamHandler(),
        # Write logs to a file.
        logging.FileHandler("logs/api_utils.log")])
logger = logging.getLogger(__name__)


class KillableFunctionRunner:
    """
    A class to run any function in a separate process that is
    monitored by a "killer" function. If the killer returns False,
    the process is terminated.

    Example usage:
        runner = KillableFunctionRunner(func=text_to_speech_api, 
                                        killer=is_phone_picked_up)
        result = runner.start(arg1=value1, arg2=value2)
    """

    def __init__(
        self,
        func : Callable[..., Optional[str]],
        killer : Callable[[], bool],
        check_interval : float = 0.1) -> None:
        """
        Initialize the runner.

        Parameters
        ----------
        func : Callable
            The main function to run (e.g., text_to_speech_api).
        killer : Callable[[], bool]
            A function that returns False when the process should be killed.
        check_interval : float
            Time interval (in seconds) to check the killer function.
        """
        # Function to run in the child process.
        self.func = func

        # Function that determines if we should kill the process.
        self.killer = killer

        # Frequency to check the killer.
        self.check_interval = check_interval

        # Will hold the process.
        self._process: Optional[multiprocessing.Process] = None

        # Queue for receiving result from the process.
        self._queue: Optional[multiprocessing.Queue] = None


    def _target(
        self, 
        queue : multiprocessing.Queue, kwargs: dict):
        try:
            # Execute the function with passed arguments.
            result = self.func(**kwargs)

            # Send result back to parent process.
            queue.put(result)

        except Exception as e:
            # Send exception back if something goes wrong.
            logger.warning("[Child] Exception occurred:")
            logger.warning(e)
            queue.put(e)


    def start(
        self, 
        **kwargs: Any) -> Optional[str]:
        """
        Start the process and monitor with killer function.

        Parameters
        ----------
        kwargs : Any
            Keyword arguments passed to the function.

        Returns
        -------
        Optional[str]
            The function's return value or None if killed.
        """
        # Create a queue for communication.
        manager = multiprocessing.Manager()
        self._queue = manager.Queue()  # type: ignore

        self._process = multiprocessing.Process(
            target=self._target,
            # Launch the function with arguments.
            args=(self._queue, kwargs))

        # Start the child process.
        self._process.start()

        try:
            # Monitor the killer condition in a loop.
            while self._process.is_alive():

                # If killer returns False, kill the process.
                if not self.killer():
                    self.stop()
                    # Indicate it was stopped prematurely.
                    return None

                # Wait before checking again.
                time.sleep(self.check_interval)

            # Wait for process to finish gracefully.
            self._process.join()

            # Try to retrieve the result (or exception) from the queue.
            if not self._queue.empty():  # type: ignore
                result = self._queue.get()  # type: ignore
                if isinstance(result, Exception):
                    # Reraise any exception from the process.
                    raise result
                # Return the successful result.
                return result
            else:
                logger.warning("[Parent] Queue is empty after process \
                               joined. No result received.")

            # No result available.
            return None

        # Make sure to clean up.
        except Exception as e:
            self.stop()
            raise e


    def stop(self):
        """
        Terminate the process if running.
        """
        if self._process and self._process.is_alive():
            # Force kill the process.
            self._process.terminate()

            # Wait until it's finished.
            self._process.join()

        # Reset process and queue for safety.
        self._process = None
        self._queue = None


def record_audio_api(
    silence_duration_to_stop : float,
    min_recording_duration : float,
    max_recording_duration : float,
    recording_api_url : str) -> Optional[str]:
    """
    Sends a request to the AudioRecordingAPI to start recording audio
    and returns the base64-encoded audio.

    Parameters
    ----------
    silence_duration_to_stop : float
        The duration of silence to trigger the stopping of the recording (default 3.0).
    min_recording_duration : float
        The minimum duration of the recording (default 5.0).
    max_recording_duration : float
        The maximum duration of the recording (default 30.0).
    recording_api_url : str
        The URL of the AudioRecordingAPI endpoint.

    Returns
    -------
    str
        The base64-encoded audio if successful.
    None
        On failure or if no audio is detected.
    """
    payload = {
        "silence_duration_to_stop": silence_duration_to_stop,
        "min_recording_duration": min_recording_duration,
        "max_recording_duration": max_recording_duration}

    try:
        # Timeout must be longer than max_recording_duration.
        timeout = max_recording_duration + 1 + 2

        # Send the POST request to the API.
        response = requests.post(
            recording_api_url,
            json=payload,
            timeout=timeout)
        
        # Raise an error for any failed responses
        response.raise_for_status()

        # Parse the JSON response
        result = response.json()

        # Check if the response was successful
        if result.get("status") == "success":
            # Return the base64-encoded audio
            return result.get("audio")

        else:
            pass
            # raise RuntimeError(f"Error from API: {result.get('message')}")

    except requests.RequestException as e:
        # Handle any connection or request exceptions
        raise RuntimeError(f"Failed to contact recording API: {e}")

    except ValueError as ve:
        # Handle JSON parsing errors
        raise RuntimeError(f"Failed to parse the response: {ve}")


def speech_to_text_api(
    audio_b64 : str,
    model : str,
    asr_server_url : str) -> Optional[str]:
    """
    Sends an ASR request to a remote server via HTTP.

    Parameters
    ----------
    audio_b64 : str
        Base64-encoded WAV audio string.
    model : str
        The ASR model to use (e.g., "vosk").
    asr_server_url : str
        URL of the remote ASR API endpoint (e.g., "http://localhost:5000/asr").

    Returns
    -------
    str
        The transcribed text.
    None
        On failure or if no speech is detected.
    """
    # Prepare the payload for the request
    payload = {
        "audio": audio_b64,
        "model": model}

    try:
        # Make the POST request to the ASR API
        response = requests.post(asr_server_url, json=payload, timeout=10)
        response.raise_for_status()  # Raise an exception for HTTP errors
        result = response.json()

        # Check if the transcription was successful
        if result.get("status") == "success":
            return result.get("text")  # Return the transcribed text
        else:
            raise RuntimeError(f"ASR failed: {result.get('message')}")

    except requests.RequestException as e:
        raise RuntimeError(f"Failed to contact ASR server: {e}")
    except Exception as e:
        raise RuntimeError(f"Error during speech-to-text conversion: {e}")


def response_api(
    text : str,
    model : str,
    response_api_url : str,
    system_prompt) -> Optional[str]:
    """
    Sends a request to the TextResponseAPI to generate a response based on input text.

    Parameters
    ----------
    text : str
        The input text for generating a response.
    model : str
        The model to use (e.g., "translate", "tiny_llama", "deepseek").
    response_api_url : str
        URL of the remote TextResponseAPI endpoint.
    system_prompt : str
        The system prompt which the response is conditioned on (if applicable).

    Returns
    -------
    str
        The model-generated response if successful.
    None
        On failure.
    """
    payload = {
        "text": text,
        "model": model,
        "system_prompt": system_prompt}

    try:
        # Send the POST request to the API
        response = requests.post(
            response_api_url,
            json=payload,
            timeout=10)
        
        # Raise an error for any failed responses
        response.raise_for_status()

        # Parse the JSON response
        result = response.json()

        # Check if the response was successful
        if result.get("status") == "success":
            # Return the model-generated response
            return result.get("response")
        else:
            raise RuntimeError(f"Error from API: {result.get('message')}")

    except requests.RequestException as e:
        # Handle any connection or request exceptions
        raise RuntimeError(f"Failed to contact response API: {e}")
    except ValueError as ve:
        # Handle JSON parsing errors
        raise RuntimeError(f"Failed to parse the response: {ve}")


def text_to_speech_api(
    output_audio_path : str,
    text : str,
    model : str,
    language : str,
    tts_server_url : str) -> Optional[str]:
    """
    Sends a TTS request to a remote server via HTTP.

    Parameters
    ----------
    output_audio_path : str
        Desired output path for the generated audio file (on the server).
    text : str
        The text to synthesize into speech.
    model : str
        The TTS model to use on the server.
    language : str
        Language code for TTS (e.g., "en", "zh-CN").
    tts_server_url : str
        URL of the remote TTS API endpoint.

    Returns
    -------
    str
        The path to the audio file on the server (if successful)
    None
        On failure.
    """
    payload = {
        "text": text,
        "model": model,
        "output_audio_path": output_audio_path,
        "language": language}

    try:
        response = requests.post(
            tts_server_url,
            json=payload,
            timeout=10)
        response.raise_for_status()
        result = response.json()

        if result.get("status") == "success":
            return result.get("audio_path")
        else:
            raise RuntimeError(f"TTS failed: {result.get('message')}")

    except requests.RequestException as e:
        raise RuntimeError(f"Failed to contact TTS server: {e}")



# Load config file.
with open("config.yaml", "r") as f:
    CONFIG = yaml.safe_load(f)


def vad():
    """
    VAD wrapper function.
    """
    vad_runner = KillableFunctionRunner(
        func=record_audio_api,
        killer=phone_picked_up)

    audio = vad_runner.start(
        silence_duration_to_stop=CONFIG["silence_duration_to_stop"],
        min_recording_duration=CONFIG["min_recording_duration"],
        max_recording_duration=CONFIG["max_recording_duration"],
        recording_api_url=CONFIG["vad_api_url"])
    
    return audio



def asr(audio):
    """
    ASR wrapper funtion.
    """
    asr_runner = KillableFunctionRunner(
        func=speech_to_text_api,
        killer=phone_picked_up)

    transcription = asr_runner.start(
        audio_b64=audio,
        model=CONFIG["asr_model"],
        asr_server_url=CONFIG["asr_api_url"])

    return transcription


def respond(transcription):
    """
    Response wrapper function.
    """
    response_runner = KillableFunctionRunner(
        func=response_api,
        killer=phone_picked_up)

    response = response_runner.start(
        text=transcription,
        model=CONFIG["response_model"],
        response_api_url=CONFIG["response_api_url"],
        system_prompt=CONFIG["system_prompt"])

    return response


def tts(response):
    """
    TTS wrapper function.
    """
    tts_runner = KillableFunctionRunner(
        func=text_to_speech_api,
        killer=phone_picked_up)

    audio_path = tts_runner.start(
        text=response,
        output_audio_path=CONFIG["tts_file_output_path"],
        model=CONFIG["text_to_speech_model"],
        language=CONFIG["tts_language"],
        tts_server_url=CONFIG["tts_api_url"])

    return audio_path
