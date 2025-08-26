from ..utils_apis import KillableFunctionRunner, record_audio_api, \
    speech_to_text_api, response_api, text_to_speech_api
from utils_gpio import phone_picked_up
from utils_play_audio import play_audio


"""
First start each of the 4 servers by running:

    python _silero_vad.py
    python _speech_to_text.py
    python _response.py
    python _text_to_speech.py
"""

##### VAD (Listening) #####
vad_runner = KillableFunctionRunner(
    func=record_audio_api,
    killer=phone_picked_up)

try:
    audio = vad_runner.start(
        silence_duration_to_stop=3,
        min_recording_duration=5,
        max_recording_duration=25,
        recording_api_url="http://localhost:8010/record")

except Exception as e:
    print(f"Error during VAD!")



##### ASR (Speech Recognition) #####
asr_runner = KillableFunctionRunner(
    func=speech_to_text_api,
    killer=phone_picked_up)

try:
    transcription = asr_runner.start(
        audio_b64=audio,
        model="vosk",
        asr_server_url="http://localhost:8011/asr")

    print(f"Transcription: {transcription}")

except Exception as e:
    print(f"Error during ASR!")



##### Response (Thinking) #####
response_runner = KillableFunctionRunner(
    func=response_api,
    killer=phone_picked_up)

try:
    response = response_runner.start(
        text=transcription,
        model="deepseek",
        response_api_url="http://localhost:8012/response")

    print(f"Response: {response}")

except Exception as e:
    print(f"Error during Thinking: {str(e)}")



##### TTS (Text to Speech) #####
tts_runner = KillableFunctionRunner(
    func=text_to_speech_api,
    killer=phone_picked_up)

try:
    audio_path = tts_runner.start(
        output_audio_path="__output.wav",
        text=response,
        model="google_tts",
        language="en",
        tts_server_url="http://localhost:8013/tts")

    print(f"Audio file created at: {audio_path}")

except Exception as e:
    print(f"Error during TTS: {str(e)}")



##### Play the audio #####
recording = play_audio(
    filepath="__output.wav",
    start_delay=0,
    looping=False,
    blocking=True,
    killable=True)
recording.start()
