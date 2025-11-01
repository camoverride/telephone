import logging
import time
from utils_simple import get_random_file, save_audio
from utils_apis import vad #, asr, respond, tts
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
            random_prompt = None
            beep = None
            listening_background_music = None
            closing_prompt = None
            hang_up_tone = None


            try:
                logging.info("--------STARTING NEW INTERACTION--------")
                # Opening sound.
                starting_audio = "prompts/0_pick_up/lets_chat_google.wav"

                # Play beginning (phone picked up) prompt
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

                # Play a random audio file.
                randomly_selected_audio_file = get_random_file("CAM_party_files")

                start_timer = time.time()
                logger.info("Playing randomly selected audio file.")
                random_prompt = play_audio(
                    filepath=randomly_selected_audio_file,
                    start_delay=0.5,
                    looping=False,
                    blocking=True,
                    killable=True)
                random_prompt.start()
                random_prompt.stop()

                # Interrupt the starting prompt and randomly selected audio.
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

                        # Save the audio.
                        save_audio(
                            filepath=audio,
                            save_folder="CAM_party_files")
                        
                        # Play the closing prompt.
                        logger.info("Playing closing prompt.")
                        closing_prompt = play_audio(
                            filepath="prompts/CAM_closing_prompt.wav",
                            start_delay=0.5,
                            looping=False,
                            blocking=True,
                            killable=True)
                        closing_prompt.start()
                        closing_prompt.stop()

                        # Clean up sounds.
                        if recording_prompt:
                            recording_prompt.stop()
                        if random_prompt:
                            random_prompt.stop()
                        if beep:
                            beep.stop()
                        if listening_background_music:
                            listening_background_music.stop()
                        if closing_prompt:
                            closing_prompt.stop()

                        # Clean-up sound
                        hang_up_tone = play_audio(
                            filepath="prompts/5_end_prompt/hang_up_tone.mp3",
                            start_delay=0,
                            looping=True,
                            blocking=True,
                            killable=True)
                        hang_up_tone.start()

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
                if random_prompt:
                    random_prompt.stop()
                if beep:
                    beep.stop()
                if listening_background_music:
                    listening_background_music.stop()
                if closing_prompt:
                    closing_prompt.stop()
                if hang_up_tone:
                    hang_up_tone.stop()
                time.sleep(1)

        else:
            time.sleep(0.1)
