import time
import traceback
import yaml
import logging
from utils import phone_picked_up, play_audio, ignored_phrases, print_text
from _silero_vad import record_audio_with_silero_vad
from _speech_to_text import speech_to_text
from _response import get_response
from _text_to_speech import text_to_speech



# Set up logging configuration.
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s')

# Load config file.
with open("config.yaml", "r") as f:
    config = yaml.safe_load(f)



def main():
    # Define sounds that will be played and might need to be closed.
    starting_prompt = None
    beep = None
    recording_sound = None
    thinking_sound = None
    hang_up_sound = None
    response_audio = None

    # Main event loop that should always run, catching errors and continuing
    # from the beginning if the phone reciever is put down.
    while True:
        try:
            if phone_picked_up():
                ########## STEP 1: Starting Prompt ##########
                # Play starting prompt at beginning of interaction.
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

                ########## STEP 2: Record speech using VAD ##########
                # Record speech from the user, stopping the recording when the user stops speaking.
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
                recorded_audio = \
                    record_audio_with_silero_vad(
                        silence_duration_to_stop=config["silence_timeout"],
                        min_recording_duration=config["min_recording_duration"],
                        max_recording_duration=config["max_recording_duration"])

                # Stop the recording sound.
                if recording_sound and hasattr(recording_sound, "stop"):
                    recording_sound.stop()

                ########## STEP 3: Speech Recognition ##########
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
                if recorded_audio is not None:
                    recognized_text = \
                        speech_to_text(
                            audio=recorded_audio,
                            model=config["speech_to_text_model"])

                logging.info(f"Recognized text :  {recognized_text}")

                # Check if the audio input should be ignored 
                # (empty, contains profanity, etc.)
                if recognized_text:
                    if ignored_phrases(recognized_text):
                        logging.info("IGNORING INPUT, continuing")
                        continue

                ########## STEP 4: Response generation ##########
                logging.info("--- Generating response")

                # Try using the model from the config. If it fails, use a backup model.
                try:
                    if recognized_text:
                        response_text = get_response(
                            text=recognized_text,
                            model=config["response_model"])

                        logging.info(f"Generated response text : {response_text}")
                    else:
                        raise TypeError("input_text is None!")

                # If there is an exception, try a fall-back model.
                except Exception as e:
                    logging.warning(e)
                    logging.warning("Trying fallback response model: DEEPSEEK")
                    config["response_model"] = config["fallback_response_model"]

                    if recognized_text:
                        response_text = get_response(
                            text=recognized_text,
                            model=config["fallback_response_model"])

                        logging.info(f"Generated response text [fallback model]: \
                                        {response_text}")
                    else:
                        raise TypeError("input_text is None!")

                ########## STEP 5: Text to speech ##########
                logging.info("--- Text to speech")

                # Create output file with response.
                if response_text and config["response_model"] == "jeff":
                    output_audio_path = response_text
    
                elif response_text:
                    output_audio_path = text_to_speech(
                        output_audio_path="____af.wav",
                        text=response_text,
                        model=config["text_to_speech_model"])

                else:
                    raise TypeError("response_text is None!")

                ########## STEP 6: Play audio! ##########
                logging.info("--- Playing output")

                # Stop the "thinking sound" that has been playing since Step 3.
                if thinking_sound and hasattr(thinking_sound, "stop"):
                    thinking_sound.stop()

                # Play the response.
                response_audio = play_audio(
                    # filepath="_output_tmp.wav",
                    filepath=output_audio_path, # audio_output
                    start_delay=0,
                    looping=False,
                    blocking=True,
                    killable=True)
                response_audio.start()

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
                    looping=False,
                    blocking=True,
                    killable=True)
                hang_up_sound.start()

            # Small pause to stop the CPU from running this loop constantly.
            else:
                time.sleep(0.1)


        # If there is an exception, continue.
        except Exception as e:
            logging.warning("TOP LEVEL EXCEPTION!")
            logging.warning(traceback.format_exc())
            continue

        # Stop any dangling sounds, if they still exist.
        finally:
            if starting_prompt and hasattr(starting_prompt, "stop"):
                starting_prompt.stop()
            if beep and hasattr(beep, "stop"):
                beep.stop()
            if recording_sound and hasattr(recording_sound, "stop"):
                recording_sound.stop()
            if thinking_sound and hasattr(thinking_sound, "stop"):
                thinking_sound.stop()
            if hang_up_sound and hasattr(hang_up_sound, "stop"):
                hang_up_sound.stop()
            if response_audio and hasattr(response_audio, "stop"):
                response_audio.stop()



if __name__ == "__main__":

    # TODO: move config down here and load into function args, to add transparency
    main()
