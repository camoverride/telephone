import logging
import time
from utils_simple import get_random_file
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

            audio_playback = None
            pause_sound = None

            try:
                logging.info("-------- STARTING NEW PLAYBACK --------")
                # Randomly selected audio file.
                audio_filepath = get_random_file("CAM_audio_files/files")

                ##### Play beginning (phone picked up) prompts #####
                start_timer = time.time()
                logger.info("Playing interaction starting prompt.")
                audio_playback = play_audio(
                    filepath=audio_filepath,
                    start_delay=0.5,
                    looping=False,
                    blocking=True,
                    killable=True)
                audio_playback.start()
                audio_playback.stop()

                pause_sound = play_audio(
                    filepath="CAM_audio_files/pause.wav",
                    start_delay=0,
                    looping=False,
                    blocking=True,
                    killable=True)
                pause_sound.start()
                pause_sound.stop()

            
            # Top level exceptions are triggered by errors.
            except Exception as e:
                logger.warning("Top level exception!")
                logger.warning(e)
                continue
    
            # Clean up all sounds.
            finally:
                if audio_playback:
                    audio_playback.stop()
                if pause_sound:
                    pause_sound.stop()
                time.sleep(1)

        else:
            time.sleep(0.1)
