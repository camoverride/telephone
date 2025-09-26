from flask import Flask, request, jsonify
from flask_restful import Api, Resource
from gtts import gTTS
import logging
import os
import platform
import pyttsx3
import re
import requests
import subprocess
from typing import Optional
import yaml
from utils import HealthCheckAPI



# Initialize Flask application and RESTful API.
app = Flask(__name__)
api = Api(app)


# Set up logging configuration.
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        # Print logs to the console.
        logging.StreamHandler(),
        # Write logs to a file.
        logging.FileHandler("logs/tts_server.log")])
logger = logging.getLogger(__name__)


# Load config file.
with open("config.yaml", "r") as f:
    config = yaml.safe_load(f)


def clean_text_for_tts(text : str) -> str:
    """
    Remove characters unwanted for TTS.

    Parameters
    ----------
    text : str
        Some text returned from the response generator.

    Returns
    -------
    str
        Text cleaned of unwanted characters.
    """
    cleaned = re.sub(r'[\*\_\[\]\{\}\(\)\~\^\=\|\\\/<>#@`]', '', text)

    return cleaned


def google_tts(
    text : str,
    output_audio_path : str,
    language : str):
    """
    Use Google to perform TTS.

    Parameters
    ----------
    text : str
        The text to be synthesized.
    output_audio_path : str
        Where the .wav file should be saved.
    language : str
        Language. "en", "zh-CN", etc.

    Returns
    -------
    str
        Path to the generated WAV audio file.
    """
    tts = gTTS(text=text,
               lang=language)
    tts.save(output_audio_path)

    return output_audio_path


