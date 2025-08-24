import time
import yaml
import logging
from _speech_to_text import speech_to_text, killable_speech_to_text
from _response import get_response, killable_get_response
from _text_to_speech import text_to_speech
from utils import play_prompt, phone_picked_up, ignored_phrases, \
    record_audio, play_audio, print_text, start_audio_loop, stop_audio_loop, \
    play_audio_interruptible
from _silero_vad import record_audio_with_silero_vad, killable_record_audio_silero



# Set up logging configuration.
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s')


# Load config file.
with open("config.yaml", "r") as f:
    config = yaml.safe_load(f)


def main():
    # Main event loop that should always run, catching errors and continuing
    # from the beginning if the phone reciever is put down.
    while True:
        try:
            ########## STEP 1: Starting Prompt ##########
            # Play starting prompt at beginning of interaction.
            if phone_picked_up():
                logging.info("--- Playing starting prompt")

                # Requires latency or this loop will run too often, consuming system resources.
                time.sleep(0.1)

                # Play the prompt and a "closing sound" (e.g. "beep") after a delay.
                play_prompt(
                    prompt_start_delay=config["prompt_start_delay"],
                    starting_audio_prompt_dir=config["starting_audio_prompt_dir"],
                    prompt_closing_sound=config["prompt_closing_sound"])
            
            # If the phone is not picked up, restart the while loop.
            else:
                continue

            
            ########## STEP 2: Record speech using VAD ##########
            # Record speech from the user, stopping the recording when the user stops speaking.
            if phone_picked_up():
                # Track this audio process to kill later.
                recording_background_noise_process = None

                try:
                    logging.info("--- Recording audio")

                    # Play a background sound from `prompts/3_waiting_for_user_input`
                    print("---1---")
                    recording_background_noise_process = \
                        start_audio_loop(looping_sound=config["recording_background_sound"])

                    # Record and save audio from the user, ending the recording once
                    # there has been either a gap in the speech `silence_timeout` or
                    # `max_recording_duration` has been reached.
                    print("---2--")
                    audio_input_filepath = \
                        killable_record_audio_silero(
                            save_filepath="_input_tmp.wav",
                            silence_duration_to_stop=config["silence_timeout"],
                            min_recording_duration=config["min_recording_duration"],
                            max_recording_duration=config["max_recording_duration"])
        
                    print("---3---")
                    logging.debug(f"Saved audio to : \
                        {audio_input_filepath}")

                # Log all exceptions.
                except Exception as e:
                    logging.warning(e)

                    # Restart the while loop.
                    continue

                # Make sure to clean up the background process.
                finally:
                    if recording_background_noise_process:
                        stop_audio_loop(recording_background_noise_process)

            # If the phone is not picked up, restart the while loop.
            else:
                print("NNNNN")
                continue


            ########## STEP 3: Speech Recognition ##########
            if phone_picked_up():
                # Track this audio process to kill later.
                asr_tts_background_noise_process = None

                try:
                    logging.info("--- Performing ASR")

                    # Play a background sound from `prompts/4_thinking`.
                    # NOTE: this continues through ASR, response, and TTS steps.
                    asr_tts_background_noise_process = \
                        start_audio_loop(looping_sound="prompts/4_thinking/chime_waiting_faster.wav")

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
                    else:
                        continue

                # Log all exceptions.
                except Exception as e:
                    logging.warning(e)

                    # Make sure to clean up the background process.
                    # This same sound should be continued through 
                    # the next step if there is no error.
                    if asr_tts_background_noise_process:
                        stop_audio_loop(asr_tts_background_noise_process)

                    # Restart the while loop.
                    continue

            # If the phone is not picked up, restart the while loop.
            else:
                continue


            ########## STEP 4: Response generation ##########
            response_text = None

            if phone_picked_up():

                logging.info("--- Generating response")
                try:
                    # Try using the model from the config. 
                    # If it fails, use a backup model.
                    response_text = get_response(
                        text=input_text,
                        model=config["response_model"])
                    
                    logging.info(f"Generated response text : {response_text}")

                # If there is an exception, try a fall-back model.
                except Exception as e:
                    logging.warning(e)

                    # Fallback model.
                    try:
                        logging.info("Trying fallback response model: DEEPSEEK")
                        response_text = get_response(
                            text=input_text,
                            model=config["fallback_response_model"])
                        
                        logging.info(f"Generated response text [fallback model]: \
                                     {response_text}")

                    # If the fallback model also fails, restart the while loop.
                    except:
                        # Make sure to clean up the background process.
                        # This same sound should be continued through 
                        # the next step if there is no error.
                        if asr_tts_background_noise_process:
                            stop_audio_loop(asr_tts_background_noise_process)
                        continue


            # If the phone is not picked up, restart the while loop.
            else:
                # Make sure to clean up the background process.
                # This same sound should be continued through 
                # the next step if there is no error.
                if asr_tts_background_noise_process:
                    stop_audio_loop(asr_tts_background_noise_process)
                continue

            # If STEP 5 failed to generate a response, continue.
            if response_text == None:
                continue


            ########## STEP 5: Text to speech ##########
            if phone_picked_up():
                logging.info("--- Text to speech")

                try:
                    # Create output file with response.
                    audio_output_filepath = text_to_speech(
                        text=response_text,
                        output_audio_path="_output_tmp.wav",
                        model=config["text_to_speech_model"])

                    logging.info(f"Saved output text : {audio_output_filepath}")

                except Exception as e:
                    logging.warning(e)
                    continue

            else:
                # Make sure to clean up the background process.
                # This same sound should be continued through 
                # the next step if there is no error.
                if asr_tts_background_noise_process:
                    stop_audio_loop(asr_tts_background_noise_process)
                    
                continue

            # Make sure to clean up the background process.
            # This same sound should be continued through 
            # the next step if there is no error.
            if asr_tts_background_noise_process:
                stop_audio_loop(asr_tts_background_noise_process)



            ########## STEP 6: Play audio! ##########
            if phone_picked_up(): # TODO: make this killable
                logging.info("--- Playing output")

                play_audio(filename=audio_output_filepath)

            else:
                continue



            ########## STEP 7: Final actions ##########
            try:
                # Print the resulting text
                print_text(
                    text=response_text,
                    printer_api=config["printer_server_url"])
                logging.info("Printing the text")

            # Continue to the next step even if this fails.
            except Exception as e:
                logging.warning(e)
                continue

            # Play final "pick up your haiku"
            play_audio_interruptible(
                filepath="prompts/5_end_prompt/hang_up_tone.mp3",
                looping=False)

            # Play the disconnected sound until the phone is returned to the hook.
            play_audio_interruptible(
                filepath="prompts/5_end_prompt/hang_up_tone.mp3",
                looping=True)


        except Exception as e:
            logging.warning("TOP LEVEL EXCEPTION!")
            logging.warning(e)

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