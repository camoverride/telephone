from flask import Flask, request, jsonify
from flask_restful import Api, Resource
from gtts import gTTS
import logging
import os
import platform
import pyttsx3
import re
import requests
import subprocess
from typing import Optional
import yaml
from utils import HealthCheckAPI



# Initialize Flask application and RESTful API.
app = Flask(__name__)
api = Api(app)


# Set up logging configuration.
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        # Print logs to the console.
        logging.StreamHandler(),
        # Write logs to a file.
        logging.FileHandler("logs/tts_server.log")])
logger = logging.getLogger(__name__)


# Load config file.
with open("config.yaml", "r") as f:
    config = yaml.safe_load(f)


def clean_text_for_tts(text : str) -> str:
    """
    Remove characters unwanted for TTS.

    Parameters
    ----------
    text : str
        Some text returned from the response generator.

    Returns
    -------
    str
        Text cleaned of unwanted characters.
    """
    cleaned = re.sub(r'[\*\_\[\]\{\}\(\)\~\^\=\|\\\/<>#@`]', '', text)

    return cleaned


def google_tts(
    text : str,
    output_audio_path : str,
    language : str):
    """
    Use Google to perform TTS.

    Parameters
    ----------
    text : str
        The text to be synthesized.
    output_audio_path : str
        Where the .wav file should be saved.
    language : str
        Language. "en", "zh-CN", etc.

    Returns
    -------
    str
        Path to the generated WAV audio file.
    """
    tts = gTTS(text=text,
               lang=language)
    tts.save(output_audio_path)

    return output_audio_path


def command_line_say(
    text : str,
    output_audio_path : str) -> str:
    """
    Use simple command line tools to perform TTS.
    Automatically detects whether we are on Linux or MacOS.

    Parameters
    ----------
    text : str
        The text to be synthesized.
    output_audio_path : str
        Where the .wav file should be saved.
    
    Returns
    -------
    str
        The `output_audio_path`
    """
    # MacOS.
    if platform.system() == "Darwin":
        filename_aiff = "temp.aiff"

        # Use macOS TTS to generate AIFF.
        subprocess.run(["say", "-o", filename_aiff, text])

        # Convert to WAV using ffmpeg.
        subprocess.run(["ffmpeg", "-y", "-i", filename_aiff, output_audio_path],
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        # Cleanup.
        os.remove(filename_aiff)    

    # Linux / Pi.
    elif platform.system() == "Linux":
        # Use pyttsx3 to save speech to file.
        # NOTE: can use "espeak" instead.
        engine = pyttsx3.init()
        engine.save_to_file(text, output_audio_path)
        engine.runAndWait()

    return output_audio_path


def pytts_asr(
    text : str,
    output_audio_path : str) -> str:
    """
    Use the pyttsx3 platform to perform speech synthesis.

    Parameters
    ----------
    text : str
        The words that will be spoken.
    output_audio_path : str
        Where the .wav file should be saved.

    Returns
    -------
    str
        The `output_audio_path` (a wav file).
    """
    engine = pyttsx3.init()
    engine.save_to_file(text, output_audio_path)
    engine.runAndWait()

    return output_audio_path


def jeff_model(
    text : str,
    server_url : str,
    output_audio_path : str) -> str:

    payload = {"text": text}
    headers = {"Content-Type": "application/json"}

    response = requests.post(server_url, json=payload, headers=headers)

    if response.status_code == 200:
        # Save response.content directly to file
        os.makedirs(os.path.dirname(output_audio_path) or '.', exist_ok=True)
        with open(output_audio_path, 'wb') as f:
            f.write(response.content)
        return output_audio_path
    else:
        raise RuntimeError(f"Server returned error {response.status_code}: {response.text}")


def text_to_speech(
    output_audio_path : str,
    text : str,
    model : str,
    language : str) -> Optional[str]:
    """
    Converts some text to a .wav audio file by performing TTS.

    Parameters
    ----------
    text : str
        The words that will be spoken.
    output_audio_path : str
        Where the .wav file should be saved.
    model : str
        Which model to use. Current models:
            - "command_line"
                Simple `say` command line utility. NOTE: only MacOS.
            - "google_tts"
                Google TTS. NOTE: requires an internet connection.
            - "pytts"    
                Pytts library. NOTE: only on Linux.
    language : str
        Language for tts synthesis. E.g. "en", "zh-CN", etc.

    Returns
    -------
    str
        Path to the generated WAV audio file.
    """
    # Purge unwanted characters from the text.
    text = clean_text_for_tts(text)

    # Choose the right model.
    if model == "command_line":
        return command_line_say(
                text=text,
                output_audio_path=output_audio_path)

    elif model == "google_tts":
        return google_tts(
                text=text,
                output_audio_path=output_audio_path,
                language=language)

    elif model == "pytts":
        return pytts_asr(
                text=text,
                output_audio_path=output_audio_path)

    elif model == "jeff":
        return jeff_model(
            text=text,
            server_url=config["jeff_tts_model_url"],
            output_audio_path=output_audio_path)

    else:
        raise ValueError(f"Unsupported TTS model: {model}")


class TextToSpeechAPI(Resource):
    """
    RESTful API resource for Text-to-Speech (TTS) conversion.

    Exposes a POST endpoint at `/tts` that accepts JSON input containing text
    and TTS parameters, and returns the path to the generated audio file.

    Expected JSON input fields:
        - text (str): The text to be converted to speech.
        - model (str): The TTS model to use (e.g., "google_tts", "pytts", "command_line").
        - output_audio_path (str): Desired output file path for the generated audio (.wav).
        - language (str): Language code for TTS (e.g., "en", "zh-cn").

    Returns
    -------
        JSON response with:
        - status (str): "success" or "error"
        - audio_path (str): Path to the generated audio file (on success)
        - message (str): Error message (on failure)
    """
    def post(self):
        """
        Handle POST requests to perform text-to-speech synthesis.

        Reads JSON data from the request body, invokes the text_to_speech function
        with the provided parameters, and returns the resulting audio file path.

        Raises
        ------
            KeyError: If any expected JSON fields are missing.
            Exception: For errors during TTS conversion.
        """
        try:
            # Parse JSON input from client request.
            data = request.get_json()

            # Extract required parameters.
            text = data["text"]
            model = data["model"]
            output_audio_path = data["output_audio_path"]
            language = data["language"]

            # Sanitize the path so system files can't be erased.
            if not output_audio_path.endswith(".wav"):
                raise ValueError("Output file must be a .wav file.")

            # Perform text-to-speech conversion.
            filepath = text_to_speech(
                output_audio_path=output_audio_path,
                text=text,
                model=model,
                language=language)

            # Return success response with audio file path.
            return jsonify({
                "status": "success",
                "audio_path": filepath
            })

        # Return error response with exception message.
        except KeyError as ke:
            return jsonify({
                "status": "error", 
                "message": f"Missing field: {ke}"
            }), 400

        # Catch remaining exceptions.
        except Exception as e:
            return jsonify({
                "status": "error",
                "message": str(e)
            }), 500


# Add the resources to the Flask app.
api.add_resource(TextToSpeechAPI, "/tts")
api.add_resource(HealthCheckAPI, "/health")



if __name__ == "__main__":

    # Run the TTS server.
    app.run(
        host="0.0.0.0",
        port=8013,
        debug=False,
        use_reloader=False)