def command_line_say(
    text : str,
    output_audio_path : str) -> str:
    """
    Use simple command line tools to perform TTS.
    Automatically detects whether we are on Linux or MacOS.

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
    # MacOS.
    if platform.system() == "Darwin":
        filename_aiff = "temp.aiff"

        # Use macOS TTS to generate AIFF.
        subprocess.run(["say", "-o", filename_aiff, text])

        # Convert to WAV using ffmpeg.
        subprocess.run(["ffmpeg", "-y", "-i", filename_aiff, output_audio_path],
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        # Cleanup.
        os.remove(filename_aiff)    

    # Linux / Pi.
    elif platform.system() == "Linux":
        # Use pyttsx3 to save speech to file.
        # NOTE: can use "espeak" instead.
        engine = pyttsx3.init()
        engine.save_to_file(text, output_audio_path)
        engine.runAndWait()

    return output_audio_path


def pytts_asr(
    text : str,
    output_audio_path : str) -> str:
    """
    Use the pyttsx3 platform to perform speech synthesis.

    Parameters
    ----------
    text : str
        The words that will be spoken.
    output_audio_path : str
        Where the .wav file should be saved.

    Returns
    -------
    str
        The `output_audio_path` (a wav file).
    """
    engine = pyttsx3.init()
    engine.save_to_file(text, output_audio_path)
    engine.runAndWait()

    return output_audio_path


def jeff_model(
    text : str,
    server_url : str,
    output_audio_path : str) -> str:

    payload = {"text": text}
    headers = {"Content-Type": "application/json"}

    response = requests.post(server_url, json=payload, headers=headers)

    if response.status_code == 200:
        # Save response.content directly to file
        os.makedirs(os.path.dirname(output_audio_path) or '.', exist_ok=True)
        with open(output_audio_path, 'wb') as f:
            f.write(response.content)
        return output_audio_path
    else:
        raise RuntimeError(f"Server returned error {response.status_code}: {response.text}")


def text_to_speech(
    output_audio_path : str,
    text : str,
    model : str,
    language : str) -> Optional[str]:
    """
    Converts some text to a .wav audio file by performing TTS.

    Parameters
    ----------
    text : str
        The words that will be spoken.
    output_audio_path : str
        Where the .wav file should be saved.
    model : str
        Which model to use. Current models:
            - "command_line"
                Simple `say` command line utility. NOTE: only MacOS.
            - "google_tts"
                Google TTS. NOTE: requires an internet connection.
            - "pytts"    
                Pytts library. NOTE: only on Linux.
    language : str
        Language for tts synthesis. E.g. "en", "zh-CN", etc.

    Returns
    -------
    str
        Path to the generated WAV audio file.
    """
    # Purge unwanted characters from the text.
    text = clean_text_for_tts(text)

    # Choose the right model.
    if model == "command_line":
        return command_line_say(
                text=text,
                output_audio_path=output_audio_path)

    elif model == "google_tts":
        return google_tts(
                text=text,
                output_audio_path=output_audio_path,
                language=language)

    elif model == "pytts":
        return pytts_asr(
                text=text,
                output_audio_path=output_audio_path)

    elif model == "jeff":
        return jeff_model(
            text=text,
            server_url=config["jeff_tts_model_url"],
            output_audio_path=output_audio_path)

    else:
        raise ValueError(f"Unsupported TTS model: {model}")


class TextToSpeechAPI(Resource):
    """
    RESTful API resource for Text-to-Speech (TTS) conversion.

    Exposes a POST endpoint at `/tts` that accepts JSON input containing text
    and TTS parameters, and returns the path to the generated audio file.

    Expected JSON input fields:
        - text (str): The text to be converted to speech.
        - model (str): The TTS model to use (e.g., "google_tts", "pytts", "command_line").
        - output_audio_path (str): Desired output file path for the generated audio (.wav).
        - language (str): Language code for TTS (e.g., "en", "zh-cn").

    Returns
    -------
        JSON response with:
        - status (str): "success" or "error"
        - audio_path (str): Path to the generated audio file (on success)
        - message (str): Error message (on failure)
    """
    def post(self):
        """
        Handle POST requests to perform text-to-speech synthesis.

        Reads JSON data from the request body, invokes the text_to_speech function
        with the provided parameters, and returns the resulting audio file path.

        Raises
        ------
            KeyError: If any expected JSON fields are missing.
            Exception: For errors during TTS conversion.
        """
        try:
            # Parse JSON input from client request.
            data = request.get_json()

            # Extract required parameters.
            text = data["text"]
            model = data["model"]
            output_audio_path = data["output_audio_path"]
            language = data["language"]

            # Sanitize the path so system files can't be erased.
            if not output_audio_path.endswith(".wav"):
                raise ValueError("Output file must be a .wav file.")

            # Perform text-to-speech conversion.
            filepath = text_to_speech(
                output_audio_path=output_audio_path,
                text=text,
                model=model,
                language=language)

            # Return success response with audio file path.
            return jsonify({
                "status": "success",
                "audio_path": filepath
            })

        # Return error response with exception message.
        except KeyError as ke:
            return jsonify({
                "status": "error", 
                "message": f"Missing field: {ke}"
            }), 400

        # Catch remaining exceptions.
        except Exception as e:
            return jsonify({
                "status": "error",
                "message": str(e)
            }), 500


# Add the resources to the Flask app.
api.add_resource(TextToSpeechAPI, "/tts")
api.add_resource(HealthCheckAPI, "/health")



if __name__ == "__main__":

    # Run the TTS server.
    app.run(
        host="0.0.0.0",
        port=8013,
        debug=False,
        use_reloader=False)

    # TEXT= """
    # I'm Jeff Bezos, and I'm reading the Unabomber's Manifesto. Let's continue.

    # The Industrial Revolution and its consequences have been a disaster for the human race. 
    # They have greatly increased the life-expectancy of those of us who live in “advanced” countries,
    # but they have destabilized society, have made life unfulfilling,
    # have subjected human beings to indignities, have led to widespread psychological suffering 
    # in the Third World to physical
    # suffering as well and have inflicted severe damage on the natural world.

    # I'm Jeff Bezos, and I'm reading the younabomber's Manifesto. Let's continue.

    # The continued development of technology will
    # worsen the situation. It will certainly subject human being to greater indignities 
    # and inflict greater damage on the natural world,
    # it will probably lead to greater social disruption and psychological suffering,
    # and it may lead to increased physical suffering
    # even in “advanced” countries.

    # I'm Jeff Bezos, and I'm reading the younabomber's Manifesto. Let's continue.

    # The industrial-technological system may survive or it may break down.
    # If it survives, it MAY eventually achieve a low level
    # of physical and psychological suffering, but only after passing through a long and very
    # painful period of adjustment and only at
    # the cost of permanently reducing human beings and many other living organisms to engineered
    # products and mere cogs in the
    # social machine. 

    # I'm Jeff Bezos, and I'm reading the younabomber's Manifesto. Let's continue.

    # Furthermore, if the system survives, the consequences will be inevitable
    # There is no way of reforming or
    # modifying the system so as to prevent it from depriving people of dignity and autonomy.
    # If the system breaks down the consequences will still be very painful. But the bigger
    # the system grows the more disastrous
    # the results of its breakdown will be, so if it is to break down it had best break down
    # sooner rather than later.

    # I'm Jeff Bezos, and I'm reading the younabomber's Manifesto. Let's continue.

    # We therefore advocate a revolution against the industrial system. This revolution
    # may or may not make use of violence; it
    # may be sudden or it may be a relatively gradual process spanning a few decades. We can't predict
    # any of that. But we do outline in a very general way the measures that those who hate the industrial system
    # should take in order to prepare the way for
    # a revolution against that form of society. 

    # I'm Jeff Bezos, and I'm reading the younabomber's Manifesto. Let's continue.

    # This is not to be a POLITICAL revolution.
    # Its object will be to overthrow not
    # governments but the economic and technological basis of the present society.
    # In this article we give attention to only some of the negative developments
    # that have grown out of the industrial-technological system.

    # I'm Jeff Bezos, and I'm reading the younabomber's Manifesto. Let's continue.

    # Other such developments we mention only briefly or ignore altogether.
    # This does not mean that we
    # regard these other developments as unimportant. For practical reasons we have to confine our
    # discussion to areas that have
    # received insufficient public attention or in which we have something new to say.

    # I'm Jeff Bezos, and I'm reading the younabomber's Manifesto. Let's continue.

    # For example,
    # since there are well-developed
    # environmental and wilderness movements, we have written very little about environmental
    # degradation or the destruction of
    # wild nature, even though we consider these to be highly important
    # Almost everyone will agree that we live in a deeply troubled society.

    # I'm Jeff Bezos, and I'm reading the younabomber's Manifesto. Let's continue.

    # One of the most widespread manifestations of the
    # craziness of our world is leftism, so a discussion of the psychology of leftism can
    # serve as an introduction to the discussion of
    # the problems of modern society in general.
    # But what is leftism? During the first half of the 20th century leftism could have been
    # practically identified with socialism.

    # I'm Jeff Bezos, and I'm reading the younabomber's Manifesto. Let's continue.

    # Today the movement is fragmented and it is not clear who can properly be called a leftist.
    # When we speak of leftists in this
    # article we have in mind mainly socialists, collectivists, “politically correct” types,
    # feminists, gay and disability activists, animal
    # rights activists and the like.

    # I'm Jeff Bezos, and I'm reading the younabomber's Manifesto. Let's continue.

    # But not everyone who is associated with one of these movements
    # is a leftist. What we are trying to
    # get at in discussing leftism is not so much movement or an ideology as a psychological type,
    # or rather a collection of related
    # types. Thus, what we mean by “leftism” will emerge more clearly in the course of our discussion
    # of leftist psychology.

    # I'm Jeff Bezos, and I'm reading the younabomber's Manifesto. Let's continue.

    # Even so, our conception of leftism will remain a good deal less clear than we would wish,
    # but there doesn't seem to be any
    # remedy for this. All we are trying to do here is indicate in a rough and approximate way
    # the two psychological tendencies that
    # we believe are the main driving force of modern leftism. We by no means claim to be telling
    # the WHOLE truth about leftist
    # psychology.

    # I'm Jeff Bezos, and I'm reading the younabomber's Manifesto. Let's continue.

    # Also, our discussion is meant to apply to modern leftism only. We leave open
    # the question of the extent to which
    # our discussion could be applied to the leftists of the 19th and early 20th centuries.
    # The two psychological tendencies that underlie modern leftism we call “feelings of
    # inferiority” and “oversocialization.”

    # I'm Jeff Bezos, and I'm reading the younabomber's Manifesto. Let's continue.

    # Feelings of inferiority are characteristic of modern leftism as a whole, while
    # oversocialization is characteristic only of a certain
    # segment of modern leftism; but this segment is highly influential.
    # """

    # TEXT2 = "I'm Jeff Bezos, and I'm reading the younabomber's Manifesto. Let's continue."

    # text_to_speech(
    #     output_audio_path="jeff_reading_unabomber.py",
    #     text=TEXT,
    #     model="jeff",
    #     language="en")
