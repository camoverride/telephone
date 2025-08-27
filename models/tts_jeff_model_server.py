import os
import re
import torch
from flask import Flask, request, make_response
from flask_restful import Api, Resource
from TTS.api import TTS # type: ignore
import tempfile



# Detect device
device = "cuda" if torch.cuda.is_available() else "cpu"

# Global model variable
tts_model = None


def init_tts_model():
    global tts_model
    if tts_model is None:
        print("Initializing TTS model...")
        tts_model = TTS("tts_models/multilingual/multi-dataset/xtts_v2").to(device)
    return tts_model


def text_to_speech(text: str, save_dir: str) -> str:
    safe_text = re.sub(r'\W+', '_', text.strip())[:50]
    filename = f"{safe_text}.wav"
    full_path = os.path.join(save_dir, filename)
    os.makedirs(save_dir, exist_ok=True)

    model = init_tts_model()
    model.tts_to_file(
        text=text,
        speaker_wav="jeff_90s_mono_16k.wav",
        language="en",
        file_path=full_path
    )
    return full_path


class TextToSpeechAPI(Resource):
    def post(self):
        try:
            data = request.get_json(force=True)
            if not data or 'text' not in data:
                return {"status": "error", "message": "Missing 'text' field in request body."}, 400

            input_text = data['text'].strip()
            if not input_text:
                return {"status": "error", "message": "'text' field cannot be empty."}, 400

            model = init_tts_model()

            # Use a temporary file to save the audio
            with tempfile.NamedTemporaryFile(suffix=".wav") as tmp_file:
                model.tts_to_file(
                    text=input_text,
                    speaker_wav="jeff_90s_mono_16k.wav",
                    language="en",
                    file_path=tmp_file.name
                )
                tmp_file.seek(0)
                audio_data = tmp_file.read()

            # Return audio as a binary response
            response = make_response(audio_data)
            response.headers.set('Content-Type', 'audio/wav')
            response.headers.set('Content-Disposition', 'attachment', filename='tts_output.wav')
            return response

        except Exception as e:
            return {"status": "error", "message": str(e)}, 500


# Flask app setup
app = Flask(__name__)
api = Api(app)

# Add resource to API
api.add_resource(TextToSpeechAPI, "/tts")



if __name__ == "__main__":
    # Initialize model before starting the server
    init_tts_model()

    # Run the TTS server.
    app.run(
        host="0.0.0.0",
        port=5000,
        debug=False,
        use_reloader=False)