from gtts import gTTS
import logging
import os
import platform
import pyttsx3
import re
import subprocess



# Set up logging configuration
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s')


def clean_text_for_tts(text : str) -> str:
    """
    Remove characters unwanted for TTS.

    Parameters
    ----------
    text : str
        Some text returned from the response genertor.
    
    Returns
    -------
    str
        Text cleaned of unwanted characters.
    """
    cleaned = re.sub(r'[\*\_\[\]\{\}\(\)\~\^\=\|\\\/<>#@`]', '', text)

    return cleaned


def google_asr(text : str,
               output_audio_path : str):
    """
    Use simple Google to perform TTS.

    Parameters
    ----------
    text : str
        The text to be synthesized.
    output_audio_path : str
        Where the .wav file should be saved.
    
    Returns
    -------
    str
        The `output_audio_path`
    """
    tts = gTTS(text=text, lang='en')
    tts.save(output_audio_path)

    return output_audio_path


def command_line_say(text : str,
                     output_audio_path : str) -> str:
    """
    Use simple command line tools to perform TTS.
    Automatically detects whether we are on Pi or MacOS.

    Parameters
    ----------
    text : str
        The text to be synthesized.
    output_audio_path : str
        Where the .wav file should be saved.
    
    Returns
    -------
    str
        The `output_audio_path`
    """
    # MacOS
    if platform.system() == "Darwin":
        filename_aiff = "temp.aiff"

        # Use macOS TTS to generate AIFF
        subprocess.run(["say", "-o", filename_aiff, text])
        logging.debug(f"Generated AIFF: {filename_aiff}")

        # Convert to WAV using ffmpeg
        subprocess.run(["ffmpeg", "-y", "-i", filename_aiff, output_audio_path],
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        logging.debug(f"Converted to WAV: {output_audio_path}")

        # Cleanup
        os.remove(filename_aiff)

        return output_audio_path
    

    # Linux / Pi
    elif platform.system() == "Linux":
        # Use pyttsx3 to save speech to file
        # NOTE: should use "espeak" instead
        engine = pyttsx3.init()
        engine.save_to_file(text, output_audio_path)
        engine.runAndWait()

        return output_audio_path


def text_to_speech(text : str,
                   output_audio_path : str,
                   model : str) -> str:
    """
    Converts some text to a .wav audio file.

    Parameters
    ----------
    text : str
        The words that will be spoken.
    output_audio_path : str
        Where the .wav file should be saved.
    model : str
        Which model to use. Current models:
            - "say_macos"
                Simple `say` command line utility. NOTE: only MacOS.
            - "pytts_pi"
                PYTTS. NOTE: only on Raspbian.
    Returns
    -------
    str
        The `output_audio_path`
    """
    # Purge unwanted characters from the text
    text = clean_text_for_tts(text)

    # Choose the right model.
    if model == "command_line":
        output_audio_path = command_line_say(text=text,
                                             output_audio_path=output_audio_path)
    if model == "google_tts":
        output_audio_path = google_asr(text=text,
                                       output_audio_path=output_audio_path)

    # Return is not strictly necessary, because it copies one of the args.
    return output_audio_path



if __name__ == "__main__":

    TEXT = "Thanks for picking up. Tell me something about truth, and I'll respond with a haiku."

    google_asr(text=TEXT, output_audio_path="_tmp.wav")
