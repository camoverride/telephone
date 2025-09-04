import logging
import time
from utils import get_random_file
from utils_apis import vad, asr, respond, tts
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



if __name__ == "__main__":

    while True:
        if phone_picked_up(throw_error=False):
            recording_prompt = None
            beep = None
            listening_background_music = None
            thinking_background_music = None
            reply_audio = None
            try:
                logging.info("--------STARTING NEW INTERACTION--------")
                # Opening sound.
                starting_audio = "prompts/0_pick_up/lets_chat_google.wav"

                ##### Play beginning (phone picked up) prompts #####
                start_timer = time.time()
                logger.info("Playing interaction starting prompt.")
                recording_prompt = play_audio(
                    filepath=starting_audio,
                    start_delay=0.5,
                    looping=False,
                    blocking=True,
                    killable=True)
                recording_prompt.start()
                recording_prompt.stop()

                beep = play_audio(
                    filepath="prompts/2_start_reply/beep_soft.wav",
                    start_delay=0,
                    looping=False,
                    blocking=True,
                    killable=True)
                beep.start()
                beep.stop()


                # Main ASR / Response / TTS event loop.
                while True:
                    if phone_picked_up():
                        ##### VAD (Listening) #####
                        # Play the listening sound.
                        listening_background_music = play_audio(
                            filepath="prompts/3_waiting_for_user_input/musical_soft_background_softer.wav",
                            start_delay=0,
                            looping=True,
                            blocking=False,
                            killable=True)
                        listening_background_music.start()

                        # Calculate VAD time.
                        start_timer = time.time()
                        logger.info("Starting VAD")
                        audio = vad()
                        logger.info(f"Completed VAD in [{time.time() - start_timer}]")

                        # Stop audio and start over.
                        if not audio:
                            logger.warning("No audio detected. Skipping this round.")
                            logger.info(END_SIGN)
                            listening_background_music.stop()
                            continue

                        ##### ASR (Speech Recognition) #####
                        # Calculate ASR time.
                        start_timer = time.time()
                        logger.info("Starting ASR")
                        transcription = asr(audio)
                        logger.info(f"Completed ASR in [{time.time() - start_timer}] ")
                        logger.info(f"    > {transcription}")

                        # Stop the "listening" music.
                        listening_background_music.stop()

                        # Stop audio and start over.
                        if not transcription:
                            logger.warning("No transcription. Skipping this round.")
                            logger.info(END_SIGN)
                            listening_background_music.stop()
                            continue

                        ##### Response (Thinking) #####
                        # Get a filler "thinking sound" to play once.
                        thinking_file_path = get_random_file("prompts/4_thinking/google")
                        thinking_background_music = play_audio(
                            filepath=thinking_file_path,
                            start_delay=0,
                            looping=False,
                            blocking=False,
                            killable=True)
                        thinking_background_music.start()

                        # Calculate response time.
                        start_timer = time.time()
                        logger.info("Starting Response")
                        response = respond(transcription)
                        logger.info(f"Completed Response in [{time.time() - start_timer}] ")
                        logger.info(f"    > {response}")

                        # Stop audio and start over.
                        if not response:
                            logger.warning("No response. Skipping this round.")
                            logger.info(END_SIGN)
                            thinking_background_music.stop()
                            continue

                        #### TTS (Text to Speech) #####
                        # Calculate TTS time.
                        start_timer = time.time()
                        logger.info("Starting TTS")
                        audio_file_path = tts(response)
                        logging.info(f"Completed TTS in [{time.time() - start_timer}] ")
                        logger.info(f"    > {audio_file_path}")

                        # Stop audio and start over.
                        if not audio_file_path:
                            logger.warning("No file generated. Skipping this round.")
                            logger.info(END_SIGN)
                            thinking_background_music.stop()
                            continue

                        # Stop the "thinking" audio.
                        thinking_background_music.stop()

                        ##### Play the response from the bot #####
                        # Record how long the utterance it.
                        start_timer = time.time()
                        logger.info("Playing audio.")

                        # Play the response.
                        reply_audio = play_audio(
                            filepath=audio_file_path,
                            start_delay=0,
                            looping=False,
                            blocking=True,
                            killable=True)
                        reply_audio.start()
                        logger.info(f"Finished playing audio in [{time.time() - start_timer}]")
                        logger.info(END_SIGN)


                        # Clean up sounds.
                        if recording_prompt:
                            recording_prompt.stop()
                        if beep:
                            beep.stop()
                        if listening_background_music:
                            listening_background_music.stop()
                        if thinking_background_music:
                            thinking_background_music.stop()
                        if reply_audio:
                            reply_audio.stop()

                    # Phone not picked up!
                    # Should return to the beginning.
                    else:
                        time.sleep(0.1)
                        continue

            
            # Top level exceptions are triggered by errors.
            except Exception as e:
                logger.warning("Top level exception!")
                logger.warning(e)
                continue
    
            # Clean up all sounds.
            finally:
                if recording_prompt:
                    recording_prompt.stop()
                if beep:
                    beep.stop()
                if listening_background_music:
                    listening_background_music.stop()
                if thinking_background_music:
                    thinking_background_music.stop()
                if reply_audio:
                    reply_audio.stop()
                time.sleep(1)

        else:
            time.sleep(0.1)
