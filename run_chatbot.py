import time
import yaml
import logging
from utils import phone_picked_up, play_audio, ignored_phrases, print_text
from _silero_vad import killable_record_audio_silero
from _speech_to_text import killable_speech_to_text
from _response import get_response, killable_get_response
from _text_to_speech import text_to_speech # TODO: needs killable TTS



# Set up logging configuration.
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s')

# Load config file.
with open("config.yaml", "r") as f:
    config = yaml.safe_load(f)

# Define sounds that will be played and might need to be closed.
starting_prompt = None
beep = None
thinking_sound = None
hang_up_sound = None


def main():
    # Main event loop that should always run, catching errors and continuing
    # from the beginning if the phone reciever is put down.
    while True:
        try:
            ########## STEP 1: Starting Prompt ##########
            # Play starting prompt at beginning of interaction.
            if phone_picked_up():
                logging.info("--- Playing starting prompt")

                # Play the prompt after a delay. Closes automatically because looping=False.
                starting_prompt = play_audio(
                    filepath=config["starting_audio_prompt"],
                    start_delay=config["prompt_start_delay"],
                    looping=False,
                    blocking=True,
                    killable=True)
                starting_prompt.start()

                # Play the beep sound. Closes automatically because looping=False.
                beep = play_audio(
                    filepath=config["prompt_closing_sound"],
                    start_delay=0,
                    looping=False,
                    blocking=True,
                    killable=True)
                beep.start()

            # If the phone is not picked up, restart the while loop.
            else:
                continue

            
            ########## STEP 2: Record speech using VAD ##########
            # Record speech from the user, stopping the recording when the user stops speaking.
            if phone_picked_up():
                logging.info("--- Recording audio")

                # Play the recording sound. Keeps looping until closed.
                recording_sound = play_audio(
                    filepath=config["recording_background_sound"],
                    start_delay=0,
                    looping=True,
                    blocking=False,
                    killable=True)
                recording_sound.start()

                # Start recording audio using VAD.
                audio_input_filepath = \
                    killable_record_audio_silero(
                        save_filepath="_input_tmp.wav",
                        silence_duration_to_stop=config["silence_timeout"],
                        min_recording_duration=config["min_recording_duration"],
                        max_recording_duration=config["max_recording_duration"])

                logging.debug(f"Saved audio to : \
                    {audio_input_filepath}")

                # Stop the recording sound.
                recording_sound.stop()

            # If the phone is not picked up, restart the while loop.
            else:
                continue


            ########## STEP 3: Speech Recognition ##########
            if phone_picked_up():
                logging.info("--- Performing ASR")

                # Play the "thinking" sound. Keeps looping until closed.
                # NOTE: this plays all the way through step 5.
                thinking_sound = play_audio(
                    filepath=config["thinking_sound"],
                    start_delay=0,
                    looping=True,
                    blocking=False,
                    killable=True)
                thinking_sound.start()

                # Perform Speech recognition on the audio file.
                input_text = \
                    killable_speech_to_text(
                        audio_file_path="_input_tmp.wav",
                        model=config["speech_to_text_model"])

                logging.info(f"Recognized text :  {input_text}")

                # Check if the audio input should be ignored 
                # (empty, contains profanity, etc.)
                if input_text:
                    if ignored_phrases(input_text):
                        logging.info("IGNORING INPUT, continuing")
                        continue

            # If the phone is not picked up, restart the while loop.
            else:
                continue


            ########## STEP 4: Response generation ##########
            if phone_picked_up():
                logging.info("--- Generating response")

                # Try using the model from the config. If it fails, use a backup model.
                try:
                    response_text = killable_get_response(
                        text=input_text,
                        model=config["response_model"])

                    logging.info(f"Generated response text : {response_text}")

                # If there is an exception, try a fall-back model.
                except Exception as e:
                    logging.warning(e)
                    logging.warning("Trying fallback response model: DEEPSEEK")
                    response_text = get_response(
                        text=input_text,
                        model=config["fallback_response_model"])

                    logging.info(f"Generated response text [fallback model]: \
                                    {response_text}")

            # If the phone is not picked up, restart the while loop.
            else:
                continue


            ########## STEP 5: Text to speech ##########
            if phone_picked_up():
                logging.info("--- Text to speech")

                # Create output file with response.
                audio_output_filepath = text_to_speech(
                    text=response_text,
                    output_audio_path="_output_tmp.wav",
                    model=config["text_to_speech_model"])

                logging.info(f"Saved output text : {audio_output_filepath}")

            # If the phone is not picked up, restart the while loop.
            else:
                continue


            ########## STEP 6: Play audio! ##########
            if phone_picked_up():
                logging.info("--- Playing output")

                # Stop the "thinking sound" that has been playing since Step 3.
                thinking_sound.stop()

                # Play the response.
                response_audio = play_audio(
                    filepath="_output_tmp.wav",
                    start_delay=0,
                    looping=False,
                    blocking=True,
                    killable=True)
                response_audio.start()

            # If the phone is not picked up, restart the while loop.
            else:
                continue


            ########## STEP 7: Final actions ##########
            # Print the resulting text.
            # print_text(
            #     text=response_text,
            #     printer_api=config["printer_server_url"])
            # logging.info("Printing the text")

            # Play the hang up sound.
            hang_up_sound = play_audio(
                    filepath=config["end_interaction_sound"],
                    start_delay=0,
                    looping=True,
                    blocking=True,
                    killable=True)
            hang_up_sound.start()


        # If there is an exception, continue.
        except Exception as e:
            logging.warning("TOP LEVEL EXCEPTION!")
            logging.warning(e)
            continue

        # Stop any dangling sounds, if they still exist.
        finally:
            if starting_prompt:
                starting_prompt.stop()
            if beep:
                beep.stop()
            if thinking_sound:
                thinking_sound.stop()
            if hang_up_sound:
                hang_up_sound.stop()

        # Small pause to prevent overheating and CPU from running too often.
        # Runs at the end of every loop through the response cycle.
        time.sleep(0.1)



if __name__ == "__main__":

    # TODO: move config down here and load into function args, to add transparency
    main()


    """
    TODO: all functions should have the OPTION to be killable!
    ---- generic killable function wrapper!

    asr model is loaded each loop, meaning it is slow and begins to miss the beginnins
    """