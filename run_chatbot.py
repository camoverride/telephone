import time
import yaml
from _speech_to_text import speech_to_text
from _response import get_response
from _text_to_speech import text_to_speech
from utils import phone_picked_up, ignored_phrases, record_audio, play_audio



# Load config file
with open("config.yaml", "r") as f:
    config = yaml.safe_load(f)


SILENCED = False


def main():
    global SILENCED

    while True:

        if phone_picked_up():

            # Audio recording.
            audio_input_filepath = record_audio(save_filepath="_input_tmp.wav",
                                                duration=config["recording_duration"])

            print(f"Saved {config['recording_duration']} seconds of audio to : \
                {audio_input_filepath}")


            # Speech to text.
            input_text = speech_to_text(audio_file_path=audio_input_filepath,
                                        model=config["speech_to_text_model"])
            
            # Check for silencing.
            if input_text == "silence":
                SILENCED = True
            
            if input_text == "continue":
                SILENCED = False

            # Periodically check if the phone has been hung up.
            if SILENCED:
                continue

            # Check if the audio input should be ignored (empty, contains profanity, etc.)
            if ignored_phrases(input_text):
                print("Text contains an ignored phrase!")

                continue

            else:
                print(f"Recognized text :  {input_text}")
            
            # Periodically check if the phone has been hung up.
            if SILENCED:
                continue


            # Response generation.
            response_text = get_response(text=input_text,
                                        model=config["response_model"])
            
            print(f"Generated response text : {response_text}")

            # Periodically check if the phone has been hung up.
            if SILENCED:
                continue
            

            # Text to speech.
            audio_output_filepath = text_to_speech(text=response_text,
                                                output_audio_path="_output_tmp.wav",
                                                model=config["text_to_speech_model"])
            
            print(f"Saved output text : {audio_output_filepath}")

            # Periodically check if the phone has been hung up.
            if SILENCED:
                continue

            # Play audio!
            play_audio(filename=audio_output_filepath)
    
        else:
            time.sleep(0.5)



if __name__ == "__main__":

    main()
