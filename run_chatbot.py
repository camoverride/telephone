import logging
import time
from utils_apis import KillableFunctionRunner, record_audio_api, \
    speech_to_text_api, response_api, text_to_speech_api
from utils_gpio import phone_picked_up
from utils_play_audio import play_audio



# Set up logging configuration.
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        # Print logs to the console.
        logging.StreamHandler(),
        # Write logs to a file.
        logging.FileHandler("logs/main.log")])
logger = logging.getLogger(__name__)
END_SIGN = "------------------------------------------"


def vad():
    """
    VAD wrapper function.
    """
    vad_runner = KillableFunctionRunner(
        func=record_audio_api,
        killer=phone_picked_up)

    try:
        audio = vad_runner.start(
            silence_duration_to_stop=1, # 3
            min_recording_duration=2, # 5
            max_recording_duration=10, # 25
            recording_api_url="http://localhost:8010/record")
        
        return audio

    except Exception as e:
        print(f"Error during VAD!")
        return None


def asr(audio):
    """
    ASR wrapper funtion.
    """
    asr_runner = KillableFunctionRunner(
        func=speech_to_text_api,
        killer=phone_picked_up)

    try:
        transcription = asr_runner.start(
            audio_b64=audio,
            model="vosk",
            asr_server_url="http://localhost:8011/asr")

        return transcription

    except Exception:
        print(f"Error during ASR!")
        return None


def respond(transcription):
    """
    Response wrapper.
    """
    response_runner = KillableFunctionRunner(
        func=response_api,
        killer=phone_picked_up)

    try:
        response = response_runner.start(
            text=transcription,
            model="deepseek",
            response_api_url="http://localhost:8012/response")

        return response

    except Exception as e:
        print(f"Error during Thinking: {str(e)}")
        return None


def tts(response):
    tts_runner = KillableFunctionRunner(
        func=text_to_speech_api,
        killer=phone_picked_up)

    try:
        audio_path = tts_runner.start(
            output_audio_path="__output.wav",
            text=response,
            model="jeff",
            language="en",
            tts_server_url="http://localhost:8013/tts")

        return audio_path

    except Exception as e:
        print(f"Error during TTS: {str(e)}")
        return None


if __name__ == "__main__":
    """
    First start each of the 4 servers by running:

        python _silero_vad.py
        python _speech_to_text.py
        python _response.py
        python _text_to_speech.py
    """
    while True:
        logging.info("--------STARTING NEW INTERACTION--------")
        while True:
            try:
                if phone_picked_up():
                    ##### VAD (Listening) #####
                    try:
                        start_timer = time.time()
                        logger.info("Starting VAD")
                        audio = vad()
                        logger.info(f"Completed VAD in [{time.time() - start_timer}]")

                        if not audio:
                            logger.warning("No audio detected. Skipping this round.")
                            logger.info(END_SIGN)
                            continue
                    except Exception as e:
                        logging.warning(e)
                        continue

                    ##### ASR (Speech Recognition) #####
                    start_timer = time.time()
                    logger.info("Starting ASR")
                    transcription = asr(audio)
                    logger.info(f"Completed ASR in [{time.time() - start_timer}] ")
                    logger.info(f"    > {transcription}")

                    if not transcription:
                        logger.warning("No transcription. Skipping this round.")
                        logger.info(END_SIGN)
                        continue

                    ##### Response (Thinking) #####
                    start_timer = time.time()
                    logger.info("Starting Response")
                    response = respond(transcription)
                    logger.info(f"Completed Response in [{time.time() - start_timer}] ")
                    logger.info(f"    > {response}")

                    if not response:
                        logger.warning("No response. Skipping this round.")
                        logger.info(END_SIGN)
                        continue

                    #### TTS (Text to Speech) #####
                    start_timer = time.time()
                    logger.info("Starting TTS")
                    audio_file_path = tts(response)
                    logging.info(f"Completed TTS in [{time.time() - start_timer}] ")
                    logger.info(f"    > {audio_file_path}")

                    if not audio_file_path:
                        logger.warning("No file generated. Skipping this round.")
                        logger.info(END_SIGN)
                        continue

                    ##### Play the audio #####
                    start_timer = time.time()
                    logger.info("Playing audio.")
                    recording = play_audio(
                        filepath=audio_file_path,
                        start_delay=0,
                        looping=False,
                        blocking=True,
                        killable=True)
                    recording.start()
                    logger.info(f"Finished playing audio in [{time.time() - start_timer}] ")
                    logger.info(END_SIGN)
                else:
                    time.sleep(2)

            except:
                time.sleep(5)
                continue