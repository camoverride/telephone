import logging
import time
from utils_simple import get_audio_file_paths_open_call
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



if __name__ == "__main__":

    while True:
        # If the phone is picked up, begin playing audio.
        if phone_picked_up(throw_error=False):
            recording_prompt = None
            random_prompt = None
            beep = None
            listening_background_music = None
            closing_prompt = None
            hang_up_tone = None


            try:
                logging.info("--------PLAY AUDIO--------")
                # Select the intro file and music file.
                intro_file_path, music_file_path = \
                    get_audio_file_paths_open_call("open_call")

                # Play the intro file.
                logger.info(f"Playing intro file: {intro_file_path}")
                intro_file = play_audio(
                    filepath=intro_file_path,
                    start_delay=0.5,
                    looping=False,
                    blocking=True,
                    killable=True)
                intro_file.start()
                intro_file.stop()

                # Play the music file.
                logger.info(f"Playing intro file: {music_file_path}")
                music_file = play_audio(
                    filepath=music_file_path,
                    start_delay=0.5,
                    looping=False,
                    blocking=True,
                    killable=True)
                music_file.start()
                music_file.stop()

                # Clean-up sound.
                hang_up_tone = play_audio(
                    filepath="prompts/5_end_prompt/hang_up_tone.mp3",
                    start_delay=0.5,
                    looping=True,
                    blocking=True,
                    killable=True)
                hang_up_tone.start()

            # Top level exceptions are triggered by errors.
            except Exception as e:
                logger.warning("Top level exception!")
                logger.warning(e)
                continue
    
            # Clean up all sounds.
            finally:
                if intro_file:
                    intro_file.stop()
                if music_file:
                    music_file.stop()
                if hang_up_tone:
                    hang_up_tone.stop()
                time.sleep(1)

        # If the phone is not picked up, keep waiting.
        else:
            time.sleep(0.1)
