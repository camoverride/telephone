import logging
import time
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
                # starting_audio = choose_from_dir("prompts/1_start_prompt/jeff_starts")
                # starting_audio = "prompts/0_begin_interaction/hello.wav"
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

                while True:
                    if phone_picked_up():
                        ##### VAD (Listening) #####
                        # Play the listening sound
                        listening_background_music = play_audio(
                            filepath="prompts/3_waiting_for_user_input/musical_soft_background_softer.wav",
                            start_delay=0,
                            looping=True,
                            blocking=False,
                            killable=True)
                        listening_background_music.start()

                        start_timer = time.time()
                        logger.info("Starting VAD")
                        audio = vad()
                        logger.info(f"Completed VAD in [{time.time() - start_timer}]")

                        if not audio:
                            logger.warning("No audio detected. Skipping this round.")
                            logger.info(END_SIGN)
                            listening_background_music.stop()
                            continue

                        ##### ASR (Speech Recognition) #####
                        start_timer = time.time()
                        logger.info("Starting ASR")
                        transcription = asr(audio)
                        logger.info(f"Completed ASR in [{time.time() - start_timer}] ")
                        logger.info(f"    > {transcription}")

                        listening_background_music.stop()

                        if not transcription:
                            logger.warning("No transcription. Skipping this round.")
                            logger.info(END_SIGN)
                            listening_background_music.stop()
                            continue

                        ##### Response (Thinking) #####

                        thinking_background_music = play_audio(
                            filepath="prompts/4_thinking/hmm_google_padded.wav",
                            start_delay=0,
                            looping=False,
                            blocking=False,
                            killable=True)
                        thinking_background_music.start()


                        start_timer = time.time()
                        logger.info("Starting Response")
                        response = respond(transcription)
                        logger.info(f"Completed Response in [{time.time() - start_timer}] ")
                        logger.info(f"    > {response}")

                        if not response:
                            logger.warning("No response. Skipping this round.")
                            logger.info(END_SIGN)
                            thinking_background_music.stop()
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
                            thinking_background_music.stop()
                            continue


                        thinking_background_music.stop()


                        ##### Play the audio #####
                        start_timer = time.time()
                        logger.info("Playing audio.")
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
