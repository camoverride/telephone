import base64
from flask import Flask, request, jsonify
from flask_restful import Api, Resource
import io
import json
import numpy as np
from vosk import Model, KaldiRecognizer
import wave
from utils import HealthCheckAPI



# Initialize Flask application and RESTful API.
app = Flask(__name__)
api = Api(app)


# Import the Vosk speech recognition model (small English model for now).
model = Model("models/vosk-model-small-en-us-0.15")


def vosk_asr(
    audio : np.ndarray,
    sample_rate : int = 16000) -> str:
    """
    Perform Automatic Speech Recognition (ASR) 
    using Vosk on in-memory audio data.

    Parameters
    ----------
    audio : np.ndarray
        Raw audio samples as a NumPy array, typically int16. If the
        audio is float, it will be scaled to int16 for Vosk compatibility.
    sample_rate : int
        The sampling rate of the audio. Default is 16000 Hz.

    Returns
    -------
    str
        Transcribed text from the audio input.
    """
    # Initialize the recognizer with the model and sample rate.
    rec = KaldiRecognizer(model, sample_rate)
    rec.SetWords(True) # Enables word-level recognition.

    # If audio is not in int16 format, scale it.
    if audio.dtype != np.int16:
        audio = (audio * 32767).astype(np.int16)

    audio_bytes = audio.tobytes()
    chunk_size = 4000 # The size of each audio chunk to process at a time.

    result_text = ""
    for i in range(0, len(audio_bytes), chunk_size):
        chunk = audio_bytes[i:i + chunk_size]
        if rec.AcceptWaveform(chunk):
            res = json.loads(rec.Result())
            result_text += res.get("text", "") + " "

    # Process any remaining audio to finalize the recognition.
    res = json.loads(rec.FinalResult())
    result_text += res.get("text", "")

    return result_text.strip()


def speech_to_text(
    audio_np : np.ndarray,
    model : str,
    sample_rate : int = 16000) -> str:
    """
    Converts audio data to text using a specified ASR model.

    Parameters
    ----------
    audio : np.ndarray
        The raw audio data in a NumPy array (int16).
    model : str
        The ASR model to use. Supported models: "vosk".
    sample_rate : int
        The audio sampling rate, typically 16000 Hz.

    Returns
    -------
    str
        The transcribed text.

    Raises
    ------
    ValueError
        If the provided model is unsupported.
    """
    if model == "vosk":
        return vosk_asr(audio=audio_np, sample_rate=sample_rate)

    raise ValueError(f"Unsupported model: {model}")


class SpeechToTextAPI(Resource):
    """
    RESTful API resource for Speech to Text (ASR) conversion.

    Exposes a POST endpoint at `/asr` that accepts JSON input containing audio
    and ASR parameters, and returns the recognized text.

    Expected JSON input fields:
        - audio (str): Base64-encoded audio data (WAV format, mono, 16-bit PCM).
        - model (str): ASR model to use (currently supports "vosk").
    """

    def post(self):
        """
        Handle POST request to transcribe audio to text.

        Expected JSON body:
        {
            "audio": "base64-encoded-audio",
            "model": "vosk"
        }

        Returns:
        -------
        JSON:
            - status: "success" or "error"
            - text: Transcribed text (if successful)
            - message: Error message (if any failure occurs)
        """
        try:
            # Parse incoming JSON request.
            data = request.get_json()

            # Base64-encoded audio data.
            audio_b64 = data["audio"]
            
            # Normalize model name.
            model_name = data["model"].strip().lower()

            # Decode the base64-encoded audio into raw bytes.
            audio_bytes = base64.b64decode(audio_b64)

            # Extract PCM audio data from the WAV file.
            with wave.open(io.BytesIO(audio_bytes), 'rb') as wav:
                sample_rate = wav.getframerate() # Sampling rate of the audio.

                if wav.getnchannels() != 1:
                    raise ValueError("Audio must be mono-channel.")

                if wav.getsampwidth() != 2:
                    raise ValueError("Audio must be 16-bit PCM.")

                # Read the raw audio frames and convert them to a NumPy array.
                audio_data = wav.readframes(wav.getnframes())
                audio_np = np.frombuffer(audio_data, dtype=np.int16)

                # Limit the maximum audio duration (for performance reasons).
                if len(audio_np) > sample_rate * 600:
                    raise ValueError("Audio too long; limit to 10 minutes.")

            # Transcribe the audio to text.
            transcription = speech_to_text(
                audio_np=audio_np,
                model=model_name,
                sample_rate=sample_rate)

            return jsonify({
                "status": "success",
                "text": transcription})

        # Handle missing fields in the request.
        except KeyError as ke:
            return jsonify({
                "status": "error",
                "message": f"Missing field: {ke}"}), 400

        # General error handling.
        except Exception as e:
            return jsonify({
                "status": "error",
                "message": str(e)}), 500


# Add the resources to the Flask app.
api.add_resource(SpeechToTextAPI, "/asr")
api.add_resource(HealthCheckAPI, "/health")



if __name__ == "__main__":

    # Run the ASR server.
    app.run(
        host="0.0.0.0",
        port=8011,
        debug=True)
