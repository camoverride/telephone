import time
import yaml
from _speech_to_text import speech_to_text
from _response import get_response
from _text_to_speech import text_to_speech
from utils import play_prompt, phone_picked_up, ignored_phrases, \
    record_audio, play_audio, print_text, start_audio_loop, stop_audio_loop, \
    play_audio_interruptible
from _silero_vad import record_audio_with_silero_vad



# Load config file
with open("config.yaml", "r") as f:
    config = yaml.safe_load(f)


def main():

    while True:
        try:
            # Play prompt
            if phone_picked_up():
                time.sleep(0.5)
                play_prompt(prompt_start_delay=config["prompt_start_delay"],
                            starting_audio_prompt_dir=config["starting_audio_prompt_dir"],
                            prompt_closing_sound=config["prompt_closing_sound"])
            
            else:
                continue


            # Audio recording.
            if phone_picked_up():
                # audio_input_filepath = record_audio(save_filepath="_input_tmp.wav",
                #                                     speech_onset_timeout=config["speech_onset_timeout"],
                #                                     max_duration=config["recording_max_duration"],
                #                                     silence_timeout=config["silence_timeout"])

                audio_input_filepath = record_audio_with_silero_vad(
                                            save_filepath="_input_tmp.wav",
                                            silence_duration_to_stop=config["silence_timeout"],
                                            min_recording_duration=config["min_recording_duration"],
                                            max_recording_duration=config["max_recording_duration"])
    
                print(f"Saved audio to : \
                    {audio_input_filepath}")
                
            else:
                continue


            # Speech to text.
            if phone_picked_up():
                input_text = speech_to_text(audio_file_path=audio_input_filepath,
                                            model=config["speech_to_text_model"])
                
                # Check if the audio input should be ignored (empty, contains profanity, etc.)
                if ignored_phrases(input_text):

                    if ignored_phrases == "hello":
                        print(f"Recognized text :  {input_text}")
                        print("IGNORING - hello message.")

                        continue

                    if ignored_phrases == "nothing":
                        print(f"Recognized text :  {input_text}")
                        print("IGNORING - nothing recognized.")

                        continue

                    if ignored_phrases == "profanity":
                        print(f"Recognized text :  {input_text}")
                        print("IGNORING - contains profanity.")

                        continue


                    continue
                
                else:
                    print(f"Recognized text :  {input_text}")
            
            else:
                continue


            # Response generation.
            if phone_picked_up():
                # Track the audio process so it can be killed later.
                audio_loop_process = None

                try:
                    # Start looped audio playback
                    audio_loop_process = start_audio_loop(looping_sound="prompts/chime_waiting_faster.wav")

                    # Try using the model from the config. If it fails, use a backup model.
                    response_text = get_response(text=input_text,
                                                 model=config["response_model"])
                    
                except Exception as e:
                    print(e)
                    print("Trying fallback response model: DEEPSEEK")
                    response_text = get_response(text=input_text,
                                                 model=config["fallback_response_model"])
                    
                finally:
                    # Always stop the looping audio
                    stop_audio_loop(audio_loop_process)
                    
                print(f"Generated response text : {response_text}")
            
            else:
                continue


            # Text to speech.
            if phone_picked_up():
                audio_output_filepath = text_to_speech(text=response_text,
                                                       output_audio_path="_output_tmp.wav",
                                                       model=config["text_to_speech_model"])
                print(f"Saved output text : {audio_output_filepath}")
            else:
                continue


            # Play audio!
            if phone_picked_up():
                play_audio(filename=audio_output_filepath)


            try:
                # Print the resulting text
                print_text(text=response_text, printer_api=config["printer_server_url"])
                print("Printing the text")

            # Continue to the next step even if this fails.
            except Exception as e:
                print(e)


            # Play the disconnected sound until the phone is returned to the hook.
            play_audio_interruptible(filepath="prompts/hang_up_tone.mp3",
                                     looping=True)
                        


        except Exception as e:
            print(e)
            continue

        # Small pause to prevent overheating and CPU from running too often.
        time.sleep(0.5)



if __name__ == "__main__":

    main()
