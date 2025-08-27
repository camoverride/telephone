import os
import re
import torch
from flask import Flask, request, make_response
from flask_restful import Api, Resource
from TTS.api import TTS # type: ignore
import tempfile
import soundfile as sf


# Detect device
device = "cuda" if torch.cuda.is_available() else "cpu"

# Global model variable
tts_model = None

SPEAKER_WAV_PATH = "jeff_90s_mono_16k.wav"



def init_tts_model():
    global tts_model, cached_speaker_embedding

    if tts_model is None:
        print("Loading TTS model...")
        tts_model = TTS("tts_models/multilingual/multi-dataset/xtts_v2").to(device)

        # Load and preprocess speaker WAV once
        wav, sr = sf.read(SPEAKER_WAV_PATH)
        wav_tensor = torch.tensor(wav).float().to(device)
        if wav_tensor.dim() == 1:
            wav_tensor = wav_tensor.unsqueeze(0)

        # Compute speaker embedding ONCE here
        cached_speaker_embedding = tts_model.synthesizer.tts_model.get_speaker_embedding(wav_tensor, sr)
        print("Speaker embedding computed once at startup.")

    return tts_model


def text_to_speech(text: str) -> bytes:
    model = init_tts_model()

    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp_file:
        tmp_path = tmp_file.name

    # Use cached speaker embedding directly, NOT the wav file
    model.tts_to_file(
        text=text,
        speaker_embedding=cached_speaker_embedding,  # pass embedding, not wav
        language="en",
        file_path=tmp_path
    )

    with open(tmp_path, "rb") as f:
        audio_data = f.read()
    os.remove(tmp_path)
    return audio_data


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