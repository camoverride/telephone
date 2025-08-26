from flask import Flask, request, jsonify
from flask_restful import Api, Resource
import logging
import numpy as np
import pyaudio
from silero_vad import load_silero_vad, get_speech_timestamps
import time
import torch
from typing import Optional
from utils import encode_audio_to_base64, HealthCheckAPI



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
        logging.FileHandler("server.log")])
logger = logging.getLogger(__name__)

# Load the silero model.
silero_model = load_silero_vad()


def record_audio_with_silero_vad(
    silence_duration_to_stop: float = 3.0,
    min_recording_duration: float = 5.0,
    max_recording_duration: float = 30.0) -> Optional[np.ndarray]:
    """
    Records audio from the mic using Silero VAD. Starts when speech is
    detected, stops after `silence_duration_to_stop` seconds of silence,
    but only if total recording time exceeds `min_recording_duration`.
    Cuts off recording if it exceeds `max_recording_duration`.

    Saves to `save_filepath`.

    Parameters
    ----------
    save_filepath : str
        Where the file is saved.
    silence_duration_to_stop : float
        How much silence until the recording is cut off.
    min_recording_duration : float
        The minimum duration of an accepted recording.
    max_recording_duration : float
        Cuts off the recording at this time.

    Returns
    -------
    str
        save_filepath if audio was recorded
    None
        if no speech detected or recording too short
    """
    # model_ready_event.wait()
    # model = silero_model

    buffer_duration = 1.0
    sample_rate = 16000
    chunk_size = 1024

    # Audio recording object.
    pa = pyaudio.PyAudio()
    stream = pa.open(format=pyaudio.paInt16,
                     channels=1,
                     rate=sample_rate,
                     input=True,
                     frames_per_buffer=chunk_size)

    # Raw int16 numpy arrays waiting for VAD check
    audio_buffer = []

    # Frames after speech started
    recorded_frames = []

    recording_started = False
    last_speech_time = None
    recording_start_time = None

    try:
        while True:
            # if not phone_picked_up():
            #     raise PhonePutDownError()
    
            # Read from the audio stream, appending to the buffer too.
            data = stream.read(chunk_size, exception_on_overflow=False)
            audio_np = np.frombuffer(data, dtype=np.int16)
            audio_buffer.append(audio_np)

            # Run VAD once we have enough audio buffered.
            total_samples = sum(len(chunk) for chunk in audio_buffer)

            if total_samples < int(buffer_duration * sample_rate):
                continue

            audio_for_vad = np.concatenate(audio_buffer)
            audio_tensor = torch.from_numpy(audio_for_vad).float() / 32768.0

            speech_timestamps = get_speech_timestamps(
                audio_tensor,
                silero_model,
                sampling_rate=sample_rate,
                return_seconds=True)

            # Assuming a buffer of 1 sec, if greater than 0.3 is speech, it's real
            speech_duration = sum(ts['end'] - ts['start'] for ts in speech_timestamps)

            if speech_duration > 0.5:
                last_speech_time = time.time()
                if not recording_started:
                    recording_started = True
                    recording_start_time = time.time()

                recorded_frames.extend(audio_buffer)
                audio_buffer = []

            else:
                if recording_started:
                    silence_elapsed = time.time() - last_speech_time  # type: ignore
                    recording_elapsed = time.time() - recording_start_time # type: ignore

                    # Check max recording duration (added)
                    if recording_elapsed >= max_recording_duration:
                        logging.info(f"Max recording duration {max_recording_duration}s\
                                      reached, stopping.")
                        break

                    # Only stop if silence passed AND minimum recording time is reached
                    if silence_elapsed >= silence_duration_to_stop and \
                        recording_elapsed >= min_recording_duration:
                        logging.info(f"Silence for {silence_elapsed:.2f}s \
                                     after speech and minimum recording time reached, stopping.")
                        break
                    else:
                        recorded_frames.extend(audio_buffer)
                        audio_buffer = []

                else:
                    # Not recording yet, limit buffer to prevent memory bloat
                    max_buffer_samples = int(buffer_duration * sample_rate * 5)
                    if sum(len(c) for c in audio_buffer) > max_buffer_samples:
                        audio_buffer.pop(0)

    finally:
        stream.stop_stream()
        stream.close()
        pa.terminate()

    if not recorded_frames:
        logging.info("No speech was detected. Returning None.")
        return None

    recorded_audio = np.concatenate(recorded_frames)

    return recorded_audio


class AudioRecordingAPI(Resource):
    """
    API Resource to trigger audio recording using Silero
    VAD and return audio as base64.
    """

    def post(self):
        """
        Handle POST request to start audio recording and return audio as base64.

        Expected JSON body:
        {
            "silence_duration_to_stop": float,  # Optional, default is 3.0
            "min_recording_duration": float,    # Optional, default is 5.0
            "max_recording_duration": float     # Optional, default is 30.0
        }

        Returns:
        -------
        JSON:
            - status: "success" or "error"
            - audio: Base64-encoded audio data (if successful)
            - message: Error message (if any failure occurs)
        """
        try:
            # Parse incoming JSON request.
            data = request.get_json()

            # Get parameters with defaults.
            silence_duration = data.get('silence_duration_to_stop', 3.0)
            min_duration = data.get('min_recording_duration', 5.0)
            max_duration = data.get('max_recording_duration', 30.0)

            # Start recording using Silero VAD.
            audio_data = record_audio_with_silero_vad(
                silence_duration_to_stop=silence_duration,
                min_recording_duration=min_duration,
                max_recording_duration=max_duration)

            if audio_data is None:
                return jsonify({
                    "status": "error",
                    "message": "No speech detected or recording duration too short."
                }), 400

            # Convert the audio to base64.
            audio_b64 = encode_audio_to_base64(audio_data)

            return jsonify({
                "status": "success",
                "audio": audio_b64
            })

        except ValueError as ve:
            logger.error(f"ValueError: {ve}")
            return jsonify({
                "status": "error",
                "message": str(ve)
            }), 400

        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            return jsonify({
                "status": "error",
                "message": "An unexpected error occurred."
            }), 500


# Add the resources to the Flask app.
api.add_resource(AudioRecordingAPI, "/record")
api.add_resource(HealthCheckAPI, "/health")



if __name__ == "__main__":

    # Run the VAD server.
    app.run(
        host="0.0.0.0",
        port=8012,
        debug=True)
