import time
import yaml
from _speech_to_text import speech_to_text
from _response import get_response
from _text_to_speech import text_to_speech
from utils import phone_picked_up, record_audio, play_audio



# Load config file
with open("config.yaml", "r") as f:
    config = yaml.safe_load(f)



def main():

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

            print(f"Recognized text :  {input_text}")


            # Response generation.
            response_text = get_response(text=input_text,
                                        model=config["response_model"])
            
            print(f"Generated response text : {response_text}")
            

            # Text to speech.
            audio_output_filepath = text_to_speech(text=response_text,
                                                output_audio_path="_output_tmp.wav",
                                                model=config["text_to_speech_model"])
            
            print(f"Saved output text : {audio_output_filepath}")

            # Play audio!
            play_audio(filename=audio_output_filepath)
    
        else:
            time.sleep(0.5)



if __name__ == "__main__":

    main()
