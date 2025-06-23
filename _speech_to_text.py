import wave
import os
import json
from vosk import Model, KaldiRecognizer



def vosk_asr(audio_file_path : str,
             model_path: str) -> str:
    """
    Uses vosk to perform ASR.

    Parameters
    ----------
    audio_file_path : str
        The path to an audio file.
    model_path : str
        Path to the vosk model artifact.

    Returns
    -------
    str
        The speech contained in the text.
    """
    # Check for Vosk model
    if not os.path.exists(model_path):
        raise Exception(f"Vosk model folder '{model_path}' not found.")

    model = Model(model_path)
    audio_file = wave.open(audio_file_path, "rb")
    rec = KaldiRecognizer(model, audio_file.getframerate())
    result_text = ""

    while True:
        data = audio_file.readframes(4000)
        if len(data) == 0:
            break
        if rec.AcceptWaveform(data):
            res = json.loads(rec.Result())
            if "text" in res:
                result_text += res["text"] + " "

    # Get final partial result
    res = json.loads(rec.FinalResult())
    if "text" in res:
        result_text += res["text"]

    result_text = result_text.strip()

    return result_text


def speech_to_text(audio_file_path : str,
                   model : str) -> str:
    """
    Extracts the speech from a given .wav file.

    Parameters
    ----------
    audio_file_path : str
        A .wav file that may or may not contain human speech.
    model : str
        Which model should be used.
    
    Returns
    -------
    str
        The speech contained in the audio, if any exists.
    """
    if model == "vosk":
        result_text = vosk_asr(audio_file_path=audio_file_path,
                               model_path="models/vosk-model-small-en-us-0.15")

    return result_text
